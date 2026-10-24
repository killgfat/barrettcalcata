"""Haigis 公式的本地实现（Haigis 2000）。

三常数形式：:

    d  = a0 + a1*ACD + a2*AL
    P  = 1336/(AL-d) - 1336/(1336/K' - d)

其中 K' 为目标屈光度折算到角膜平面后的等效角膜屈光度。

A 常数只用于推导默认的 a0（0.62467*A - 72.434），这是由 A 常数换算得到的
近似起点，不是 Haigis 优化后的三常数（优化需要术前术后 IOL Master 数据
做最小二乘拟合）。若调用方提供术前实测 ACD，请一并给出优化后的 a0/a1/a2。
"""

from __future__ import annotations

from .common import (
    VERGENCE_SCALE,
    as_float,
    build_formula_result,
    corneal_target,
    invert_vergence_target,
    normalize_k_to_reference,
    validate_eye,
)

LABEL = "Haigis"

CITATIONS = (
    (
        "Haigis W, Lege B, Miller N, Schneider B. Comparison of immersion "
        "ultrasound biometry and partial coherence interferometry for "
        "intraocular lens calculation according to Haigis. Graefes Arch Clin "
        "Exp Ophthalmol. 2000;238(9):765-773."
    ),
)

MODEL = "Haigis"
MODEL_NOTE = (
    "公开 Haigis 三常数公式（2000）：a1=0.40、a2=0.10 为经典取值，"
    "a0 由 A 常数换算得到，并非个体化优化结果。"
)
DEFAULT_A_CONSTANT = 118.7

A1 = 0.4
A2 = 0.1
A0_SLOPE = 0.62467
A0_INTERCEPT = -72.434
DEFAULT_ACD = 3.2

# Haigis 的角膜屈光度约定：Dc = 331.5 / r（折射率 1.3315）。
HAIGIS_KERATOMETRY_MM = 331.5
REFERENCE_KERATOMETRY_MM = 337.5

MISSING_ACD_WARNING = "缺少术前 ACD，使用默认值 3.20 mm（Haigis 建议使用实测 ACD）"


def _a0(a_constant):
    """由 A 常数换算的近似 a0 常数。"""
    return A0_SLOPE * a_constant + A0_INTERCEPT


def _haigis_k(k_reference):
    """把 1.3375 基准的 K 折算为 Haigis 的 1.3315 基准 Dc。"""
    return k_reference * HAIGIS_KERATOMETRY_MM / REFERENCE_KERATOMETRY_MM


def _elp(al, acd, a0):
    """Haigis 的有效晶体位置 d（mm，自角膜顶点起算）。"""
    return a0 + A1 * acd + A2 * al


def _power(al, elp, k_target):
    """给定 ELP 与角膜平面目标 K'，求精确 IOL 度数。"""
    if al - elp <= 1e-6:
        raise ValueError("AL 与 ELP 过于接近，Haigis 公式发散")
    cornea_term = VERGENCE_SCALE / k_target - elp
    if cornea_term <= 1e-6:
        raise ValueError("角膜屈光度与 ELP 组合导致 Haigis 公式发散")
    return VERGENCE_SCALE / (al - elp) - VERGENCE_SCALE / cornea_term


def refraction_for_power(
    al,
    k,
    iol_power,
    a_constant=DEFAULT_A_CONSTANT,
    k_index=1.3375,
    acd=None,
):
    """给定 IOL 度数，返回 Haigis 预测屈光度（D，眼镜平面）。

    acd 缺省时使用 3.20 mm，与 calculate 的缺省处理保持一致。
    """
    al_value, k_value = validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    a_value = as_float(a_constant, "a_constant")
    acd_value = DEFAULT_ACD if acd is None else as_float(acd, "ACD")
    elp = _elp(al_value, acd_value, _a0(a_value))
    return invert_vergence_target(
        al_value,
        elp,
        _haigis_k(k_ref),
        as_float(iol_power, "iol_power"),
    )


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
):
    """按统一返回结构计算 Haigis。

    lt/wtw 仅为统一各公式签名而保留：Haigis 三常数形式不使用晶体厚度和
    白到白距离。acd 缺省时按 3.20 mm 计算并标记低置信度。
    """
    al_value, k_value = validate_eye(al, k)
    k_index_value = as_float(k_index, "k_index")
    k_ref = normalize_k_to_reference(k_value, k_index_value)
    a_value = as_float(a_constant, "a_constant")
    target_value = as_float(target, "target_refraction")

    warnings = []
    if acd is None:
        acd_value = DEFAULT_ACD
        warnings.append(MISSING_ACD_WARNING)
    else:
        acd_value = as_float(acd, "ACD")

    a0 = _a0(a_value)
    elp = _elp(al_value, acd_value, a0)
    k_haigis = _haigis_k(k_ref)
    exact_power = _power(
        al_value,
        elp,
        k_haigis + corneal_target(target_value),
    )

    def refraction_at(power):
        """返回该 IOL 度数对应的预测屈光度。"""
        return invert_vergence_target(al_value, elp, k_haigis, power)

    return build_formula_result(
        al=al_value,
        k=k_value,
        target=target_value,
        step=step,
        exact_power=exact_power,
        refraction_for_power=refraction_at,
        elp=elp,
        a_constant=a_value,
        lens_factor=None,
        constants_text=(
            f"A={a_value:.2f}; a0={a0:.2f}; a1={A1:.2f}; a2={A2:.2f}; "
            f"ACD={acd_value:.2f} mm; K(1.3315)={k_haigis:.2f} D"
        ),
        model=MODEL,
        model_note=MODEL_NOTE,
        warnings=warnings,
    )


__all__ = [
    "CITATIONS",
    "LABEL",
    "calculate",
    "refraction_for_power",
]
