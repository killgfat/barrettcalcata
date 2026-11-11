"""Castrop 公式的本地实现（Langenbucher 2021）。

模型眼有 4 个折射面：眼镜平面、角膜前表面、角膜后表面、薄 IOL；
折射率取 n_air=1.0、n_cornea=1.376、n_aqueous=1.336。

有效晶体位置（ELP，自角膜前顶点量到 IOL 主平面）::

    ELP = ACD + C*LT + H

ACD 是术前晶状体眼前房深度，LT 是晶状体厚度，C 是 Olsen 式的晶状体
厚度比例系数（典型 0.35~0.44），H 是 IOL 主平面相对晶状体赤道面的
轴向偏移。论文另给出把 AL 与角膜半径纳入的回归式，见 ELP_MODELS；
R 是把验光系统误差折算到屈光度的偏移，加在预测等效球镜上。

角膜前后表面分别折射，中间按角膜折射率传播；等效屈光力仅供诊断::

    PCA     = (nC - 1)/RCA
    PCP     = (n - nC)/RCP
    Pcornea = PCA + PCP - (dC/nC)*PCA*PCP

缺少术后角膜数据时按论文用固定比值推算：:

    RCP = RCA*6.4/7.77,  dC = 0.50 mm

眼轴先用 Cooke 回归折算成等效分段测量（论文第 4 点）::

    ALcor = 1.23854 + 0.95855*AL - 0.05467*LT

度数求解（predSE 为术后等效球镜）::

    Rg      = predSE - R
    Lspec   = Rg/(1 - dVD*Rg)
    Lfront  = Lspec + PCA
    Lback   = Lfront/(1 - (dC/nC)*Lfront) + PCP
    Liol    = Lback/(1 - ((ELP-dC)/n)*Lback)
    PIOL    = n/(ALcor - ELP) - Liol

上述传播式的长度用米；函数接口和诊断输出的长度仍用 mm。
反解 predSE 时按同一链条逆推，因此 target 往返自洽。

ULIB 快照（2016-10-31 停更）不包含 Castrop 的 C/H/R。常数只能来自
IOLCon 的 “Castrop(C / H / R)” 列，或由调用方直接给出 ELP；两者都没有
时退回论文的优化初值 C=0.40/H=0.00/R=0.00 并标注低置信度。
"""

from __future__ import annotations

from .common import (
    K_HARD_MAX,
    K_HARD_MIN,
    SPECTACLE_VERTEX_M,
    as_float,
    build_formula_result,
    normalize_k_to_reference,
    validate_eye,
)

LABEL = "Castrop"

CITATIONS = (
    (
        "Langenbucher A, Szentmáry N, Cayless A, Weisensee J, Fabian E, "
        "Wendelstein J, Hoffmann P. Considerations on the Castrop formula for "
        "calculation of intraocular lens power. PLoS One. 2021;16(6):e0252102."
    ),
    (
        "Hoffmann P, Langenbucher A. The Castrop IOL Formula. In: Cataract "
        "and Refractive Surgery. Springer; 2024. "
        "doi:10.1007/978-3-031-50666-6_38"
    ),
)

MODEL = "Castrop"
MODEL_NOTE = (
    "公开 Castrop 公式（Langenbucher 2021）：厚角膜 + 薄 IOL 的四折射面"
    "近轴聚散度模型；ELP 由术前 ACD/LT 与 C/H 推导（可选纳入 AL 与角膜"
    "半径的回归式），R 为折算到屈光度的系统偏移。"
)
DEFAULT_A_CONSTANT = 118.7

# 论文采用的折射率（前言 Methods 第 1 段）。
N_AIR = 1.0
N_CORNEA = 1.376
N_AQUEOUS = 1.336

# 曲率计折射率 1.3375 下 K = 337.5/R(mm)，用于把平均 K 换回前表面半径。
KERATOMETRY_MM = 337.5

# 论文给定的缺省值：角膜厚度 500 μm、后/前表面半径比 6.4/7.77。
DEFAULT_CCT_MM = 0.50
DEFAULT_POSTERIOR_RATIO = 6.4 / 7.77

# 论文常数优化的初始化三元组 C/H/R = 0.4/0/0。
DEFAULT_C = 0.40
DEFAULT_H = 0.0
DEFAULT_R = 0.0

