"""公式调度层：唯一对外计算入口。

- 名称/模式标准化与能力检查在这里完成；
- 本地公式模块只负责光学算法，不读取 HTTP request；
- 在线 Barrett/Toric 适配器负责官网请求；
- 本模块只组装统一输出，不实现 ELP、折射率转换或目标屈光反解。
"""

from __future__ import annotations

import math

from . import (
    barrett,
    barrett_online,
    barrett_toric,
    common,
    constants,
    haigis,
    haigis_toric,
    hoffer_q,
    iol_models,
    srkt,
)
from .types import (
    CalculationRequest,
    FormulaCapabilities,
    InputValidationError,
    ToricCalculationRequest,
    UnsupportedFormulaError,
    UnsupportedModeError,
)

FORMULA_LABELS = {
    "barrett": "Barrett Universal II",
    "srkt": "SRK/T",
    "hoffer_q": "Hoffer Q",
    "haigis": "Haigis",
    "haigis-toric": haigis_toric.LABEL,
}

FORMULA_NAMES = tuple(FORMULA_LABELS)

# 计算模型 = 公式 + 执行方式的显式组合。API 的新契约使用这个名称。
CALCULATION_MODELS = {
    "barrett_ii_offline": ("barrett", "offline"),
    "barrett_ii": ("barrett", "online"),
    "srkt": ("srkt", "offline"),
    "hoffer_q": ("hoffer_q", "offline"),
    "haigis": ("haigis", "offline"),
    "haigis-toric": ("haigis-toric", "offline"),
}

CALCULATION_MODEL_LABELS = {
    "barrett_ii_offline": "Barrett Universal II（离线）",
    "barrett_ii": "Barrett Universal II（在线）",
    "srkt": "SRK/T",
    "hoffer_q": "Hoffer Q",
    "haigis": "Haigis",
    "haigis-toric": haigis_toric.LABEL,
}

TORIC_CALCULATION_MODEL = "barrett_ii_toric"
TORIC_CALCULATION_MODEL_LABEL = "Barrett Universal II Toric（在线）"

CAPABILITIES = {
    "haigis-toric": FormulaCapabilities(
        name="haigis-toric",
        label=haigis_toric.LABEL,
        modes=("offline",),
        required_inputs=("AL", "K1", "K2", "K1Axis", "K2Axis", "ACD"),
        optional_inputs=haigis_toric.OPTIONAL_INPUTS,
        ignored_inputs=("LenThickness", "WTW"),
        constants="haigis_constants(a0/a1/a2)，必须提供完整三常数",
        supports_toric=True,
    ),
    "barrett": FormulaCapabilities(
        name="barrett",
        label="Barrett Universal II",
        modes=("offline", "online"),
        required_inputs=("AL", "K1", "K2"),
        optional_inputs=("ACD", "LenThickness", "WTW"),
        ignored_inputs=(),
        constants="A-constant / Lens Factor",
        supports_toric=True,
    ),
    "srkt": FormulaCapabilities(
        name="srkt",
        label="SRK/T",
        modes=("offline",),
        required_inputs=("AL", "K1", "K2"),
        optional_inputs=(),
        ignored_inputs=("ACD", "LenThickness", "WTW"),
        constants="A-constant",
    ),
    "hoffer_q": FormulaCapabilities(
        name="hoffer_q",
        label="Hoffer Q",
        modes=("offline",),
        required_inputs=("AL", "K1", "K2"),
        optional_inputs=(),
        ignored_inputs=("ACD", "LenThickness", "WTW"),
        constants="A-constant（推导 pACD）；或 hoffer_q_pacd（报告中的 pACD）",
    ),
    "haigis": FormulaCapabilities(
        name="haigis",
        label="Haigis",
        modes=("offline",),
        required_inputs=("AL", "K1", "K2"),
        optional_inputs=("ACD",),
        ignored_inputs=("LenThickness", "WTW"),
        constants=(
            "A-constant（推导近似 a0）；a1=0.40，a2=0.10；或 haigis_constants(a0/a1/a2)"
        ),
    ),
}

