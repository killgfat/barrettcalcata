"""离线 BUII 模块的单元测试。"""

import importlib
import itertools
import math
import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

offline = importlib.import_module("barrett_offline")


def test_a_constant_to_lens_factor_matches_published_pairs():
    """厂商公开的四组 (A, LF) 锚点都应落在 0.01 以内。"""
    anchors = {
        118.7: 1.73,
        119.0: 1.88,
        119.1: 1.94,
        119.3: 2.04,
    }
    for a_constant, expected in anchors.items():
        assert offline.a_constant_to_lens_factor(a_constant) == pytest.approx(
            expected, abs=0.01
        )


def test_a_constant_lens_factor_round_trip():
    for a_constant in (112.0, 115.5, 118.7, 120.0, 125.0):
        lens_factor = offline.a_constant_to_lens_factor(a_constant)
        assert offline.lens_factor_to_a_constant(lens_factor) == pytest.approx(
            a_constant, abs=1e-9
        )


def test_emmetropia_verification_step():
    """反解到 0.5 D 后再正算，预测屈光度应接近 0。"""
    solved = offline.solve_iol_power(23.5, 44.0, target=0.0, a_constant=118.7)
    assert solved["iol_power"] % 0.5 == 0
    assert abs(solved["predicted_refraction"]) < 0.2
    assert math.isfinite(solved["elp"])
    assert solved["confidence"] == "OK"


def test_target_refraction_inverse_is_exact():
    """精确度数正反解应回到目标屈光度。"""
    for target in (-2.0, -0.5, 0.0, 1.0, 2.5):
        exact = offline.iol_power_for_target(
            24.0, 43.0, target=target, a_constant=119.3
        )
        predicted = offline.predict_refraction(
            24.0, 43.0, a_constant=119.3, iol_power=exact
        )
        assert predicted == pytest.approx(target, abs=1e-6)


def test_one_dioptre_step_mode():
    """高度数晶体可切换到 1 D 步进。"""
    solved = offline.solve_iol_power(
        29.0, 41.0, target=-1.0, a_constant=118.7, step=1.0
    )
    assert solved["step"] == 1.0
    assert solved["iol_power"] == pytest.approx(round(solved["iol_power"]), abs=1e-9)
    for option in solved["iol_options"]:
        assert float(option["iol_power"]) % 1.0 == 0


def test_solve_power_matches_table_recommendation():
    for target in (-2.0, 0.0, 1.5):
        solved = offline.solve_iol_power(24.2, 45.1, target=target)
        recommended = [row for row in solved["iol_options"] if row["recommended"]]
        assert recommended
        assert float(recommended[0]["iol_power"]) == pytest.approx(solved["iol_power"])


def test_iol_table_has_one_recommendation_and_half_dioptre_steps():
    table = offline.build_iol_table(23.5, 44.0, target=0.0)
    assert len(table) == 9
    assert sum(1 for row in table if row["recommended"]) == 1
    powers = [float(row["iol_power"]) for row in table]
    assert powers == sorted(powers)
    steps = [round(b - a, 6) for a, b in itertools.pairwise(powers)]
    assert all(step == pytest.approx(0.5) for step in steps)


def test_input_domain_flags_low_confidence():
    assert offline.assess_input_domain(23.5, 44.0)["confidence"] == "OK"

    short_eye = offline.assess_input_domain(21.0, 44.0)
    assert short_eye["confidence"] == "LOW_CONFIDENCE"
    assert any("AL=" in warning for warning in short_eye["warnings"])

    steep_k = offline.assess_input_domain(23.5, 49.0)
    assert steep_k["confidence"] == "LOW_CONFIDENCE"
    assert any("K=" in warning for warning in steep_k["warnings"])

    long_eye = offline.solve_iol_power(27.0, 43.0)
    assert long_eye["confidence"] == "LOW_CONFIDENCE"
    assert long_eye["low_confidence"] is True
    assert long_eye["warnings"]

    normal_eye = offline.solve_iol_power(23.5, 44.0)
    assert normal_eye["low_confidence"] is False


@pytest.mark.parametrize(
    "al,k",
    [
        (11.9, 44.0),
        (38.1, 44.0),
        (23.5, 29.9),
        (23.5, 60.1),
    ],
)
def test_hard_limits_reject(al, k):
    with pytest.raises(offline.OfflineInputError):
        offline.solve_iol_power(al, k)


def test_k_index_conversion_matches_reference_index():
    k_1332 = 43.0
    k_13375 = k_1332 * (1.3375 - 1.0) / (1.332 - 1.0)
    elp_converted = offline.predict_elp(23.5, k_1332, k_index=1.332)
    elp_reference = offline.predict_elp(23.5, k_13375, k_index=1.3375)
    assert elp_converted == pytest.approx(elp_reference, abs=1e-9)


def test_elp_increases_with_axial_length_and_k():
    """单调性检查：模型在参考点附近应是物理上合理的方向。"""
    base = offline.predict_elp(23.5, 44.0, a_constant=118.7)
    assert offline.predict_elp(24.5, 44.0, a_constant=118.7) > base
    assert offline.predict_elp(23.5, 45.0, a_constant=118.7) > base


def test_reference_case_matches_public_grid():
    """公开数据 B_norm 基线（AL 23.5, K 43.5/44.5, A 118.7）。

    官方值 20.487927565392354 来自 ekrbye/barrett-uii-data 的 scans.csv。
    """
    exact = offline.iol_power_for_target(
        23.5,
        44.0,
        target=0.0,
        a_constant=118.7,
        acd=3.2,
        lt=4.6,
        wtw=11.9,
    )
    assert exact == pytest.approx(20.487927565392354, abs=0.1)


def test_result_marks_itself_as_approximation():
    solved = offline.solve_iol_power(23.5, 44.0)
    assert solved["model"] == offline.MODEL_ID
    assert "不是官方" in solved["model_note"]


def test_module_has_no_network_imports_and_runs_with_socket_disabled(
    monkeypatch,
):
    """离线模块源码不得 import 网络库，且断网仍可计算。"""

    source = Path(offline.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "import requests",
        "import urllib",
        "from urllib",
        "import socket",
        "import http",
    ):
        assert forbidden not in source

    class BlockedSocket:
        def __init__(self, *args, **kwargs):
            raise OSError("network disabled in test")

    monkeypatch.setattr(socket, "socket", BlockedSocket)
    solved = offline.solve_iol_power(23.5, 44.0, a_constant=118.7)
    assert math.isfinite(solved["iol_power_exact"])
    assert solved["iol_options"]