# 缺少术前 ACD/LT 时的文档化缺省值，与 Haigis 的处理保持一致。
DEFAULT_ACD = 3.2
DEFAULT_LT = 4.6

# Cooke 眼轴回归（Kane/Cooke 的分段等效形式）。
COOKE_INTERCEPT = 1.23854
COOKE_AL_SLOPE = 0.95855
COOKE_LT_SLOPE = -0.05467

# ELP 推导方式：与 IOLCon 的 “ELP calculation” 三个选项一一对应。
ELP_MODEL_ACD_LT = "acd_lt"
ELP_MODEL_REGRESSION = "regression"
ELP_MODEL_REGRESSION_NO_R = "regression_no_r"
ELP_MODELS = (
    ELP_MODEL_ACD_LT,
    ELP_MODEL_REGRESSION,
    ELP_MODEL_REGRESSION_NO_R,
)

_ELP_MODEL_ALIASES = {
    "acd_lt": ELP_MODEL_ACD_LT,
    "acdlt": ELP_MODEL_ACD_LT,
    "acd": ELP_MODEL_ACD_LT,
    "default": ELP_MODEL_ACD_LT,
    "with_acd_lt": ELP_MODEL_ACD_LT,
    "regression": ELP_MODEL_REGRESSION,
    "with_al": ELP_MODEL_REGRESSION,
    "acd_al_r_lt": ELP_MODEL_REGRESSION,
    "with_acd_al_r_lt": ELP_MODEL_REGRESSION,
    "regression_no_r": ELP_MODEL_REGRESSION_NO_R,
    "no_r": ELP_MODEL_REGRESSION_NO_R,
    "acd_al_lt": ELP_MODEL_REGRESSION_NO_R,
    "with_acd_al_lt": ELP_MODEL_REGRESSION_NO_R,
}

# 输入合理范围。C 的临床取值落在 0.35~0.44，这里留出优化后的余量。
C_MIN, C_MAX = 0.20, 0.60
H_MIN, H_MAX = -1.0, 1.0
R_MIN, R_MAX = -1.0, 1.0
ELP_MIN, ELP_MAX = 2.0, 12.0
CCT_MIN, CCT_MAX = 0.3, 0.9
POSTERIOR_RATIO_MIN, POSTERIOR_RATIO_MAX = 0.6, 0.95

MISSING_ACD_WARNING = (
    "缺少术前 ACD，Castrop 的 ELP 无法按实测值推导，使用默认值 3.20 mm"
)
MISSING_LT_WARNING = (
    "缺少晶状体厚度 LT，Castrop 的 ELP 无法按实测值推导，使用默认值 4.60 mm"
)
DEFAULT_CONSTANTS_WARNING = (
    "未提供 Castrop C/H/R，使用论文优化初值 C=0.40/H=0.00/R=0.00；"
    "该组常数无晶体特异性，度数仅供参考"
)


def normalize_elp_model(value):
    """标准化 ELP 推导方式；空值回落到论文原式（ACD + C·LT + H）。"""
    if value is None:
        return ELP_MODEL_ACD_LT
    # IOLCon 的选项文字是 “with ACD, AL and LT”，这里把标点、and 一并
    # 归成下划线，让网页文案也能直接当参数值传进来。
    text = str(value).strip().lower().replace("and", "_")
    text = "".join(char if char.isalnum() else "_" for char in text)
    key = "_".join(part for part in text.split("_") if part)
    if not key:
        return ELP_MODEL_ACD_LT
    if key in _ELP_MODEL_ALIASES:
        return _ELP_MODEL_ALIASES[key]
    raise ValueError("castrop_elp_model 只支持 " + ", ".join(ELP_MODELS))


def _corneal_radius_mm(k_reference):
    """由 1.3375 基准的平均 K 反算角膜前表面平均半径（mm）。"""
    if k_reference <= 0:
        raise ValueError("K 必须为正数，无法换算角膜前表面半径")
    return KERATOMETRY_MM / k_reference


def corrected_al(al, lt):
    """Cooke 回归修正后的等效分段眼轴（mm）。"""
    al_value = as_float(al, "AL")
    lt_value = as_float(lt, "LenThickness")
    return COOKE_INTERCEPT + COOKE_AL_SLOPE * al_value + COOKE_LT_SLOPE * lt_value


