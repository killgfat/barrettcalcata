"""Barrett Universal II 的本地封装：数值核心仍由 barrett_offline 提供。

本模块不复制任何 ELP 系数，只做参数转发与统一字段补齐，因此
barrett_offline 的校准结果与行为保持不变。
"""

from __future__ import annotations

from barrett_offline import solve_iol_power

from .common import as_float

LABEL = "Barrett Universal II"

CITATIONS = (
    (
        "Barrett GD. Intraocular lens calculation formulas for new intraocular "
        "lens implants. J Cataract Refract Surg. 1987;13(4):389-396."
    ),
    (
        "Barrett GD. An improved universal theoretical formula for intraocular "
        "lens power prediction. J Cataract Refract Surg. 1993;19(6):713-720. "
        "PMID 8271166."
    ),
    (
        "Barrett GD. Barrett Formulas: Strategies to Improve IOL Power "
        "Prediction. In: Intraocular Lens Calculations. Springer; 2024. "
        "doi:10.1007/978-3-031-50666-6_37."
    ),
)


def calculate(
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
    """调用离线 Barrett 核心，并补上统一的 constants_text 字段。

    其余字段（含 model/model_note/confidence）原样透传，避免与
    barrett_offline 的校准说明脱节。
    """
    k_index_value = as_float(k_index, "k_index")
    solved = solve_iol_power(
        al,
        k,
        target=target,
        a_constant=a_constant,
        k_index=k_index_value,
        step=step,
        acd=acd,
        lt=lt,
        wtw=wtw,
    )
    solved["constants_text"] = (
        f"A={solved['a_constant']:.2f}; "
        f"LF={solved['lens_factor']:.2f}; "
        f"K index={k_index_value}"
    )
    return solved


__all__ = ["CITATIONS", "LABEL", "calculate"]
