"""Barrett 型号 → ULIB 常数映射的分派测试。"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from formula import CalculationRequest, calculate, constants
from formula.data_model_map import BARRETT_TO_ULIB

EYE = {"AL": 23.5, "K1": 43.5, "K2": 44.5, "ACD": 3.2, "Refraction": 0}


def run(model, **extra):
    """按 model 跑一次计算，返回完整结果。"""
    payload = {"model": model, "right_eye": dict(EYE), **extra}
    request = CalculationRequest.from_mapping(payload)
    return asyncio.run(calculate(request))


def test_mapping_table_covers_eighteen_barrett_models():
    """Barrett 下拉的 18 个型号都在表里，且没有重复。"""
    names = [row[0] for row in BARRETT_TO_ULIB]
    assert len(names) == 18
    assert len(set(names)) == 18


def test_every_mapped_target_exists_in_ulib_snapshot():
    """映射目标必须真的存在于 ULIB 快照，避免写错名字。"""
    mapped = 0
    for name, ulib_name, match, note in BARRETT_TO_ULIB:
        if ulib_name is None:
            assert match is None
            assert note, f"{name} 未映射但缺少原因说明"
            continue
        mapped += 1
        assert match in {"exact", "series"}
        entry = constants.lookup(ulib_name)
        assert entry is not None, f"{name} 指向的 {ulib_name!r} 不在快照中"
    assert mapped == 11


def test_lookup_for_barrett_model_returns_ulib_constants():
    """Barrett 型号能查到对应的 ULIB 常数。"""
    result = constants.lookup_for_barrett_model("AMO ZCB00")
    assert result is not None
    assert result["barrett_model"] == "AMO ZCB00"
    assert result["ulib_name"] == "AMO Tecnis 1 ZCB00"
    assert result["match"] == "exact"
    assert result["haigis_constants"] == (-1.302, 0.21, 0.251)
    assert result["srkt_a"] == 119.3
    assert result["hoffer_q_pacd"] == 5.8
    assert result["a_constant"] == 119.3


def test_lookup_for_barrett_model_is_case_and_punctuation_insensitive():
    """大小写和标点不影响映射。"""
    for variant in ("amo zcb00", "AMO-ZCB00", "  Amo   ZCB00 "):
        assert constants.lookup_for_barrett_model(variant) is not None


def test_unmapped_barrett_model_returns_none():
    """ULIB 没有对应条目的型号返回 None，不去猜近似型号。"""
    for name in ("Alcon MN60MA", "AMO ZCT", "Hoya iSert 351"):
        assert constants.lookup_for_barrett_model(name) is None
    assert constants.lookup_for_barrett_model("Not A Lens") is None


def test_srkt_uses_ulib_optimized_a_when_a_constant_not_given():
    """不填 A 常数时，SRK/T 改用 ULIB 的优化 A。"""
    result = run("srkt", iol_model="AMO ZCB00")
    assert result["constants_source"]["applied"] == ["a_constant"]
    assert result["right_eye"]["used_inputs"]["a_constant"] == 119.3


def test_explicit_a_constant_wins_over_ulib():
    """调用方显式给的 A 常数优先。"""
    result = run("srkt", iol_model="AMO ZCB00", a_constant=118.8)
    assert result["right_eye"]["used_inputs"]["a_constant"] == 118.8
    info = result["constants_source"]
    assert "a_constant" not in info["applied"]


def test_hoffer_q_uses_ulib_pacd():
    """不填 pACD 时，Hoffer Q 改用 ULIB 的优化 pACD。"""
    result = run("hoffer_q", iol_model="AMO ZCB00")
    assert "hoffer_q_pacd" in result["constants_source"]["applied"]
    assert result["right_eye"]["used_inputs"]["pACD"] == 5.8


def test_explicit_pacd_wins_over_ulib():
    """调用方显式给的 pACD 优先。"""
    result = run("hoffer_q", iol_model="AMO ZCB00", hoffer_q_pacd=5.40)
    assert result["right_eye"]["used_inputs"]["pACD"] == 5.40


def test_haigis_uses_ulib_three_constants():
    """不填 Haigis 常数时，改用 ULIB 的 a0/a1/a2。"""
    result = run("haigis", iol_model="AMO ZCB00")
    used = result["right_eye"]["used_inputs"]
    assert "haigis_constants" in result["constants_source"]["applied"]
    assert used["a0"] == -1.302
    assert used["a1"] == 0.21
    assert used["a2"] == 0.251


def test_explicit_haigis_constants_win_over_ulib():
    """调用方显式给的三常数优先。"""
    result = run(
        "haigis",
        iol_model="AMO ZCB00",
        haigis_constants={"a0": 1.0, "a1": 0.4, "a2": 0.1},
    )
    used = result["right_eye"]["used_inputs"]
    assert used["a0"] == 1.0


def test_barrett_does_not_read_ulib():
    """Barrett 使用自己的 Lens Factor 路径，不套用 ULIB。"""
    result = run("barrett_ii_offline", iol_model="AMO ZCB00")
    assert "constants_source" not in result


def test_unmapped_model_reports_fallback_note():
    """型号无映射时明确标注常数来自 A 常数换算。"""
    result = run("srkt", iol_model="Alcon MN60MA")
    info = result["constants_source"]
    assert info["source"] == "a_constant_conversion"
    assert info["applied"] == []
    assert "标准关系" in info["note"]


def test_preliminary_mapping_downgrades_confidence():
    """样本量偏小的 ULIB 条目会降低置信度。"""
    # Zeiss 709M 映射到 n=48 的条目，低于 50 的 prelim 阈值。
    result = run("srkt", iol_model="Zeiss 709M")
    info = result["constants_source"]
    assert info["preliminary"] is True
    assert info["warnings"]
    assert result["right_eye"]["confidence"] == "LOW_CONFIDENCE"