def corneal_power(
    k,
    k_index=1.3375,
    cct=DEFAULT_CCT_MM,
    posterior_ratio=DEFAULT_POSTERIOR_RATIO,
):
    """返回厚透镜模型的角膜等效屈光度与几何参数。

    返回 dict：
      p_cornea  参考主平面的等效屈光度（D）
      p_front   前表面屈光度（D）
      p_back    后表面屈光度（D）
      r_front   前表面半径（mm）
      r_back    后表面半径（mm）
      cct       角膜厚度（mm）
    """
    k_value = as_float(k, "K")
    if not K_HARD_MIN <= k_value <= K_HARD_MAX:
        raise ValueError(
            f"K={k_value:.2f} D 超出可计算范围 {K_HARD_MIN:.0f}-{K_HARD_MAX:.0f} D"
        )
    k_ref = normalize_k_to_reference(k_value, k_index)
    cct_value = as_float(cct, "cct")
    if not CCT_MIN <= cct_value <= CCT_MAX:
        raise ValueError(
            f"cct={cct_value:.2f} mm 超出合理范围 {CCT_MIN:.1f}-{CCT_MAX:.1f} mm"
        )
    ratio_value = as_float(posterior_ratio, "posterior_ratio")
    if not POSTERIOR_RATIO_MIN <= ratio_value <= POSTERIOR_RATIO_MAX:
        raise ValueError(
            f"posterior_ratio={ratio_value:.3f} 超出合理范围 "
            f"{POSTERIOR_RATIO_MIN:.2f}-{POSTERIOR_RATIO_MAX:.2f}"
        )

    r_front = _corneal_radius_mm(k_ref)
    r_back = r_front * ratio_value
    # 屈光度用米制半径，避免 mm/m 混用。
    p_front = (N_CORNEA - N_AIR) / (r_front / 1000.0)
    p_back = (N_AQUEOUS - N_CORNEA) / (r_back / 1000.0)
    p_cornea = p_front + p_back - (cct_value / 1000.0 / N_CORNEA) * p_front * p_back
    return {
        "p_cornea": p_cornea,
        "p_front": p_front,
        "p_back": p_back,
        "r_front": r_front,
        "r_back": r_back,
        "cct": cct_value,
        "posterior_ratio": ratio_value,
        "k_reference": k_ref,
    }


def _constant_value(source, name):
    """从 dict/dataclass 取常数，兼容大小写写法。"""
    if source is None:
        return None
    if isinstance(source, dict):
        for key in (name, name.lower(), name.upper()):
            if key in source:
                return source[key]
        return None
    for attr in (name.lower(), name, name.upper()):
        if hasattr(source, attr):
            return getattr(source, attr)
    return None


def _resolve_constants(constants):
    """返回 (C, H, R, 是否有任何自定义常数)。缺项用论文初值补齐。"""
    if constants is None:
        return DEFAULT_C, DEFAULT_H, DEFAULT_R, False

    raw_c = _constant_value(constants, "C")
    raw_h = _constant_value(constants, "H")
    raw_r = _constant_value(constants, "R")
    provided = [value for value in (raw_c, raw_h, raw_r) if value not in (None, "")]

    c_value = DEFAULT_C if raw_c in (None, "") else as_float(raw_c, "C")
    h_value = DEFAULT_H if raw_h in (None, "") else as_float(raw_h, "H")
    r_value = DEFAULT_R if raw_r in (None, "") else as_float(raw_r, "R")

    if not C_MIN <= c_value <= C_MAX:
        raise ValueError(
            f"Castrop C={c_value:.3f} 超出合理范围 {C_MIN:.2f}-{C_MAX:.2f}"
        )
    if not H_MIN <= h_value <= H_MAX:
        raise ValueError(
            f"Castrop H={h_value:.3f} 超出合理范围 {H_MIN:.1f}-{H_MAX:.1f}"
        )
    if not R_MIN <= r_value <= R_MAX:
        raise ValueError(
            f"Castrop R={r_value:.3f} 超出合理范围 {R_MIN:.1f}-{R_MAX:.1f}"
        )
    return c_value, h_value, r_value, bool(provided)


