"""内置 ULIB 常数快照的查询测试。"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from formula import constants
from formula.data_ulib import iter_rows


def test_snapshot_parses_all_rows():
    """快照每一行都能解析，且字段数为 8。"""
    rows = list(iter_rows())
    assert len(rows) == 304
    for row in rows:
        assert len(row) == 8
        assert isinstance(row[0], str) and row[0]


def test_alcon_sn60wf_matches_ulib_table():
    """Alcon SN60WF 的常数与 ULIB 表一致。"""
    entry = constants.lookup("Alcon SN60WF")
    assert entry is not None
    assert entry.nominal_a == 118.7
    assert entry.haigis == (-0.769, 0.234, 0.217)
    assert entry.pacd == 5.64
    assert entry.sf == 1.84
    assert entry.srkt_a == 119.0
    assert entry.srk2_a == 119.2
    assert entry.samples == 5363
    assert entry.preliminary is False
    assert entry.warnings() == []


def test_regional_variants_are_not_merged():
    """同名不同地区版本常数不同，必须分别命中。"""
    base = constants.lookup("Alcon SN60WF")
    japan = constants.lookup("Alcon SN60WF (Japan)")
    assert base is not None and japan is not None
    assert base.name != japan.name
    assert base.haigis != japan.haigis


def test_positive_and_negative_diopter_lenses_stay_distinct():
    """(+) 与 (-) 版本不能归一化到同一条。"""
    plus = constants.lookup("Alcon MA60MA (+diopters)")
    minus = constants.lookup("Alcon MA60MA (-diopters)")
    assert plus is not None and minus is not None
    assert plus.srkt_a == 126.6
    assert minus.srkt_a == 103.6
    # 去掉正负标记后无法区分是哪一款，应拒绝匹配。
    assert constants.lookup("Alcon MA60MA") is None


def test_name_matching_is_forgiving_about_case_space_and_dash():
    """大小写、多余空格、连字符不影响匹配。"""
    for variant in ("alcon sn60wf", "ALCON-SN60WF", "  Alcon   SN60WF  "):
        entry = constants.lookup(variant)
        assert entry is not None
        assert entry.name == "Alcon SN60WF"


def test_unknown_model_returns_none():
    """未收录型号返回 None，不做模糊猜测。"""
    for value in ("Not A Real Lens", "", None, "AcrySof SN60WF"):
        assert constants.lookup(value) is None


def test_preliminary_entry_reports_warning():
    """样本量小于 50 的条目附带 preliminary 警告。"""
    entry = constants.lookup("Oculentis L-402-1 discontinued")
    assert entry is not None
    assert entry.samples < 50
    assert entry.preliminary is True
    warnings = entry.warnings()
    assert len(warnings) == 1
    assert "preliminary" in warnings[0]


def test_short_name_index_skips_conflicts():
    """去括号短名发生冲突时不参与匹配。"""
    # ZEISS CT SPHERIS 203(P) 只有一条带括号后缀的版本，短名可用。
    assert constants.lookup("ZEISS CT SPHERIS 203(P)") is not None
    # 短名索引必须小于整名索引，说明冲突项已被剔除。
    assert constants.short_index_size() < constants.count()


def test_to_dict_carries_source_metadata():
    """输出结构带上来源，便于上层标注数据版本。"""
    data = constants.lookup("Alcon SA60AT").to_dict()
    assert data["source"] == "ulib"
    assert data["source_revision"] == "2016-10-31"
    assert data["source_url"].endswith("/ulib/c1.htm")
    assert data["srkt_a"] == 118.8
    assert data["nominal_a"] == 118.4


def test_row_without_nominal_constant_is_preserved():
    """原表留空的名义 A 常数按 None 保留，不臆造数值。"""
    entry = constants.lookup("Medicem WIOL-CF")
    assert entry is not None
    assert entry.nominal_a is None
    assert entry.srkt_a == 120.6


@pytest.mark.parametrize("model_name", ["Alcon SN60WF", "Alcon SA60AT"])
def test_lookup_is_stable_across_calls(model_name):
    """重复查询返回同一条目。"""
    first = constants.lookup(model_name)
    second = constants.lookup(model_name)
    assert first == second
