"""Barrett Universal II 离线计算核心（ALK 简化版 + 可选五参数修正）。

来源与限制（务必先读）
======================
1. 官方 Barrett Universal II（BUII）的 ELP 预测使用未公开的三阶多项式回归和
   厚透镜近轴光线追迹；Barrett 本人在 2024 年专著章节中说明其最简实现约
   750 行代码、完整实现可达 3000 行（G. D. Barrett, "Barrett Formulas:
   Strategies to Improve IOL Power Prediction", in Intraocular Lens
   Calculations, Springer, 2024, doi:10.1007/978-3-031-50666-6_37）。
2. 任务书引用的论文 "A new theoretical approach to intraocular lens power
   calculation using only axial length and keratometry"（Clin Exp
   Ophthalmol. 2021;49(7):660-670）无法在 PubMed / Crossref / Wiley 目录
   中检索到；同卷同期的 660-670 页由另外两篇论文占据。详细检索记录见
   docs/calibration_report.md。因此本模块不声称逐系数复刻该论文。
3. GitHub 上的 Wingman4l7/catcalc 只是一份 Selenium 网页填表脚本（没有
   BUII 公式）；任务书提到的 wcgBarrett 在 GitHub / PyPI 上均不存在。
   故无法做三方公式对数，报告里改为与公开的 SRK/T、Holladay 1 公式对照，
   并单独说明原因。
4. 本模块真正"成文"的部分是 Gaussian 聚散度（vergence）核心和厚透镜主平面
   思想，可追溯到：
     - G. D. Barrett. Intraocular lens calculation formulas for new
       intraocular lens implants. J Cataract Refract Surg. 1987;13(4):389-396.
     - G. D. Barrett. An improved universal theoretical formula for
       intraocular lens power prediction. J Cataract Refract Surg.
       1993;19(6):713-720. PMID 8271166.
     - Fyodorov 薄透镜/聚散度公式（EyeWiki: Biometry for Intra-Ocular Lens
       Power Calculation）。
   聚散度核心写作（mm 制）::

       P = 1336 / (AL - ELP) - 1336 / (1336 / K' - ELP)

   其中 K' = K + Rc，Rc 为目标屈光度折算到角膜平面的值。
5. ELP 预测式是本仓库根据公开 CC-BY-4.0 校准网格反演并固化的近似式，
   不是官方系数，也不是论文系数；系数与拟合/验证方法全部写在
   docs/calibration_report.md，代码常量旁标注 "CALIBRATED"。换成官方
   系数时只需替换 ELP_* 常量。运行路径零网络、零第三方依赖。

A-constant 与 Lens Factor 的换算
=================================
官方计算器的 A<->LF 换算未公开公式，但多家厂商公开了成对的常数，例如
Johnson & Johnson 镜片常数表（2026 版）给出：

    A = 118.7 -> LF = 1.73
    A = 119.0 -> LF = 1.88
    A = 119.1 -> LF = 1.94
    A = 119.3 -> LF = 2.04

四点最小二乘得到 LF = 0.518667 * A - 59.8368（残差 <= 0.005）。本模块
采用该线性关系，并把它与 ELP 的常数项解耦：A 只通过 LF 平移 ELP。
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# 光学常数（论文/教科书的通用取值）
# ---------------------------------------------------------------------------

# 眼内介质折射率；聚散度公式中以 1336 表示 1.336 * 1000（mm 制）。
N_AQUEOUS = 1.336
N_VITREOUS = 1.336
VERGENCE_SCALE = 1336.0

# 眼镜平面到角膜顶点的顶点距离（米）。Barrett 计算器默认 12 mm。
SPECTACLE_VERTEX_M = 0.012

# 角膜曲率计折射率。1.3375 是标定基准；1.332 为备选。
K_INDEX_REF = 1.3375
K_INDEX_ALT = 1.332

# 官方表单允许的硬边界（超出直接拒绝，避免产生无意义数值）。
AL_HARD_MIN = 12.0
AL_HARD_MAX = 38.0
K_HARD_MIN = 30.0
K_HARD_MAX = 60.0

# 论文适用域。超出只降置信度，不拒绝计算（报告里给出依据）。
AL_COMFORT_MIN = 22.0
AL_COMFORT_MAX = 26.0
K_COMFORT_MIN = 38.0
K_COMFORT_MAX = 48.0

# IOL 度数表格的显示范围（覆盖官方表格常见的负/超高度数）。
IOL_TABLE_MIN = -10.0
IOL_TABLE_MAX = 45.0

# ---------------------------------------------------------------------------
# A-constant <-> Lens Factor（4 组公开厂商常数对的最小二乘直线）
# ---------------------------------------------------------------------------

LF_SLOPE = 0.518667  # CALIBRATED: 见模块 docstring 的 4 组锚点
LF_INTERCEPT = -59.836800  # CALIBRATED
LF_REFERENCE_A = 118.7  # 校准网格使用的 A-constant

DEFAULT_A_CONSTANT = 118.7  # 与校准数据一致；API 层默认 119.30
DEFAULT_K_INDEX = K_INDEX_REF

# 参考眼（校准数据的基线）。
REF_AL = 23.5
REF_K = 44.0
REF_ACD = 3.2
REF_LT = 4.6
REF_WTW = 11.9

# ---------------------------------------------------------------------------
# ELP 近似式（单位 mm）
#
#   ELP = C0 + cAL*da + cK*dk + cAL2*da^2 + cALK*da*dk + cK2*dk^2
#         + cACD*dacd + cLT*dlt + cWTW*dwtw
#         + (LF(A) - LF(118.7))
#
# 其中 da = AL - 23.5, dk = K - 44.0, dacd/dlt/dwtw 同理。
# C0 吸收了 LF(118.7) = 1.7305，所以 A 变化只通过最后一项平移 ELP。
#
# CALIBRATED（非官方、非论文系数）：由 scripts/calibrate_offline.py 从
# ekrbye/barrett-uii-data 的 CC-BY-4.0 公开数据反演，拟合与留一验证见
# docs/calibration_report.md。不要把它误当成官方 BUII 的系数。
# ---------------------------------------------------------------------------

ELP_C0 = 5.481512
ELP_C_AL = 0.384027
ELP_C_K = 0.131907
ELP_C_AL2 = 0.041244
ELP_C_ALK = 0.045497
ELP_C_K2 = 0.004143

# 五参数修正项（ACD / 晶状体厚度 / 角膜白到白）。
# 只在调用方显式提供这些测量值时启用；否则退化为 ALK 版。
ELP_C_ACD = 0.274984
ELP_C_LT = 0.207436
ELP_C_WTW = -0.028200

# 模型标识，随每个结果返回，防止前端误以为这是官方全量公式。
MODEL_ID = "BUII-ALK-offline-surrogate/1.0"
MODEL_NOTE = (
    "离线近似实现：Gaussian 聚散度核心 + 公开网格反演的 ELP 近似式；"
    "不是官方 Barrett Universal II，不等价于官网计算器。"
)


class OfflineInputError(ValueError):
    """离线计算的输入超出可计算范围。"""


def _as_float(value, name):
    """把输入转换为有限浮点数，失败时抛出 OfflineInputError。"""
    if isinstance(value, bool) or value is None:
        raise OfflineInputError(f"{name} 必须是有效数值")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise OfflineInputError(f"{name} 必须是有效数值") from exc
    if not math.isfinite(result):
        raise OfflineInputError(f"{name} 必须是有限数值")
    return result


def a_constant_to_lens_factor(a_constant=DEFAULT_A_CONSTANT):
    """A-constant 线性换算为 Barrett Lens Factor。

    锚点来自厂商公开常数表（A=118.7/119.0/119.1/119.3 -> LF
    1.73/1.88/1.94/2.04），最小二乘直线见模块 docstring。
    """
    a = _as_float(a_constant, "a_constant")
    if not 100.0 <= a <= 140.0:
        raise OfflineInputError("a_constant 超出合理范围 100-140")
    return LF_SLOPE * a + LF_INTERCEPT


def lens_factor_to_a_constant(lens_factor):
    """Lens Factor 反算 A-constant（与 a_constant_to_lens_factor 互逆）。"""
    lf = _as_float(lens_factor, "lens_factor")
    return (lf - LF_INTERCEPT) / LF_SLOPE


def normalize_k_to_reference(k, k_index=DEFAULT_K_INDEX):
    """把任意 K-index 下的角膜屈光度折算到 1.3375 基准。

    同一角膜半径 r 下 K = (n - 1) / r，因此
    K_13375 = K_other * (1.3375 - 1) / (n_other - 1)。
    """
    k_value = _as_float(k, "K")
    try:
        index = float(k_index)
    except (TypeError, ValueError) as exc:
        raise OfflineInputError("k_index 必须是有效数值") from exc
    if abs(index - K_INDEX_REF) < 1e-9:
        return k_value
    if abs(index - K_INDEX_ALT) < 1e-9:
        return k_value * (K_INDEX_REF - 1.0) / (K_INDEX_ALT - 1.0)
    raise OfflineInputError("k_index 只支持 1.3375 或 1.332")


def assess_input_domain(al, k):
    """评估输入是否落在论文适用域内。

    返回 {"confidence": "OK"|"LOW_CONFIDENCE", "warnings": [...]}。
    """
    al_value = _as_float(al, "AL")
    k_value = _as_float(k, "K")
    warnings = []
    if al_value < AL_COMFORT_MIN or al_value > AL_COMFORT_MAX:
        warnings.append(
            f"AL={al_value:.2f} mm 超出论文适用域 "
            f"{AL_COMFORT_MIN:.0f}-{AL_COMFORT_MAX:.0f} mm"
        )
    if k_value < K_COMFORT_MIN or k_value > K_COMFORT_MAX:
        warnings.append(
            f"K={k_value:.2f} D 超出论文适用域 "
            f"{K_COMFORT_MIN:.0f}-{K_COMFORT_MAX:.0f} D"
        )
    return {
        "confidence": "LOW_CONFIDENCE" if warnings else "OK",
        "warnings": warnings,
    }


def _validate_eye(al, k):
    """校验硬边界并返回 (al, k)。"""
    al_value = _as_float(al, "AL")
    k_value = _as_float(k, "K")
    if not AL_HARD_MIN <= al_value <= AL_HARD_MAX:
        raise OfflineInputError(
            f"AL={al_value:.2f} mm 超出可计算范围 "
            f"{AL_HARD_MIN:.0f}-{AL_HARD_MAX:.0f} mm"
        )
    if not K_HARD_MIN <= k_value <= K_HARD_MAX:
        raise OfflineInputError(
            f"K={k_value:.2f} D 超出可计算范围 {K_HARD_MIN:.0f}-{K_HARD_MAX:.0f} D"
        )
    if al_value <= 0 or 1336.0 / k_value <= 0:
        raise OfflineInputError("AL/K 组合无法形成有效光学系统")
    return al_value, k_value


def _resolve_lens_factor(lf, a_constant):
    """解析 LF：显式 LF 优先，其次 A-constant，最后用默认 A。"""
    if lf is not None:
        return _as_float(lf, "lens_factor")
    if a_constant is not None:
        return a_constant_to_lens_factor(a_constant)
    return a_constant_to_lens_factor(DEFAULT_A_CONSTANT)


def predict_elp(
    al,
    k,
    lf=None,
    a_constant=None,
    k_index=DEFAULT_K_INDEX,
    acd=None,
    lt=None,
    wtw=None,
    use_surgeon_inputs=True,
):
    """预测有效晶体位置 ELP（mm，自角膜顶点起算）。

    参数
    ----
    al, k : 眼轴长度（mm）与角膜屈光度（D）。
    lf, a_constant : 二者取其一；都缺省时使用 A=118.7。
    k_index : 1.3375 或 1.332，内部统一折算到 1.3375 基准。
    acd, lt, wtw : 可选术前测量值；提供后启用五参数修正项。
    use_surgeon_inputs : 置 False 时强制只用 AL+K（纯 ALK 版）。
    """
    al_value, k_value = _validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    lens_factor = _resolve_lens_factor(lf, a_constant)

    da = al_value - REF_AL
    dk = k_ref - REF_K
    elp = (
        ELP_C0
        + ELP_C_AL * da
        + ELP_C_K * dk
        + ELP_C_AL2 * da * da
        + ELP_C_ALK * da * dk
        + ELP_C_K2 * dk * dk
    )

    if use_surgeon_inputs:
        if acd is not None:
            elp += ELP_C_ACD * (_as_float(acd, "ACD") - REF_ACD)
        if lt is not None:
            elp += ELP_C_LT * (_as_float(lt, "LT") - REF_LT)
        if wtw is not None:
            elp += ELP_C_WTW * (_as_float(wtw, "WTW") - REF_WTW)

    # A-constant 只通过 LF 平移 ELP；LF(118.7) 已包含在 C0 中。
    elp += lens_factor - a_constant_to_lens_factor(LF_REFERENCE_A)
    return elp


def _corneal_plane_target(target, vertex=SPECTACLE_VERTEX_M):
    """把眼镜平面的目标屈光度折算到角膜平面。"""
    target_value = _as_float(target, "target_refraction")
    denominator = 1.0 - vertex * target_value
    if denominator <= 1e-6:
        raise OfflineInputError("target_refraction 过大，无法折算到角膜平面")
    return target_value / denominator


def iol_power_for_target(
    al,
    k,
    target=0.0,
    lf=None,
    a_constant=None,
    k_index=DEFAULT_K_INDEX,
    acd=None,
    lt=None,
    wtw=None,
    use_surgeon_inputs=True,
    vertex=SPECTACLE_VERTEX_M,
):
    """给定目标屈光度，求精确（未取整）的 IOL 度数。

    公式（mm 制）::

        K' = K + target / (1 - vertex * target)
        P  = 1336 / (AL - ELP) - 1336 / (1336 / K' - ELP)
    """
    al_value, k_value = _validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    elp = predict_elp(
        al_value,
        k_ref,
        lf=lf,
        a_constant=a_constant,
        k_index=K_INDEX_REF,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
    )
    k_target = k_ref + _corneal_plane_target(target, vertex)

    if al_value - elp <= 1e-6:
        raise OfflineInputError("AL 与 ELP 过于接近，公式发散")
    if 1336.0 / k_target - elp <= 1e-6:
        raise OfflineInputError("角膜屈光度与 ELP 组合导致公式发散")

    return VERGENCE_SCALE / (al_value - elp) - VERGENCE_SCALE / (
        VERGENCE_SCALE / k_target - elp
    )


def _predict_refraction_impl(
    al,
    k,
    lf,
    a_constant,
    iol_power,
    acd,
    lt,
    wtw,
    use_surgeon_inputs,
    vertex,
):
    """predict_refraction 的内部实现，返回元数据字典。"""
    elp = predict_elp(
        al,
        k,
        lf=lf,
        a_constant=a_constant,
        k_index=K_INDEX_REF,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
    )
    exact_power = iol_power_for_target(
        al,
        k,
        target=0.0,
        lf=lf,
        a_constant=a_constant,
        k_index=K_INDEX_REF,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
        vertex=vertex,
    )
    if iol_power is None:
        power = _round_to_step(exact_power, 0.5)
        rounded = True
    else:
        power = _as_float(iol_power, "iol_power")
        rounded = False

    # 反解：V = 1336/(AL-ELP) - P，则 K' = 1336/(1336/V + ELP)。
    vergence_after_iol = VERGENCE_SCALE / (al - elp) - power
    if vergence_after_iol <= 0:
        return {
            "refraction": float("nan"),
            "iol_power": power,
            "elp": elp,
            "exact_emmetropic_power": exact_power,
            "rounded": rounded,
        }
    k_target = VERGENCE_SCALE / (VERGENCE_SCALE / vergence_after_iol + elp)
    corneal_refraction = k_target - k
    denominator = 1.0 + vertex * corneal_refraction
    refraction = (
        corneal_refraction / denominator if denominator > 1e-6 else float("nan")
    )
    return {
        "refraction": refraction,
        "iol_power": power,
        "elp": elp,
        "exact_emmetropic_power": exact_power,
        "rounded": rounded,
    }


def predict_refraction(
    al,
    k,
    lf=None,
    a_constant=None,
    k_index=DEFAULT_K_INDEX,
    iol_power=None,
    acd=None,
    lt=None,
    wtw=None,
    use_surgeon_inputs=True,
    vertex=SPECTACLE_VERTEX_M,
):
    """给定 IOL 度数，预测术后屈光度（D，眼镜平面）。

    iol_power 省略时，先求正视所需度数并四舍五入到 0.5 D，再返回该档
    晶体的预测屈光度（即论文里的 emmetropia verifying 步骤）。
    返回值是浮点数；需要元数据请用 predict_refraction_detail。
    """
    al_value, k_value = _validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    detail = _predict_refraction_impl(
        al_value,
        k_ref,
        lf=lf,
        a_constant=a_constant,
        iol_power=iol_power,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
        vertex=vertex,
    )
    return detail["refraction"]


def predict_refraction_detail(
    al,
    k,
    lf=None,
    a_constant=None,
    k_index=DEFAULT_K_INDEX,
    iol_power=None,
    acd=None,
    lt=None,
    wtw=None,
    use_surgeon_inputs=True,
    vertex=SPECTACLE_VERTEX_M,
):
    """与 predict_refraction 相同，但返回完整元数据字典。"""
    al_value, k_value = _validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    detail = _predict_refraction_impl(
        al_value,
        k_ref,
        lf=lf,
        a_constant=a_constant,
        iol_power=iol_power,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
        vertex=vertex,
    )
    detail.update(
        {
            "al": al_value,
            "k": k_value,
            "k_reference_index": k_ref,
            "lens_factor": _resolve_lens_factor(lf, a_constant),
            "a_constant": (
                _as_float(a_constant, "a_constant") if a_constant is not None else None
            ),
            "model": MODEL_ID,
        }
    )
    return detail


def _round_to_step(value, step):
    """四舍五入到给定步长（0.5 或 1.0 D）。"""
    try:
        step_value = float(step)
    except (TypeError, ValueError) as exc:
        raise OfflineInputError("step 必须是有效数值") from exc
    if not math.isfinite(step_value) or step_value <= 0:
        raise OfflineInputError("step 必须是正数")
    return round(math.floor(value / step_value + 0.5) * step_value, 4)


def _format_power(value):
    """格式化为官方表格风格的字符串（整度数不带小数点）。"""
    if abs(value - round(value)) < 1e-9:
        return str(round(value))
    return f"{value:.1f}"


def build_iol_table(
    al,
    k,
    target=0.0,
    lf=None,
    a_constant=None,
    k_index=DEFAULT_K_INDEX,
    step=0.5,
    span=2.0,
    acd=None,
    lt=None,
    wtw=None,
    use_surgeon_inputs=True,
):
    """生成 IOL 度数候选表（按 step 步进，默认 0.5 D）。

    每行与官网结果的字段保持一致：iol_power、refraction、recommended，
    并额外给出 optic 以便 Web UI 复用。
    """
    al_value, k_value = _validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    exact_power = iol_power_for_target(
        al_value,
        k_ref,
        target=target,
        lf=lf,
        a_constant=a_constant,
        k_index=K_INDEX_REF,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
    )
    center = _round_to_step(exact_power, step)
    half_span = round(span / step)
    rows = []
    for offset in range(-half_span, half_span + 1):
        power = round(center + offset * step, 4)
        if power < IOL_TABLE_MIN or power > IOL_TABLE_MAX:
            continue
        detail = _predict_refraction_impl(
            al_value,
            k_ref,
            lf=lf,
            a_constant=a_constant,
            iol_power=power,
            acd=acd,
            lt=lt,
            wtw=wtw,
            use_surgeon_inputs=use_surgeon_inputs,
            vertex=SPECTACLE_VERTEX_M,
        )
        rows.append(
            {
                "iol_power": _format_power(power),
                "optic": "Biconvex",
                "refraction": f"{detail['refraction']:.2f}",
                "recommended": False,
            }
        )
    # 推荐档 = 预测屈光度最接近目标值的一档（与 Web UI 逻辑一致）。
    target_value = _as_float(target, "target_refraction")
    best = None
    best_diff = float("inf")
    for index, row in enumerate(rows):
        diff = abs(float(row["refraction"]) - target_value)
        if diff < best_diff:
            best_diff = diff
            best = index
    if best is not None:
        rows[best]["recommended"] = True
    return rows


def solve_iol_power(
    al,
    k,
    target=0.0,
    lf=None,
    a_constant=None,
    k_index=DEFAULT_K_INDEX,
    step=0.5,
    span=2.0,
    acd=None,
    lt=None,
    wtw=None,
    use_surgeon_inputs=True,
):
    """目标屈光度反解 IOL 度数（最近档）并给出验证信息。

    返回字典包含：精确度数、取整后度数、该档晶体的预测屈光度、ELP、
    Lens Factor、置信度和警告。
    """
    al_value, k_value = _validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    domain = assess_input_domain(al_value, k_value)
    warnings = list(domain["warnings"])

    elp = predict_elp(
        al_value,
        k_ref,
        lf=lf,
        a_constant=a_constant,
        k_index=K_INDEX_REF,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
    )
    exact_power = iol_power_for_target(
        al_value,
        k_ref,
        target=target,
        lf=lf,
        a_constant=a_constant,
        k_index=K_INDEX_REF,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
    )
    rounded_power = _round_to_step(exact_power, step)
    if rounded_power < IOL_TABLE_MIN or rounded_power > IOL_TABLE_MAX:
        warnings.append(
            f"推荐度数 {rounded_power:.1f} D 超出表格范围 "
            f"{IOL_TABLE_MIN:.0f}-{IOL_TABLE_MAX:.0f} D"
        )
    detail = _predict_refraction_impl(
        al_value,
        k_ref,
        lf=lf,
        a_constant=a_constant,
        iol_power=rounded_power,
        acd=acd,
        lt=lt,
        wtw=wtw,
        use_surgeon_inputs=use_surgeon_inputs,
        vertex=SPECTACLE_VERTEX_M,
    )
    lens_factor = _resolve_lens_factor(lf, a_constant)
    return {
        "al": al_value,
        "k": k_value,
        "k_reference_index": k_ref,
        "target_refraction": _as_float(target, "target_refraction"),
        "step": float(step),
        "iol_power": rounded_power,
        "iol_power_text": _format_power(rounded_power),
        "iol_power_exact": exact_power,
        "predicted_refraction": detail["refraction"],
        "elp": elp,
        "lens_factor": lens_factor,
        "a_constant": (
            _as_float(a_constant, "a_constant")
            if a_constant is not None
            else lens_factor_to_a_constant(lens_factor)
        ),
        "confidence": domain["confidence"],
        "low_confidence": domain["confidence"] == "LOW_CONFIDENCE",
        "warnings": warnings,
        "model": MODEL_ID,
        "model_note": MODEL_NOTE,
        "iol_options": build_iol_table(
            al_value,
            k_value,
            target=target,
            lf=lf,
            a_constant=a_constant,
            k_index=k_index,
            step=step,
            span=span,
            acd=acd,
            lt=lt,
            wtw=wtw,
            use_surgeon_inputs=use_surgeon_inputs,
        ),
    }


__all__ = [
    "MODEL_ID",
    "MODEL_NOTE",
    "OfflineInputError",
    "a_constant_to_lens_factor",
    "assess_input_domain",
    "build_iol_table",
    "iol_power_for_target",
    "lens_factor_to_a_constant",
    "normalize_k_to_reference",
    "predict_elp",
    "predict_refraction",
    "predict_refraction_detail",
    "solve_iol_power",
]
