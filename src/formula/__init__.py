"""IOL 公式包：普通/散光计算的唯一公共入口。

对外只暴露 formula.calculate、formula.calculate_toric 及型号查询；
API 层不再直接 import 任何具体公式模块。
"""

from __future__ import annotations

from . import barrett, haigis, hoffer_q, srkt
from .formula import (
    CAPABILITIES,
    FORMULA_LABELS,
    FORMULA_NAMES,
    calculate,
    calculate_toric,
    fetch_iol_model_list,
    fetch_model_a_constant,
    get_formula_capabilities,
    get_formula_label,
    get_hello_message,
    list_formulas,
    normalize_formula,
    normalize_mode,
)
from .types import (
    CalculationError,
    CalculationRequest,
    EyeInput,
    FormulaCapabilities,
    FormulaError,
    InputValidationError,
    ToricCalculationRequest,
    UnsupportedFormulaError,
    UnsupportedModeError,
)

_MODULES = {
    "barrett": barrett,
    "srkt": srkt,
    "hoffer_q": hoffer_q,
    "haigis": haigis,
}


def calculate_formula(
    name,
    al,
    k,
    target=0.0,
    a_constant=118.7,
    k_index=1.3375,
    acd=None,
    lt=None,
    wtw=None,
    step=0.5,
):
    """同步单眼计算（脚本/测试兼容入口）。

    这是对具体公式模块的薄封装，不参与 API 调度；API 必须使用
    formula.calculate，以便统一校验、模式检查和结果组装。
    """
    formula = normalize_formula(name)
    return _MODULES[formula].calculate(
        al,
        k,
        target=target,
        a_constant=a_constant,
        k_index=k_index,
        acd=acd,
        lt=lt,
        wtw=wtw,
        step=step,
    )


__all__ = [
    "CAPABILITIES",
    "FORMULA_LABELS",
    "FORMULA_NAMES",
    "CalculationError",
    "CalculationRequest",
    "EyeInput",
    "FormulaCapabilities",
    "FormulaError",
    "InputValidationError",
    "ToricCalculationRequest",
    "UnsupportedFormulaError",
    "UnsupportedModeError",
    "calculate",
    "calculate_formula",
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
