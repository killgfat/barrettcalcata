"""SRK/T 公式的本地实现（Retzlaff 1990）。

公式使用平均角膜屈光度与 A 常数推导术后前房深度，并对角膜穹隆高度、
视网膜厚度做经验修正：:

    R     = 337.5 / K'
    Lcor  = AL                          (AL <= 24.2)
            其余 -3.446 + 1.716*AL - 0.0237*AL^2
    CW    = -5.41 + 0.58412*Lcor + 0.098*K'
    H     = R - sqrt(R^2 - CW^2/4)
    ACD   = 0.62467*A - 68.747 + H - 3.336
    ALopt = AL + 0.65696 - 0.02029*AL
    P     = 1000*n_a*(n_a*R - (n_c-1)*ALopt)
            / ((ALopt - ACD)*(n_a*R - (n_c-1)*ACD))

n_a = 1.336，n_c = 1.333。K' 是目标屈光度折算到角膜平面后的等效屈光度::

    K' = K + Rx / (1 - 0.012*Rx)

与 scripts/calibrate_offline.py::srkt_power 的差异
=================================================
校准脚本把目标屈光度写成多项式形式 ``- 0.001*Rx*(V*(...)+...)``（分子、
分母各一项）。该写法的数值行为是 dP/dRx ≈ +0.0175 D/D（AL=23.5、K=44、
A=118.7），符号与量级都不符合临床（真实约为 -1.3 D/D），反解出的预测屈光
度也不会跟随 target。本模块改为用上面的 K' 替换 K 并去掉两个 0.001*Rx 项：
Rx=0 时 K'=K、两项为 0，所以 target=0 的结果与校准脚本逐位一致（校准脚本
只在 target=0 使用 SRK/T 对照，因此 docs 里的校准指标不受影响）；非零
target 时 dP/dRx ≈ -1.1 D/D，与 Barrett/Hoffer Q/Haigis 的目标处理一致。
"""

from __future__ import annotations

import math

from .common import (
    N_AQUEOUS,
    SPECTACLE_VERTEX_M,
    as_float,
    build_formula_result,
    normalize_k_to_reference,
    validate_eye,
)

LABEL = "SRK/T"

CITATIONS = (
    (
        "Retzlaff JA, Sanders DR, Kraff MC. Development of the SRK/T "
        "intraocular lens implant power calculation formula. J Cataract "
        "Refract Surg. 1990;16(3):333-340."
    ),
)

MODEL = "SRK/T"
MODEL_NOTE = (
    "公开 SRK/T 公式（Retzlaff 1990）：平均 K + A 常数推导 ACD，"
    "含角膜穹隆高度与视网膜厚度修正。"
)
DEFAULT_A_CONSTANT = 118.7

N_CORNEA = 1.333
KERATOMETRY_MM = 337.5  # 1.3375 折射率下 K = 337.5 / R

# 反解 target 的搜索区间（眼镜平面屈光度，D）。
TARGET_SEARCH_MIN = -25.0
TARGET_SEARCH_MAX = 25.0
BISECTION_STEPS = 100


def _corneal_target(target, vertex=SPECTACLE_VERTEX_M):
    """把眼镜平面目标屈光度折算到角膜平面（SRK/T 自己的目标处理）。"""
    target_value = as_float(target, "target_refraction")
    denominator = 1.0 - vertex * target_value
    if denominator <= 1e-6:
        raise ValueError("target_refraction 过大，无法折算到角膜平面")
    return target_value / denominator


def _acd(al, k_prime, a_constant):
    """SRK/T 推导出的有效晶体位置（即 ACD，mm）。"""
    radius = KERATOMETRY_MM / k_prime
    if al <= 24.2:
        lcor = al
    else:
        lcor = -3.446 + 1.716 * al - 0.0237 * al * al
    corneal_width = -5.41 + 0.58412 * lcor + 0.098 * k_prime
    discriminant = radius * radius - corneal_width * corneal_width / 4.0
    height = radius - math.sqrt(discriminant) if discriminant > 0 else radius
    return 0.62467 * a_constant - 68.747 + height - 3.336


def _power_for_elp(al, k_prime, elp):
    """给定 ACD 求正视所需的精确 IOL 度数。"""
    radius = KERATOMETRY_MM / k_prime
    al_optical = al + 0.65696 - 0.02029 * al
    first = N_AQUEOUS * radius - (N_CORNEA - 1.0) * al_optical
    second = N_AQUEOUS * radius - (N_CORNEA - 1.0) * elp
    denominator = (al_optical - elp) * second
    if abs(denominator) <= 1e-12:
        raise ValueError("SRK/T 公式发散：参数组合无法求出度数")
    return 1000.0 * N_AQUEOUS * first / denominator


def _power(al, k_ref, a_constant, target):
    """给定眼镜平面目标屈光度，求精确 IOL 度数。

    ELP 只由术前 AL/K 与 A 常数决定，不随目标屈光度改变；目标屈光度只
    通过 K' 进入光学度数计算。
    """
    elp = _acd(al, k_ref, a_constant)
    k_prime = k_ref + _corneal_target(target)
    return _power_for_elp(al, k_prime, elp)


def _refraction(al, k_ref, a_constant, iol_power):
    """由同一 SRK/T 公式反解预测屈光度（二分法，P 随 target 单调递减）。"""
    low = TARGET_SEARCH_MIN
    high = TARGET_SEARCH_MAX
    low_power = _power(al, k_ref, a_constant, low)
    high_power = _power(al, k_ref, a_constant, high)
    if not low_power >= iol_power >= high_power:
        return float("nan")
    for _ in range(BISECTION_STEPS):
        middle = (low + high) / 2.0
        if _power(al, k_ref, a_constant, middle) > iol_power:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def refraction_for_power(
    al,
    k,
    iol_power,
    a_constant=DEFAULT_A_CONSTANT,
    k_index=1.3375,
):
    """给定 IOL 度数，返回 SRK/T 预测屈光度（D，眼镜平面）。"""
    al_value, k_value = validate_eye(al, k)
    k_ref = normalize_k_to_reference(k_value, k_index)
    return _refraction(
        al_value,
        k_ref,
        as_float(a_constant, "a_constant"),
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
    """按统一返回结构计算 SRK/T。

    acd/lt/wtw 仅为统一各公式签名而保留：SRK/T 自行推导前房深度，不使用
    术前实测的 ACD、晶体厚度和白到白距离。
    """
    al_value, k_value = validate_eye(al, k)
    k_index_value = as_float(k_index, "k_index")
    k_ref = normalize_k_to_reference(k_value, k_index_value)
    a_value = as_float(a_constant, "a_constant")
    target_value = as_float(target, "target_refraction")

    # ELP 用术前 K 推导，目标屈光度只影响光学部分的 K'。
    elp = _acd(al_value, k_ref, a_value)
    k_prime = k_ref + _corneal_target(target_value)
    exact_power = _power_for_elp(al_value, k_prime, elp)

    def refraction_at(power):
        """返回该 IOL 度数对应的预测屈光度。"""
        return _refraction(al_value, k_ref, a_value, power)

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
        constants_text=(f"A={a_value:.2f}; ACD={elp:.2f} mm; K index={k_index_value}"),
        model=MODEL,
        model_note=MODEL_NOTE,
    )


__all__ = [
    "CITATIONS",
    "LABEL",
    "calculate",
    "refraction_for_power",
]