_MODULES = {
    "barrett": barrett,
    "srkt": srkt,
    "hoffer_q": hoffer_q,
    "haigis": haigis,
    "haigis-toric": haigis_toric,
}

# 官网普通 Barrett 适配器在 ACD 缺失时沿用的默认值（与官网表单一致）。
ONLINE_DEFAULT_ACD = 3.00


def normalize_calculation_model(value):
    """标准化计算模型名称；None/空返回 None。"""
    if value is None:
        return None
    model = str(value).strip().lower()
    if not model:
        return None
    if model not in CALCULATION_MODELS:
        raise UnsupportedFormulaError("model 只支持 " + ", ".join(CALCULATION_MODELS))
    return model


def calculation_model_for(formula, mode):
    """由旧 formula/mode 推导等价的 calculation model。"""
    if formula == "barrett":
        return "barrett_ii" if mode == "online" else "barrett_ii_offline"
    return formula


def get_calculation_model_label(model):
    """返回计算模型的展示名称。"""
    key = normalize_calculation_model(model)
    return CALCULATION_MODEL_LABELS.get(key, key)


def normalize_formula(value):
    """标准化公式名称：None/空 -> barrett，大小写不敏感。"""
    if value is None:
        return "barrett"
    formula = str(value).strip().lower()
    if not formula:
        return "barrett"
    if formula not in FORMULA_LABELS:
        raise UnsupportedFormulaError("formula 只支持 " + ", ".join(FORMULA_NAMES))
    return formula


def normalize_mode(value):
    """标准化执行方式：offline（默认）或 online。"""
    if value is None:
        return "offline"
    mode = str(value).strip().lower()
    if not mode:
        return "offline"
    if mode not in ("offline", "online"):
        raise UnsupportedModeError("mode 只支持 offline 或 online")
    return mode


def get_formula_label(name):
    """返回公式展示名。"""
    return FORMULA_LABELS[normalize_formula(name)]


def get_formula_capabilities(name):
    """返回公式能力声明。"""
    return CAPABILITIES[normalize_formula(name)]


def list_formulas():
    """返回所有公式的能力声明（供文档/客户端使用）。"""
    return [CAPABILITIES[name].to_dict() for name in FORMULA_NAMES]


def _used_inputs(formula, eye, request, solved, overrides=None):
    """只列出实际参与该公式计算的输入；默认值与覆盖值明确标记。

    overrides 是 ULIB 映射带来的常数替换，这里必须反映替换后的真实值，
    否则 used_inputs 会显示与实际计算不一致的常数。
    """
    overrides = overrides or {}
    used = {
        "AL": eye.al,
        "K": eye.k_mean,
        "Refraction": eye.target_refraction,
        "a_constant": overrides.get("a_constant", request.a_constant),
        "k_index": request.k_index,
        "step": request.step,
    }
    if formula == "barrett":
        used.update(
            {
                "ACD": eye.acd,
                "LenThickness": eye.lt,
                "WTW": eye.wtw,
            }
        )
    elif formula in {"haigis", "haigis-toric"}:
        acd_value = eye.acd
        if acd_value is None:
            acd_value = haigis.DEFAULT_ACD
            used["ACD_defaulted"] = True
        used.update(
            {
                "ACD": acd_value,
                "LenThickness": None,
                "WTW": None,
            }
        )
        haigis_source = overrides.get("constants")
        if haigis_source is not None:
            used["a_constant"] = None
            used["a0"] = haigis_source["a0"]
            used["a1"] = haigis_source["a1"]
            used["a2"] = haigis_source["a2"]
        elif request.haigis_constants is not None:
            used["a_constant"] = None
            used["a0"] = request.haigis_constants.a0
            used["a1"] = request.haigis_constants.a1
            used["a2"] = request.haigis_constants.a2
        if formula == "haigis-toric":
            used.update(solved["used_toric_inputs"])
    else:
        used.update({"ACD": None, "LenThickness": None, "WTW": None})
        if formula == "hoffer_q":
            pacd_value = overrides.get("pacd", request.hoffer_q_pacd)
            if pacd_value is not None:
                used["pACD"] = pacd_value
    return used


