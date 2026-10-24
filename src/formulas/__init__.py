"""本地公式包：Barrett Universal II / SRK/T / Hoffer Q / Haigis 统一调度。

四个公式的 calculate 返回同一套字段结构（见 formulas.common.
build_formula_result），API 层因此只需按 formula 名称分发，无需关心各公式的
内部实现细节。
"""

from __future__ import annotations

from . import barrett, haigis, hoffer_q, srkt

FORMULA_LABELS = {
    "barrett": "Barrett Universal II",
    "srkt": "SRK/T",
    "hoffer_q": "Hoffer Q",
    "haigis": "Haigis",
}

FORMULA_NAMES = tuple(FORMULA_LABELS)

_MODULES = {
    "barrett": barrett,
    "srkt": srkt,
    "hoffer_q": hoffer_q,
    "haigis": haigis,
}


def normalize_formula(value):
    """标准化公式名称：None/空 -> barrett，大小写不敏感，未知名称报错。"""
    if value is None:
        return "barrett"
    formula = str(value).strip().lower()
    if not formula:
        return "barrett"
    if formula not in FORMULA_LABELS:
        raise ValueError("formula 只支持 barrett, srkt, hoffer_q, haigis")
    return formula


def get_formula_label(name):
    """返回公式的展示名称。"""
    return FORMULA_LABELS[normalize_formula(name)]


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
    """按公式名称计算单眼，四个公式共用同一套参数与返回结构。"""
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
    "FORMULA_LABELS",
    "FORMULA_NAMES",
    "calculate_formula",
    "get_formula_label",
    "normalize_formula",
]