def _elp_from_model(al, acd, lt, c, h, model, r_front):
    """按选定方式推导 ELP（mm）。"""
    if model == ELP_MODEL_REGRESSION:
        # Springer 版 recent 回归：含 AL 与角膜前表面平均半径。
        return 0.045 * al + 0.761 * acd - 0.042 * r_front + c * lt + h
    if model == ELP_MODEL_REGRESSION_NO_R:
        # 不含角膜半径的回归：角膜屈光术后或曲率不可靠时使用。
        return 0.036 * al + 0.753 * acd + c * lt + h
    # PLoS ONE 2021 原文的 Olsen 式：ACD + C·LT + H。
    return acd + c * lt + h


def _validate_elp(elp, al):
    """ELP 必须落在合理区间且短于眼轴。"""
    elp_value = as_float(elp, "ELP")
    if not ELP_MIN <= elp_value <= ELP_MAX:
        raise ValueError(
            f"ELP={elp_value:.2f} mm 超出合理范围 {ELP_MIN:.1f}-{ELP_MAX:.1f} mm"
        )
    if elp_value >= al:
        raise ValueError(f"ELP={elp_value:.2f} mm 不小于眼轴 AL={al:.2f} mm，无法求解")
    return elp_value


def _propagate(vergence, distance_mm, refractive_index):
    """沿给定介质传播聚散度；负距离用于反向传播。"""
    denominator = 1.0 - distance_mm / 1000.0 / refractive_index * vergence
    if abs(denominator) <= 1e-9:
        raise ValueError("角膜屈光度与传播距离组合导致 Castrop 公式发散")
    return vergence / denominator


def _power(al_cor, elp, cornea, target, r_offset):
    """由目标屈光度解 IOL 度数（D）。"""
    rg = target - r_offset
    denominator = 1.0 - SPECTACLE_VERTEX_M * rg
    if abs(denominator) <= 1e-9:
        raise ValueError("目标屈光度过大，无法折算到角膜前顶点")
    l_spec = rg / denominator
    l_front = l_spec + cornea["p_front"]
    l_back = (
        _propagate(l_front, cornea["cct"], N_CORNEA) + cornea["p_back"]
    )
    l_iol = _propagate(l_back, elp - cornea["cct"], N_AQUEOUS)
    axial = (al_cor - elp) / 1000.0
    if axial <= 1e-6:
        raise ValueError("ELP 与眼轴过于接近，Castrop 公式发散")
    return N_AQUEOUS / axial - l_iol


def _refraction(al_cor, elp, cornea, iol_power, r_offset):
    """由 IOL 度数反解预测等效球镜（D，眼镜平面）。"""
    axial = (al_cor - elp) / 1000.0
    if axial <= 1e-6:
        return float("nan")
    l_iol = N_AQUEOUS / axial - as_float(iol_power, "iol_power")
    try:
        l_back = _propagate(l_iol, cornea["cct"] - elp, N_AQUEOUS)
        l_front = _propagate(
            l_back - cornea["p_back"], -cornea["cct"], N_CORNEA
        )
    except ValueError:
        return float("nan")
    l_spec = l_front - cornea["p_front"]
    denominator = 1.0 + SPECTACLE_VERTEX_M * l_spec
    if abs(denominator) <= 1e-9:
        return float("nan")
    return l_spec / denominator + r_offset