def _online_used_inputs(eye, request):
    """在线 Barrett 的实际输入；官网适配器缺省 ACD 时按 3.00 标记。"""
    acd_value = eye.acd
    defaulted = acd_value is None
    if defaulted:
        acd_value = ONLINE_DEFAULT_ACD
    used = {
        "AL": eye.al,
        "K": eye.k_mean,
        "Refraction": eye.target_refraction,
        "ACD": acd_value,
        "LenThickness": eye.lt,
        "WTW": eye.wtw,
        "a_constant": request.a_constant,
        "k_index": request.k_index,
    }
    if defaulted:
        used["ACD_defaulted"] = True
    return used


def _build_eye_result(
    formula, eye, request, solved, overrides=None, constants_info=None
):
    """把一个公式的原始结果映射为 API 的单眼结构。"""
    predicted = solved["predicted_refraction"]
    iol_options = sorted(solved["iol_options"], key=lambda row: float(row["iol_power"]))
    caps = CAPABILITIES[formula]
    overrides = overrides or {}
    ignored_inputs = list(caps.ignored_inputs)
    # Haigis 用三常数时 A 常数不参与；否则 A 常数才是常数来源。
    if formula in {"haigis", "haigis-toric"} and (
        "constants" in overrides or request.haigis_constants is not None
    ):
        ignored_inputs.append("a_constant")
    # 型号常数优先时，请求里被屏蔽的同类常数也要如实列出。
    if constants_info is not None:
        ignored_inputs.extend(constants_info.get("ignored_request", []))
    # 同名字段可能从两条路径计入，去重但保持顺序。
    ignored_inputs = list(dict.fromkeys(ignored_inputs))
    result = {
        "biometry": (
            f"AL {eye.al:.2f} mm; "
            f"K1 {eye.k1:.2f} D; K2 {eye.k2:.2f} D; "
            f"Kmean {eye.k_mean:.2f} D"
        ),
        "prediction": "offline",
        "constants": solved["constants_text"],
        "iol_options": iol_options,
        "recommended_power": solved["iol_power_text"],
        "predicted_refraction": (
            round(predicted, 2) if math.isfinite(predicted) else None
        ),
        "elp": round(solved["elp"], 2),
        "confidence": solved["confidence"],
        "low_confidence": solved["low_confidence"],
        "warnings": solved["warnings"],
        "provided_inputs": eye.provided_inputs(),
        "used_inputs": _used_inputs(formula, eye, request, solved, overrides),
        "ignored_inputs": ignored_inputs,
    }
    if formula == "haigis-toric":
        result["provided_inputs"] = {
            **dict(eye.raw),
            **eye.provided_inputs(),
        }
        for field in (
            "posterior_mode",
            "anterior_astigmatism",
            "posterior_astigmatism",
            "net_astigmatism",
            "iol_spherical_equivalent",
            "iol_cylinder",
            "iol_axis",
            "corneal_factor",
            "corneal_correction",
            "residual_astigmatism",
            "recommended_iol_cylinder_exact",
            "recommended_iol_cylinder",
            "recommended_axis",
            "toric_options",
        ):
            result[field] = solved[field]
    return result


