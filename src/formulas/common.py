"""本地公式包共用工具：输入校验、适用域评估、度数表与结果组装。

本模块只依赖标准库，供 barrett/srkt/hoffer_q/haigis 四个公式复用。
所有长度单位 mm，屈光度单位 D，聚散度以 1336 表示 1.336*1000。
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# 光学常数
# ---------------------------------------------------------------------------

N_AQUEOUS = 1.336
VERGENCE_SCALE = 1336.0
SPECTACLE_VERTEX_M = 0.012

K_INDEX_REF = 1.3375
K_INDEX_ALT = 1.332

# 硬边界：超出直接拒绝，避免产生无意义的医学数值。
AL_HARD_MIN = 12.0
AL_HARD_MAX = 38.0
K_HARD_MIN = 30.0
K_HARD_MAX = 60.0

# 舒适域：超出只降置信度，不拒绝计算。
AL_COMFORT_MIN = 22.0
AL_COMFORT_MAX = 26.0
K_COMFORT_MIN = 38.0
K_COMFORT_MAX = 48.0

# IOL 度数表的显示范围（覆盖常见的负度数/超高度数）。
IOL_TABLE_MIN = -10.0
IOL_TABLE_MAX = 45.0


def as_float(value, name):
    """把输入转换为有限浮点数，失败时抛出 ValueError。"""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} 必须是有效数值")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是有效数值") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} 必须是有限数值")
    return result


def normalize_k_to_reference(k, k_index=K_INDEX_REF):
    """把任意角膜曲率计折射率下的 K 折算到 1.3375 基准。"""
    k_value = as_float(k, "K")
    index = as_float(k_index, "k_index")
    if abs(index - K_INDEX_REF) < 1e-9:
        return k_value
    if abs(index - K_INDEX_ALT) < 1e-9:
        return k_value * (K_INDEX_REF - 1.0) / (K_INDEX_ALT - 1.0)
    raise ValueError("k_index 只支持 1.3375 或 1.332")


def corneal_target(target, vertex=SPECTACLE_VERTEX_M):
    """把眼镜平面的目标屈光度折算到角膜平面。"""
    target_value = as_float(target, "target_refraction")
    denominator = 1.0 - vertex * target_value
    if denominator <= 1e-6:
        raise ValueError("target_refraction 过大，无法折算到角膜平面")
    return target_value / denominator


def validate_eye(al, k):
    """校验 AL/K 的硬边界，返回 (AL, K) 浮点元组。"""
    al_value = as_float(al, "AL")
    k_value = as_float(k, "K")
    if not AL_HARD_MIN <= al_value <= AL_HARD_MAX:
        raise ValueError(
            f"AL={al_value:.2f} mm 超出可计算范围 "
            f"{AL_HARD_MIN:.0f}-{AL_HARD_MAX:.0f} mm"
        )
    if not K_HARD_MIN <= k_value <= K_HARD_MAX:
        raise ValueError(
            f"K={k_value:.2f} D 超出可计算范围 {K_HARD_MIN:.0f}-{K_HARD_MAX:.0f} D"
        )
    return al_value, k_value


def assess_domain(al, k):
    """评估 AL/K 是否落在舒适域内。

    返回 {"confidence", "warnings", "low_confidence"}；超出舒适域时只追加
    警告并降置信度，不拒绝计算。
    """
    al_value = as_float(al, "AL")
    k_value = as_float(k, "K")
    warnings = []
    if al_value < AL_COMFORT_MIN or al_value > AL_COMFORT_MAX:
        warnings.append(
            f"AL={al_value:.2f} mm 超出适用域 "
            f"{AL_COMFORT_MIN:.0f}-{AL_COMFORT_MAX:.0f} mm"
        )
    if k_value < K_COMFORT_MIN or k_value > K_COMFORT_MAX:
        warnings.append(
            f"K={k_value:.2f} D 超出适用域 {K_COMFORT_MIN:.0f}-{K_COMFORT_MAX:.0f} D"
        )
    low_confidence = bool(warnings)
    return {
        "confidence": "LOW_CONFIDENCE" if low_confidence else "OK",
        "warnings": warnings,
        "low_confidence": low_confidence,
    }


def round_to_step(value, step):
    """按给定步长四舍五入（step 必须为正数）。"""
    step_value = as_float(step, "step")
    if step_value <= 0:
        raise ValueError("step 必须是正数")
    value_float = as_float(value, "计数值")
    return round(math.floor(value_float / step_value + 0.5) * step_value, 4)


def format_power(value):
    """格式化为表格风格的度数文本（整数不带小数点）。"""
    power = as_float(value, "iol_power")
    if abs(power - round(power)) < 1e-9:
        return str(round(power))
    return f"{power:.1f}"


def build_table(
    exact_power,
    refraction_for_power,
    target,
    step=0.5,
    span=2.0,
    table_min=IOL_TABLE_MIN,
    table_max=IOL_TABLE_MAX,
):
    """围绕精确度数生成 IOL 候选表（默认 0.5 D 步长、span 2.0 -> 9 行）。

    每行调用 refraction_for_power(power) 得到该度数对应的预测屈光度；
    预测屈光度无法计算的档位会被跳过（极端参数下允许少于 9 行）。
    推荐行 = 预测屈光度最接近 target 的一行，且仅标记一行。
    """
    step_value = as_float(step, "step")
    if step_value <= 0:
        raise ValueError("step 必须是正数")
    span_value = as_float(span, "span")
    if span_value < 0:
        raise ValueError("span 必须是非负数")
    target_value = as_float(target, "target_refraction")

    center = round_to_step(exact_power, step_value)
    half_span = round(span_value / step_value)
    rows = []
    for offset in range(-half_span, half_span + 1):
        power = round(center + offset * step_value, 4)
        if power < table_min or power > table_max:
            continue
        try:
            refraction = float(refraction_for_power(power))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(refraction):
            continue
        rows.append(
            {
                "iol_power": format_power(power),
                "optic": "Biconvex",
                "refraction": f"{refraction:.2f}",
                "recommended": False,
            }
        )

    if not rows:
        raise ValueError("无法生成 IOL 度数表：所有档位的预测屈光度都不可用")
    best_index = min(
        range(len(rows)),
        key=lambda index: abs(float(rows[index]["refraction"]) - target_value),
    )
    rows[best_index]["recommended"] = True
    return rows


def invert_vergence_target(al, elp, k, iol_power, vertex=SPECTACLE_VERTEX_M):
    """由 P = 1336/(AL-ELP) - 1336/(1336/K' - ELP) 反解眼镜平面屈光度。

    反解步骤：先由 P 求出角膜平面的等效 K'，再由顶点距离公式还原眼镜
    平面的屈光度。无法反解（发散或超出物理范围）时返回 nan。
    """
    al_value = as_float(al, "AL")
    elp_value = as_float(elp, "ELP")
    k_value = as_float(k, "K")
    power_value = as_float(iol_power, "iol_power")
    if al_value - elp_value <= 1e-6:
        return float("nan")
    vergence_after_iol = VERGENCE_SCALE / (al_value - elp_value) - power_value
    if vergence_after_iol <= 0:
        return float("nan")
    k_target = VERGENCE_SCALE / (VERGENCE_SCALE / vergence_after_iol + elp_value)
    corneal_refraction = k_target - k_value
    denominator = 1.0 + vertex * corneal_refraction
    if denominator <= 1e-6:
        return float("nan")
    return corneal_refraction / denominator


def build_formula_result(
    *,
    al,
    k,
    target,
    step,
    exact_power,
    refraction_for_power,
    elp,
    a_constant,
    lens_factor,
    constants_text,
    model,
    model_note,
    warnings=(),
):
    """按统一返回结构组装公式结果（四个公式共用同一份字段定义）。"""
    domain = assess_domain(al, k)
    merged_warnings = list(domain["warnings"]) + [str(item) for item in warnings]
    table = build_table(
        exact_power,
        refraction_for_power,
        target,
        step=step,
    )
    recommended = next(row for row in table if row["recommended"])
    iol_power = float(recommended["iol_power"])
    predicted_refraction = float(refraction_for_power(iol_power))
    low_confidence = bool(merged_warnings) or domain["low_confidence"]
    return {
        "iol_power": iol_power,
        "iol_power_text": recommended["iol_power"],
        "iol_power_exact": float(exact_power),
        "predicted_refraction": predicted_refraction,
        "elp": float(elp),
        "lens_factor": (float(lens_factor) if lens_factor is not None else None),
        "a_constant": float(a_constant),
        "confidence": "LOW_CONFIDENCE" if low_confidence else "OK",
        "low_confidence": low_confidence,
        "warnings": merged_warnings,
        "model": model,
        "model_note": model_note,
        "constants_text": constants_text,
        "iol_options": table,
    }


__all__ = [
    "AL_COMFORT_MAX",
    "AL_COMFORT_MIN",
    "AL_HARD_MAX",
    "AL_HARD_MIN",
    "IOL_TABLE_MAX",
    "IOL_TABLE_MIN",
    "K_COMFORT_MAX",
    "K_COMFORT_MIN",
    "K_HARD_MAX",
    "K_HARD_MIN",
    "K_INDEX_ALT",
    "K_INDEX_REF",
    "N_AQUEOUS",
    "SPECTACLE_VERTEX_M",
    "VERGENCE_SCALE",
    "as_float",
    "assess_domain",
    "build_formula_result",
    "build_table",
    "corneal_target",
    "format_power",
    "invert_vergence_target",
    "normalize_k_to_reference",
    "round_to_step",
    "validate_eye",
]