def calculate(
    al,
    k,
    target=0.0,
    a_constant=DEFAULT_A_CONSTANT,
    k_index=1.3375,
    acd=None,
    lt=None,
    wtw=None,
    step=0.5,
    constants=None,
    elp=None,
    elp_model=None,
    cct=None,
    posterior_ratio=None,
    al_correction=True,
):
    """按统一返回结构计算 Castrop。

    constants 可传 dict 或带 C/H/R 属性的对象；缺项按论文初值补齐。
    elp 给定时直接使用该 ELP（IOLCon 或 AS-OCT 实测），不再走常数推导，
    但 R 仍作用于目标屈光度。wtw 仅为统一签名保留，Castrop 不使用。
    """
    al_value, k_value = validate_eye(al, k)
    k_index_value = as_float(k_index, "k_index")
    target_value = as_float(target, "target_refraction")
    a_value = as_float(a_constant, "a_constant")

    warnings = []
    c_value, h_value, r_value, custom_constants = _resolve_constants(constants)

    if acd is None:
        acd_value = DEFAULT_ACD
        warnings.append(MISSING_ACD_WARNING)
    else:
        acd_value = as_float(acd, "ACD")
    if lt is None:
        lt_value = DEFAULT_LT
        warnings.append(MISSING_LT_WARNING)
    else:
        lt_value = as_float(lt, "LenThickness")

    cornea = corneal_power(
        k_value,
        k_index_value,
        DEFAULT_CCT_MM if cct is None else cct,
        DEFAULT_POSTERIOR_RATIO if posterior_ratio is None else posterior_ratio,
    )
    p_cornea = cornea["p_cornea"]

    # 光学链里的眼轴始终是 Cooke 修正后的等效分段值（可关闭）。
    al_cor = corrected_al(al_value, lt_value) if al_correction else al_value

    if elp is not None:
        elp_value = _validate_elp(elp, al_value)
        elp_source = "provided"
        model_used = None
    else:
        model_used = normalize_elp_model(elp_model)
        elp_value = _validate_elp(
            _elp_from_model(
                al_cor,
                acd_value,
                lt_value,
                c_value,
                h_value,
                model_used,
                cornea["r_front"],
            ),
            al_value,
        )
        elp_source = model_used
        if not custom_constants:
            warnings.append(DEFAULT_CONSTANTS_WARNING)

    if not al_correction:
        warnings.append("已关闭 Cooke 眼轴修正，直接使用测量眼轴；与论文计算口径不同")
    if abs(al_cor - al_value) > 0.5:
        # 常态下 Cooke 修正只挪动 0.01~0.1 mm；超过 0.5 mm 说明 LT 异常，
        # 值得提示，否则每条结果都挂一条无信息量的警告。
        warnings.append(
            f"Cooke 修正后的眼轴 ALcor={al_cor:.2f} mm 与原始 "
            f"AL={al_value:.2f} mm 相差 {al_cor - al_value:+.2f} mm，"
            "请核对晶状体厚度"
        )

    exact_power = _power(al_cor, elp_value, cornea, target_value, r_value)

    def refraction_at(power):
        """返回该 IOL 度数对应的预测等效球镜。"""
        return _refraction(al_cor, elp_value, cornea, power, r_value)

    result = build_formula_result(
        al=al_value,
        k=k_value,
        target=target_value,
        step=step,
        exact_power=exact_power,
        refraction_for_power=refraction_at,
        elp=elp_value,
        a_constant=a_value,
        lens_factor=None,
        constants_text=(
            f"C={c_value:.3f}; H={h_value:.3f}; R={r_value:.3f}; "
            f"ELP={elp_value:.2f} mm（{elp_source}）; "
            f"Pcornea={p_cornea:.2f} D; ALcor={al_cor:.2f} mm"
        ),
        model=MODEL,
        model_note=MODEL_NOTE,
        warnings=warnings,
    )
    result["castrop"] = {
        "C": c_value,
        "H": h_value,
        "R": r_value,
        "elp": elp_value,
        "elp_source": elp_source,
        "elp_model": model_used,
        "al_measured": al_value,
        "al_corrected": al_cor,
        "al_correction": bool(al_correction),
        "acd": acd_value,
        "lt": lt_value,
        "acd_defaulted": acd is None,
        "lt_defaulted": lt is None,
        "constants_provided": custom_constants,
        **cornea,
    }
    return result


def refraction_for_power(
    al,
    k,
    iol_power,
    a_constant=DEFAULT_A_CONSTANT,
    k_index=1.3375,
    acd=None,
    lt=None,
    constants=None,
    elp=None,
    elp_model=None,
    cct=None,
    posterior_ratio=None,
    al_correction=True,
):
    """给定 IOL 度数，返回 Castrop 预测等效球镜（D，眼镜平面）。"""
    result = calculate(
        al,
        k,
        target=0.0,
        a_constant=a_constant,
        k_index=k_index,
        acd=acd,
        lt=lt,
        step=0.5,
        constants=constants,
        elp=elp,
        elp_model=elp_model,
        cct=cct,
        posterior_ratio=posterior_ratio,
        al_correction=al_correction,
    )
    # 用同一套几何复算，避免从候选表反查。
    detail = result["castrop"]
    return _refraction(
        detail["al_corrected"],
        detail["elp"],
        detail,
        iol_power,
        detail["R"],
    )


__all__ = [
    "CITATIONS",
    "DEFAULT_C",
    "DEFAULT_H",
    "DEFAULT_R",
    "ELP_MODELS",
    "LABEL",
    "calculate",
    "corneal_power",
    "corrected_al",
    "normalize_elp_model",
    "refraction_for_power",
]