def _resolve_offline_constants(request, formula):
    """按公式决定常数来源。

    - Barrett 走自己的 Lens Factor 换算，不读 ULIB（ULIB 表内没有 LF 列）；
    - 其余本地公式在型号命中 ULIB 时由型号常数说了算：SRK/T 用优化 A，
      Hoffer Q 用 pACD，Haigis 用 a0/a1/a2。请求里同类的 a_constant /
      hoffer_q_pacd / haigis_constants 会被屏蔽（记入 ignored_request），
      避免同一请求里出现两套互相冲突的常数。
    - 型号命中但 ULIB 缺该项时才回落到请求值，并在 warnings 中说明。

    返回 (calculate_kwargs 的常数部分, 说明信息 dict 或 None)。
    """
    if formula == "barrett":
        return {}, None

    # 型号无法映射时给出警告：此时 A 常数走的是厂商标准关系换算，
    # 不是晶体优化常数，两种来源的差异可达 0.5 D 以上。
    # 型号可能来自两条路径：API 传的 Barrett 型号名，或 Web UI 的 ULIB
    # 选择器传的 ULIB 原始型号名。两者都要能识别，否则会把 UI 选中的
    # ULIB 晶体误判成「未映射」，给出错误的说明。
    mapped = constants.resolve_model_constants(request.iol_model)
    if mapped is None:
        model_name = (
            str(request.iol_model).strip()
            if request.iol_model and request.iol_model != "Personal Constant"
            else ""
        )
        fallback = {
            "source": "a_constant_conversion",
            "barrett_model": model_name or None,
            "applied": [],
            "ignored_request": [],
            "warnings": [],
            "note": (
                f"型号 {model_name!r} 未映射到 ULIB 条目，常数由 A 常数按厂商"
                "标准关系换算得到，不是晶体优化常数"
                if model_name
                else "未选择晶体型号，常数由 A 常数按厂商标准关系换算得到，"
                "不是晶体优化常数"
            ),
        }
        return {}, fallback

    info = {
        "source": "ulib",
        "source_revision": constants.ULIB_SOURCE_REVISION,
        "barrett_model": mapped["barrett_model"],
        "ulib_name": mapped["ulib_name"],
        "match": mapped["match"],
        "matched_by": mapped["matched_by"],
        "samples": mapped["samples"],
        "preliminary": mapped["preliminary"],
        "note": mapped["note"],
        "applied": [],
        "ignored_request": [],
        "warnings": list(mapped["warnings"]),
    }
    overrides = {}
    ignored = info["ignored_request"]

    # 型号常数优先：请求里显式给的 A 常数不再参与计算。
    ulib_a_constant = mapped.get("a_constant")
    if ulib_a_constant is not None:
        overrides["a_constant"] = ulib_a_constant
        info["applied"].append("a_constant")
        if request.a_constant_provided:
            ignored.append("a_constant")
    elif request.a_constant_provided:
        info["warnings"].append(
            f"ULIB 条目 {mapped['ulib_name']} 缺少 A 常数，沿用请求中的 a_constant"
        )

    if formula == "hoffer_q":
        ulib_pacd = mapped.get("hoffer_q_pacd")
        if ulib_pacd is not None:
            overrides["pacd"] = ulib_pacd
            info["applied"].append("hoffer_q_pacd")
            if request.hoffer_q_pacd is not None:
                ignored.append("hoffer_q_pacd")
        elif request.hoffer_q_pacd is not None:
            info["warnings"].append(
                f"ULIB 条目 {mapped['ulib_name']} 缺少 Hoffer Q pACD，"
                "沿用请求中的 hoffer_q_pacd"
            )

    if formula in {"haigis", "haigis-toric"}:
        haigis_values = mapped.get("haigis_constants")
        if haigis_values:
            overrides["constants"] = {
                "a0": haigis_values[0],
                "a1": haigis_values[1],
                "a2": haigis_values[2],
            }
            info["applied"].append("haigis_constants")
            if request.haigis_constants is not None:
                ignored.append("haigis_constants")
        elif request.haigis_constants is not None:
            info["warnings"].append(
                f"ULIB 条目 {mapped['ulib_name']} 缺少 Haigis 三常数，"
                "沿用请求中的 haigis_constants"
            )

    return overrides, info


