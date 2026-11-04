"""ULIB 型号名解析：UI 传原名与 API 传 Barrett 名都要能识别。"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from formula import CalculationRequest, calculate, constants

EYE = {"AL": 23.5, "K1": 43.5, "K2": 44.5, "ACD": 3.2, "Refraction": 0}


def run(model, **extra):
    payload = {"model": model, "right_eye": dict(EYE), **extra}
    return asyncio.run(calculate(CalculationRequest.from_mapping(payload)))


def test_resolve_accepts_barrett_model_name():
    """Barrett 型号名经映射表命中。"""
    result = constants.resolve_model_constants("AMO ZCB00")
    assert result is not None
    assert result["matched_by"] == "barrett_model"
    assert result["barrett_model"] == "AMO ZCB00"
    assert result["ulib_name"] == "AMO Tecnis 1 ZCB00"


def test_resolve_accepts_ulib_original_name():
    """ULIB 原始型号名直接命中（Web UI 选择器走这条）。"""
    result = constants.resolve_model_constants("AMO Tecnis 1 ZCB00")
    assert result is not None
    assert result["matched_by"] == "ulib_name"
    assert result["ulib_name"] == "AMO Tecnis 1 ZCB00"
    assert result["match"] == "ulib_name"
    assert result["a_constant"] == 119.3


def test_resolve_returns_none_for_unknown_and_unmapped():
    """未知型号与明确不映射的 Barrett 型号都返回 None。"""
    assert constants.resolve_model_constants("nosuch lens") is None
    assert constants.resolve_model_constants("Alcon MN60MA") is None
    assert constants.resolve_model_constants("Personal Constant") is None
    assert constants.resolve_model_constants(None) is None


def test_ui_supplied_ulib_name_is_not_reported_as_unmapped():
    """UI 传 ULIB 原名时，说明里不能出现"未映射"这类误导性措辞。"""
    result = run("haigis", iol_model="AMO Tecnis 1 ZCB00")
    info = result["constants_source"]
    assert info["source"] == "ulib"
    assert info["matched_by"] == "ulib_name"
    assert info["applied"] == ["a_constant", "haigis_constants"]
    assert info["ulib_name"] == "AMO Tecnis 1 ZCB00"


def test_ui_flow_with_explicit_constants_still_reports_ulib():
    """UI 选中后显式提交常数时，说明仍标明来自哪个 ULIB 条目。"""
    result = run(
        "haigis",
        iol_model="AMO Tecnis 1 ZCB00",
        a_constant=119.3,
        haigis_constants={"a0": -1.302, "a1": 0.21, "a2": 0.251},
    )
    info = result["constants_source"]
    assert info["source"] == "ulib"
    assert info["applied"] == []
    assert info["ulib_name"] == "AMO Tecnis 1 ZCB00"
    # 计算用的确实是显式提供的三常数。
    used = result["right_eye"]["used_inputs"]
    assert used["a0"] == -1.302


def test_generic_ulib_name_drives_constants_for_all_three_formulas():
    """任一公式传 ULIB 原名都能取到对应常数。"""
    for model, field in (
        ("srkt", "a_constant"),
        ("hoffer_q", "hoffer_q_pacd"),
        ("haigis", "haigis_constants"),
    ):
        result = run(model, iol_model="AMO Tecnis 1 ZCB00")
        info = result["constants_source"]
        assert info["source"] == "ulib", model
        assert field in info["applied"], model


def test_unmapped_model_still_reports_conversion_source():
    """真正未映射的型号仍标注 A 常数换算。"""
    result = run("srkt", iol_model="Alcon MN60MA")
    info = result["constants_source"]
    assert info["source"] == "a_constant_conversion"
    assert "标准关系" in info["note"]
