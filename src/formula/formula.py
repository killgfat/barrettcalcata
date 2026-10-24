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
    haigis,
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
}

FORMULA_NAMES = tuple(FORMULA_LABELS)

CAPABILITIES = {
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
        constants="A-constant（推导 pACD）",
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
}

# 官网普通 Barrett 适配器在 ACD 缺失时沿用的默认值（与官网表单一致）。
ONLINE_DEFAULT_ACD = 3.00


def normalize_formula(value):
    """标准化公式名称：None/空 -> barrett，大小写不敏感。"""
    if value is None:
        return "barrett"
    formula = str(value).strip().lower()
    if not formula:
        return "barrett"
    if formula not in FORMULA_LABELS:
        raise UnsupportedFormulaError("formula 只支持 barrett, srkt, hoffer_q, haigis")
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


def _used_inputs(formula, eye, request, solved):
    """只列出实际参与该公式计算的输入；默认值明确标记。"""
    used = {
        "AL": eye.al,
        "K": eye.k_mean,
        "Refraction": eye.target_refraction,
        "a_constant": request.a_constant,
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
    elif formula == "haigis":
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
        if request.haigis_constants is not None:
            used["a_constant"] = None
            used["a0"] = request.haigis_constants.a0
            used["a1"] = request.haigis_constants.a1
            used["a2"] = request.haigis_constants.a2
    else:
        used.update({"ACD": None, "LenThickness": None, "WTW": None})
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


def _build_eye_result(formula, eye, request, solved):
    """把一个公式的原始结果映射为 API 的单眼结构。"""
    predicted = solved["predicted_refraction"]
    iol_options = sorted(solved["iol_options"], key=lambda row: float(row["iol_power"]))
    caps = CAPABILITIES[formula]
    ignored_inputs = list(caps.ignored_inputs)
    if formula == "haigis" and request.haigis_constants is not None:
        ignored_inputs.append("a_constant")
    return {
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
        "used_inputs": _used_inputs(formula, eye, request, solved),
        "ignored_inputs": ignored_inputs,
    }


def _calculate_offline(request, formula):
    """本地公式单/双眼计算与结果组装。"""
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
        if formula == "haigis":
            calculate_kwargs["constants"] = request.haigis_constants
        solved = _MODULES[formula].calculate(
            eye.al,
            eye.k_mean,
            **calculate_kwargs,
        )
        solved_eyes[eye_name] = solved
        eyes[eye_name] = _build_eye_result(formula, eye, request, solved)

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
    formula = normalize_formula(request.formula)
    mode = normalize_mode(request.mode)
    caps = CAPABILITIES[formula]
    if mode not in caps.modes:
        if formula != "barrett":
            raise UnsupportedModeError("只有 Barrett 支持 online 模式")
        raise UnsupportedModeError(f"{caps.label} 不支持 {mode} 模式")
    if mode == "online":
        return await _calculate_online(request, formula)
    return _calculate_offline(request, formula)


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
        **result,
    }
    return labelled


def get_hello_message():
    """兼容 /hello 端点。"""
    return barrett_online.get_hello_message()


def fetch_iol_model_list():
    """兼容 IOL 型号列表查询。"""
    return iol_models.fetch_iol_model_list()


def fetch_model_a_constant(model_name):
    """兼容单个 IOL 型号 A 常数查询。"""
    return iol_models.fetch_model_a_constant(model_name)


__all__ = [
    "CAPABILITIES",
    "FORMULA_LABELS",
    "FORMULA_NAMES",
    "calculate",
    "calculate_toric",
    "fetch_iol_model_list",
    "fetch_model_a_constant",
    "get_formula_capabilities",
    "get_formula_label",
    "get_hello_message",
    "list_formulas",
    "normalize_formula",
    "normalize_mode",
]