def _calculate_offline(request, formula):
    """本地公式单/双眼计算与结果组装。"""
    constant_overrides, constants_info = _resolve_offline_constants(request, formula)
    if (
        formula == "haigis-toric"
        and request.haigis_constants is None
        and "constants" not in constant_overrides
    ):
        raise InputValidationError(
            "haigis-toric 需要 haigis_constants，"
            "或指定能命中内置 ULIB 的 iol_model 由型号提供常数"
        )
    eyes = {}
    solved_eyes = {}
    for eye_name, eye in (
        ("right_eye", request.right_eye),
        ("left_eye", request.left_eye),
    ):
        if eye is None:
            continue
        common.validate_eye(eye.al, eye.k_mean)
        common.validate_optional_measurements(
            acd=eye.acd,
            lt=eye.lt,
            wtw=eye.wtw,
            target=eye.target_refraction,
        )
        calculate_kwargs = {
            "target": eye.target_refraction,
            "a_constant": request.a_constant,
            "k_index": request.k_index,
            "acd": eye.acd,
            "lt": eye.lt,
            "wtw": eye.wtw,
            "step": request.step,
        }
        if formula in {"haigis", "haigis-toric"}:
            calculate_kwargs["constants"] = request.haigis_constants
        elif formula == "hoffer_q":
            calculate_kwargs["pacd"] = request.hoffer_q_pacd
        if formula == "haigis-toric":
            calculate_kwargs.update(
                {
                    "k1": eye.k1,
                    "k2": eye.k2,
                    "k1_axis": eye.raw.get("K1Axis"),
                    "k2_axis": eye.raw.get("K2Axis"),
                    **{
                        field: eye.raw[field]
                        for field in haigis_toric.OPTIONAL_INPUTS
                        if field in eye.raw
                    },
                }
            )
        solved = _MODULES[formula].calculate(
            eye.al,
            eye.k_mean,
            **{**calculate_kwargs, **constant_overrides},
        )
        if constants_info is not None:
            solved["warnings"] = list(solved["warnings"]) + constants_info["warnings"]
            if constants_info["warnings"]:
                solved["low_confidence"] = True
                solved["confidence"] = "LOW_CONFIDENCE"
        solved_eyes[eye_name] = solved
        eyes[eye_name] = _build_eye_result(
            formula, eye, request, solved, constant_overrides, constants_info
        )

    reference = next(iter(solved_eyes.values()))
    caps = CAPABILITIES[formula]
    result = {
        "formula": formula,
        "formula_label": caps.label,
        "mode": "offline",
        "model": reference["model"],
        "model_note": reference["model_note"],
        "formula_capabilities": caps.to_dict(),
        "right_eye": eyes.get("right_eye"),
        "left_eye": eyes.get("left_eye"),
    }
    if formula == "barrett":
        result["calibration_report"] = "docs/calibration_report.md"
    if constants_info is not None:
        result["constants_source"] = constants_info
    return result


async def _calculate_online(request, formula):
    """官网 Barrett 普通计算；仅 Barrett 支持 online。"""
    if formula != "barrett":
        raise UnsupportedModeError("只有 Barrett 支持 online 模式")
    result = await barrett_online.calculate_barrett_iol(
        right_eye_params=(
            request.right_eye.online_params() if request.right_eye else None
        ),
        left_eye_params=(
            request.left_eye.online_params() if request.left_eye else None
        ),
        a_constant=request.a_constant,
        patient_name=request.patient_name,
        iol_model=request.iol_model,
        k_index=request.k_index,
    )
    caps = CAPABILITIES[formula]
    wrapped = {
        "formula": "barrett",
        "formula_label": caps.label,
        "mode": "online",
        "formula_capabilities": caps.to_dict(),
        **result,
    }
    for eye_name, eye in (
        ("right_eye", request.right_eye),
        ("left_eye", request.left_eye),
    ):
        if eye is None or not isinstance(wrapped.get(eye_name), dict):
            continue
        wrapped[eye_name] = {
            **wrapped[eye_name],
            "provided_inputs": eye.provided_inputs(),
            "used_inputs": _online_used_inputs(eye, request),
            "ignored_inputs": [],
        }
    return wrapped


