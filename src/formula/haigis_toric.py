"""Haigis-T 的公开框架近轴实现，不声称复刻设备的完整 Haigis-T。

球镜直接复用 haigis.calculate；散光在同一 ELP 下按主平面聚散度传播。
Haigis 2009（PMID 19523090）支持近轴矩阵路线；Fabian & Wehner 2019
（PMID 31185101）支持区分 K 与包含后表面的 TK。

UNVERIFIED-PENDING-PRIMARY：任务所列 Haigis 2015;31(10):669-676 的
题名/全文未能核实。此模块的矩阵化简、前表面 K-index 换算及 PCA 代理
不能据此宣称为原文逐式实现，详见 docs/formulas.md。
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from . import common, haigis
from .types import HaigisConstants

LABEL = "Haigis-T（公开框架近轴实现）"
MODEL = "Haigis-T-paraxial"
MODEL_NOTE = (
    "球镜/ELP 复用 Haigis；散光使用主平面近轴传播及双角矢量。"
    "UNVERIFIED-PENDING-PRIMARY：未核实完整 Haigis-T 一手算法，"
    "不保证与 IOL Master Haigis-T 等价。"
)
CITATIONS = haigis.CITATIONS + (
    (
        "Haigis W. IOL calculation using paraxial matrix optics. "
        "Ophthalmic Physiol Opt. 2009;29(4):458-463. PMID 19523090."
    ),
    (
        "Fabian E, Wehner W. Prediction Accuracy of Total Keratometry "
        "Compared to Standard Keratometry Using Different Intraocular "
        "Lens Power Formulas. J Refract Surg. 2019;35(6):362-368. "
        "PMID 31185101."
    ),
    (
        "Koch DD et al. Contribution of posterior corneal astigmatism "
        "to total corneal astigmatism. J Cataract Refract Surg. "
        "2012;38(12):2080-2087. PMID 23069271."
    ),
)

# UNVERIFIED-PENDING-PRIMARY：固定 0.30 D ATR 仅为显式启用的 PCA 代理，
# 不是已证实的 Haigis-T 系数。Koch 2012 的群体平均量值不能代替个体测量，
# 也不能证实 Haigis-T 使用该定值/轴位。默认不启用。
ESTIMATED_PCA_CYLINDER = 0.30
ESTIMATED_PCA_AXIS = 0.0

OPTIONAL_INPUTS = (
    "iol_cylinder",
    "iol_axis",
    "iol_spherical_equivalent",
    "posterior_mode",
    "posterior_cylinder",
    "posterior_axis",
    "total_cylinder",
    "total_axis",
    "total_source",
    "incision_sia",
    "incision_location",
    "cylinder_powers",
)


def _axis(value: Any, name: str, maximum: float = 180) -> float:
    angle = common.as_float(value, name)
    if not 0 <= angle <= maximum:
        raise ValueError(f"{name} 必须在 0~{maximum:g} 度之间")
    return angle % 180


def _magnitude(value: Any, name: str) -> float:
    cylinder = common.as_float(value, name)
    if cylinder < 0:
        raise ValueError(f"{name} 必须为非负柱镜量值")
    return cylinder


def iol_to_cornea_factor(
    al: float, elp: float, iol_spherical_equivalent: float, cylinder: float
) -> float:
    """返回 IOL 柱镜乘数；C_cornea = C_IOL * factor（角膜平面）。

    长度取 mm：t=d/(1000*n)，B=1000*n/(AL-d)-P_SE，G(B)=B/(1+t*B)。
    对 IOL 两主子午线 P_SE±C/2 传播后相减，得到
    factor=1/((1+t*B)^2-(t*C/2)^2)。不使用固定的 1/1.46。
    这是主平面等效薄透镜的近轴矩阵化简；不引入未经公开的 IOL 厚度、
    折射率或前后表面弯曲系数。
    """
    al_value = common.as_float(al, "AL")
    d = common.as_float(elp, "ELP")
    power = common.as_float(
        iol_spherical_equivalent, "iol_spherical_equivalent"
    )
    cyl = _magnitude(cylinder, "iol_cylinder")
    if not 0 < d < al_value:
        raise ValueError("ELP 必须为正且小于 AL")
    t = d / common.VERGENCE_SCALE
    b = common.VERGENCE_SCALE / (al_value - d) - power
    low = 1 + t * (b - cyl / 2)
    high = 1 + t * (b + cyl / 2)
    if min(low, high) <= 1e-10:
        raise ValueError("IOL 柱镜与 ELP 组合导致近轴传播发散")
    return 1 / (low * high)


def _residual(
    net: tuple[float, float], cylinder: float, axis: float, factor: float
) -> dict[str, Any]:
    correction = common.astigmatism_vector(cylinder * factor, axis)
    return {
        **common.vector_astigmatism(
            net[0] - correction[0], net[1] - correction[1]
        ),
        "plane": "corneal",
    }


def calculate(
    al: float,
    k: float,
    target: float = 0.0,
    a_constant: float = haigis.DEFAULT_A_CONSTANT,
    k_index: float = common.K_INDEX_REF,
    acd: float | None = None,
    lt: float | None = None,
    wtw: float | None = None,
    step: float = 0.5,
    constants: HaigisConstants | dict | None = None,
    *,
    k1: float,
    k2: float,
    k1_axis: float,
    k2_axis: float,
    iol_cylinder: float = 0.0,
    iol_axis: float | None = None,
    iol_spherical_equivalent: float | None = None,
    posterior_mode: str = "none",
    posterior_cylinder: float | None = None,
    posterior_axis: float | None = None,
    total_cylinder: float | None = None,
    total_axis: float | None = None,
    total_source: str | None = None,
    incision_sia: float = 0.0,
    incision_location: float | None = None,
    cylinder_powers: Sequence[float] | None = None,
) -> dict[str, Any]:
    """计算球镜 SE、实际植入残余散光及可供柱镜档位的推荐。

    k 必须等于 (k1+k2)/2，保持普通公式的统一签名。ACD 和完整三常数
    必填。输入 K 是角膜曲率计 D；实测 PCA/总散光是角膜平面光学 D。
    轴表示光学强子午线；iol_axis 是 IOL 弱子午线的对齐方向。
    incision_sia 是沿切口位置的扁平化量，默认 0，不猜测切口位置。
    cylinder_powers 是调用者提供的 IOL 平面可供档位；不内置厂商库存。
    """
    al_value, k_value = common.validate_eye(al, k)
    _, flat = common.validate_eye(al_value, k1)
    _, steep = common.validate_eye(al_value, k2)
    if steep < flat:
        raise ValueError("K2 必须不小于 K1")
    if not math.isclose(k_value, (flat + steep) / 2, abs_tol=1e-9):
        raise ValueError("K 必须等于 (K1+K2)/2")
    flat_axis = _axis(k1_axis, "K1Axis")
    steep_axis = _axis(k2_axis, "K2Axis")
    if not math.isclose((steep_axis - flat_axis) % 180, 90, abs_tol=1e-6):
        raise ValueError("K1Axis 与 K2Axis 必须正交；只支持规则散光")
    if acd is None:
        raise ValueError("Haigis-T 必须提供术前实测 ACD")
    acd_value = round(common.as_float(acd, "ACD"), 2)
    common.validate_optional_measurements(acd=acd_value, target=target)
    if constants is None:
        raise ValueError("Haigis-T 必须提供 haigis_constants.a0/a1/a2")
    if isinstance(constants, HaigisConstants):
        constants = vars(constants)
    resolved = HaigisConstants.from_mapping(constants)
    a_value = common.parse_a_constant(a_constant)
    index = common.normalize_k_index(k_index)
    spherical = haigis.calculate(
        al_value,
        k_value,
        target=target,
        a_constant=a_value,
        k_index=index,
        acd=acd_value,
        step=common.parse_step(step),
        constants=resolved,
    )
    d = spherical["elp"]
    # UNVERIFIED-PENDING-PRIMARY：对两子午线沿用球镜的 1.3315 约定，
    # 保证无 PCA/SICA 时与现有 Haigis 的两子午线传播一致；尚未确认
    # 商用 Haigis-T 对散光也作同样换算。
    flat_effective = haigis._haigis_k(
        common.normalize_k_to_reference(flat, index)
    )
    steep_effective = haigis._haigis_k(
        common.normalize_k_to_reference(steep, index)
    )
    anterior = common.astigmatism_vector(
        steep_effective - flat_effective, steep_axis
    )
    if not isinstance(posterior_mode, str) or posterior_mode not in {
        "none",
        "measured",
        "estimated",
        "total",
    }:
        raise ValueError("posterior_mode 只支持 none/measured/estimated/total")
    posterior = (0.0, 0.0)
    warnings = list(spherical["warnings"]) + [MODEL_NOTE]
    if posterior_mode == "measured":
        posterior = common.astigmatism_vector(
            _magnitude(posterior_cylinder, "posterior_cylinder"),
            _axis(posterior_axis, "posterior_axis"),
        )
    elif posterior_cylinder is not None or posterior_axis is not None:
        raise ValueError(
            "posterior_cylinder/axis 只适用于 measured，禁止重复 PCA"
        )
    if posterior_mode == "estimated":
        posterior = common.astigmatism_vector(
            ESTIMATED_PCA_CYLINDER, ESTIMATED_PCA_AXIS
        )
        warnings.append(
            "UNVERIFIED-PENDING-PRIMARY：PCA 使用固定 0.30 D @0 度 ATR 代理，"
            "不是已证实的 Haigis-T 系数或个体化 PCA 预测"
        )
    elif posterior_mode == "none":
        warnings.append("PCA 未计入：WTR 可能过矫、ATR 可能欠矫")
    if posterior_mode == "total":
        if not isinstance(total_source, str) or total_source not in {
            "TK",
            "TCRP",
        }:
            raise ValueError("total_source 必须为 TK 或 TCRP")
        corneal = common.astigmatism_vector(
            _magnitude(total_cylinder, "total_cylinder"),
            _axis(total_axis, "total_axis"),
        )
        warnings.append(
            "实测总散光替换前表面/PCA 矢量；球镜仍使用前表面平均 K，"
            "未将 TK 与 TCRP 的平均屈光力视为可互换"
        )
    else:
        if any(
            v is not None for v in (total_cylinder, total_axis, total_source)
        ):
            raise ValueError("total_cylinder/axis/source 只适用于 total")
        corneal = (anterior[0] + posterior[0], anterior[1] + posterior[1])
    sia = _magnitude(incision_sia, "incision_sia")
    incision = None
    if incision_location is not None:
        incision = _axis(incision_location, "incision_location", 360)
    elif sia:
        raise ValueError("非零 incision_sia 必须提供 incision_location")
    sica = common.astigmatism_vector(-sia, incision or 0)
    net = (corneal[0] + sica[0], corneal[1] + sica[1])
    net_result = common.vector_astigmatism(*net)
    mean_k = (flat_effective + steep_effective) / 2
    if mean_k - net_result["cylinder"] / 2 <= 0:
        raise ValueError("总散光导致角膜主子午线屈光力非正")

    cyl = _magnitude(iol_cylinder, "iol_cylinder")
    if iol_axis is None and cyl:
        raise ValueError("非零 iol_cylinder 必须提供 iol_axis")
    implant_axis = _axis(iol_axis, "iol_axis") if iol_axis is not None else 0.0
    power = (
        spherical["iol_power"]
        if iol_spherical_equivalent is None
        else common.as_float(
            iol_spherical_equivalent, "iol_spherical_equivalent"
        )
    )
    if not common.IOL_TABLE_MIN <= power <= common.IOL_TABLE_MAX:
        raise ValueError(
            "iol_spherical_equivalent 超出支持范围 "
            f"{common.IOL_TABLE_MIN:g}~{common.IOL_TABLE_MAX:g} D"
        )
    factor = iol_to_cornea_factor(al_value, d, power, cyl)
    # 由 Cc=Ci/(h²-(t*Ci/2)²) 解析反解 Ci，避免二次方程相减消差。
    t = d / common.VERGENCE_SCALE
    b = common.VERGENCE_SCALE / (al_value - d) - power
    h = 1 + t * b
    c = net_result["cylinder"]
    exact_cylinder = 2 * c * h * h / (1 + math.hypot(1, c * t * h))
    options = []
    if cylinder_powers is not None:
        if (
            not isinstance(cylinder_powers, (list, tuple))
            or not cylinder_powers
        ):
            raise ValueError("cylinder_powers 必须是非空数值数组")
        powers = sorted(
            {_magnitude(value, "cylinder_powers") for value in cylinder_powers}
        )
        for candidate in powers:
            candidate_factor = iol_to_cornea_factor(
                al_value, d, power, candidate
            )
            options.append(
                {
                    "iol_cylinder": candidate,
                    "axis": net_result["axis"],
                    "corneal_factor": candidate_factor,
                    "corneal_correction": candidate * candidate_factor,
                    "residual_astigmatism": _residual(
                        net,
                        candidate,
                        net_result["axis"] or 0,
                        candidate_factor,
                    ),
                    "recommended": False,
                }
            )
        best = min(
            options, key=lambda row: row["residual_astigmatism"]["cylinder"]
        )
        best["recommended"] = True
        recommended = best["iol_cylinder"]
    else:
        recommended = None
        warnings.append(
            "未提供 cylinder_powers，仅给连续柱镜解，不猜测可供档位"
        )

    posterior_result = common.vector_astigmatism(*posterior)
    total_result = common.vector_astigmatism(*corneal)
    return {
        **spherical,
        "model": MODEL,
        "model_note": MODEL_NOTE,
        "warnings": warnings,
        "confidence": "LOW_CONFIDENCE",
        "low_confidence": True,
        "posterior_mode": posterior_mode,
        "anterior_astigmatism": common.vector_astigmatism(*anterior),
        "posterior_astigmatism": (
            None if posterior_mode == "total" else posterior_result
        ),
        "net_astigmatism": net_result,
        "iol_spherical_equivalent": power,
        "iol_cylinder": cyl,
        "iol_axis": implant_axis if iol_axis is not None else None,
        "corneal_factor": factor,
        "corneal_correction": cyl * factor,
        "residual_astigmatism": _residual(net, cyl, implant_axis, factor),
        "recommended_iol_cylinder_exact": exact_cylinder,
        "recommended_iol_cylinder": recommended,
        "recommended_axis": net_result["axis"],
        "toric_options": options,
        "used_toric_inputs": {
            "K1": flat,
            "K2": steep,
            "K1Axis": flat_axis,
            "K2Axis": steep_axis,
            "ACD": acd_value,
            "posterior_mode": posterior_mode,
            "posterior_cylinder": (
                posterior_result["cylinder"]
                if posterior_mode in {"estimated", "measured"}
                else None
            ),
            "posterior_axis": (
                posterior_result["axis"]
                if posterior_mode in {"estimated", "measured"}
                else None
            ),
            "total_cylinder": (
                total_result["cylinder"] if posterior_mode == "total" else None
            ),
            "total_axis": (
                total_result["axis"] if posterior_mode == "total" else None
            ),
            "total_source": total_source,
            "incision_sia": sia,
            "incision_location": incision,
            "iol_cylinder": cyl,
            "iol_axis": implant_axis if iol_axis is not None else None,
            "iol_spherical_equivalent": power,
            "cylinder_powers": [row["iol_cylinder"] for row in options],
        },
    }


__all__ = ["CITATIONS", "LABEL", "calculate", "iol_to_cornea_factor"]