async def calculate(request: CalculationRequest):
    """普通 IOL 计算的唯一入口。"""
    if not isinstance(request, CalculationRequest):
        raise InputValidationError("calculate 需要 CalculationRequest")

    model = normalize_calculation_model(request.model)
    if model is not None:
        formula, mode = CALCULATION_MODELS[model]
    else:
        formula = normalize_formula(request.formula)
        mode = normalize_mode(request.mode)
        model = calculation_model_for(formula, mode)

    caps = CAPABILITIES[formula]
    if mode not in caps.modes:
        if formula != "barrett":
            raise UnsupportedModeError("只有 Barrett 支持 online 模式")
        raise UnsupportedModeError(f"{caps.label} 不支持 {mode} 模式")

    if mode == "online":
        result = await _calculate_online(request, formula)
    else:
        result = _calculate_offline(request, formula)
    result["calculation_model"] = model
    result["calculation_model_label"] = CALCULATION_MODEL_LABELS[model]
    return result


async def calculate_toric(request: ToricCalculationRequest):
    """散光（Toric）计算入口；保持官网适配器原有返回结构。"""
    if not isinstance(request, ToricCalculationRequest):
        raise InputValidationError("calculate_toric 需要 ToricCalculationRequest")
    result = await barrett_toric.calculate_barrett_toric_iol(
        right_eye_params=request.right_eye,
        left_eye_params=request.left_eye,
        a_constant=request.a_constant,
        patient_name=request.patient_name,
        iol_model=request.iol_model,
        k_index=request.k_index,
        cylinder_mode=request.cylinder_mode,
    )
    labelled = {
        "formula_name": "barrett_toric",
        "formula_label": "Barrett Universal II Toric",
        "mode": "online",
        "calculation_model": TORIC_CALCULATION_MODEL,
        "calculation_model_label": TORIC_CALCULATION_MODEL_LABEL,
        **result,
    }
    return labelled


def get_hello_message():
    """兼容 /hello 端点。"""
    return barrett_online.get_hello_message()


def fetch_iol_model_list():
    """兼容 IOL 型号列表查询。"""
    return iol_models.fetch_iol_model_list()


def list_iol_models(formula=None):
    """按公式返回可选晶体列表与来源说明。"""
    return iol_models.list_iol_models(formula)


def fetch_model_constants(model_name):
    """按型号查询常数：优先内置 ULIB 快照，未收录再回退 Barrett 官网。"""
    return iol_models.fetch_model_constants(model_name)


def lookup_ulib_constants(model_name):
    """只查内置 ULIB 快照，未收录返回 None，不发网络请求。"""
    return iol_models.lookup_ulib_constants(model_name)


def fetch_model_a_constant(model_name):
    """兼容单个 IOL 型号 A 常数查询。"""
    return iol_models.fetch_model_a_constant(model_name)


__all__ = [
    "CALCULATION_MODELS",
    "CALCULATION_MODEL_LABELS",
    "CAPABILITIES",
    "FORMULA_LABELS",
    "FORMULA_NAMES",
    "calculate",
    "calculate_toric",
    "calculation_model_for",
    "fetch_iol_model_list",
    "fetch_model_a_constant",
    "fetch_model_constants",
    "get_calculation_model_label",
    "get_formula_capabilities",
    "get_formula_label",
    "get_hello_message",
    "list_formulas",
    "list_iol_models",
    "lookup_ulib_constants",
    "normalize_calculation_model",
    "normalize_formula",
    "normalize_mode",
]
