"""公式调度层的新契约测试：输入、能力、used/ignored inputs 与错误边界。"""

import asyncio
import math
import socket
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import formula
from formula.types import (
    CalculationRequest,
    InputValidationError,
    ToricCalculationRequest,
    UnsupportedModeError,
)


def run_calculation(body):
    return asyncio.run(formula.calculate(CalculationRequest.from_mapping(body)))


def reference_body(**eye_overrides):
    eye = {
        "AL": 23.5,
        "K1": 43.5,
        "K2": 44.0,
        "ACD": 3.2,
        "Refraction": 0,
        "LenThickness": 4.6,
        "WTW": 11.9,
    }
    eye.update(eye_overrides)
    return {
        "right_eye": eye,
        "a_constant": 118.7,
        "model": "barrett_ii_offline",
    }


def test_offline_output_contract_and_provided_inputs():
    data = run_calculation(reference_body())

    assert data["formula"] == "barrett"
    assert data["formula_label"] == "Barrett Universal II"
    assert data["mode"] == "offline"
    assert data["formula_capabilities"]["modes"] == ("offline", "online")
    assert data["calibration_report"] == "docs/calibration_report.md"

    eye = data["right_eye"]
    for key in (
        "biometry",
        "prediction",
        "constants",
        "iol_options",
        "recommended_power",
        "predicted_refraction",
        "elp",
        "confidence",
        "low_confidence",
        "warnings",
        "provided_inputs",
        "used_inputs",
        "ignored_inputs",
    ):
        assert key in eye

    assert eye["provided_inputs"]["ACD"] == 3.2
    assert eye["provided_inputs"]["LenThickness"] == 4.6
    assert eye["used_inputs"]["ACD"] == 3.2
    assert eye["used_inputs"]["LenThickness"] == 4.6
    assert eye["used_inputs"]["WTW"] == 11.9
    assert eye["ignored_inputs"] == []
    assert all(row["optic"] is None for row in eye["iol_options"])
    powers = [float(row["iol_power"]) for row in eye["iol_options"]]
    assert powers == sorted(powers)


def test_srkt_marks_measured_acd_as_ignored():
    body = reference_body()
    body.pop("model", None)
    body["formula"] = "srkt"
    data = run_calculation(body)

    eye = data["right_eye"]
    assert eye["provided_inputs"]["ACD"] == 3.2
    assert eye["used_inputs"]["ACD"] is None
    assert eye["used_inputs"]["LenThickness"] is None
    assert eye["ignored_inputs"] == ["ACD", "LenThickness", "WTW"]
    assert eye["prediction"] == "offline"


def test_hoffer_q_marks_measured_acd_as_ignored():
    body = reference_body()
    body.pop("model", None)
    body["formula"] = "hoffer_q"
    data = run_calculation(body)

    eye = data["right_eye"]
    assert eye["used_inputs"]["ACD"] is None
    assert eye["ignored_inputs"] == ["ACD", "LenThickness", "WTW"]


def test_all_formula_tables_are_ascending_by_iol_power():
    for formula_name in formula.FORMULA_NAMES:
        body = reference_body()
        body.pop("model", None)
        body["formula"] = formula_name
        eye = run_calculation(body)["right_eye"]
        powers = [float(row["iol_power"]) for row in eye["iol_options"]]
        assert powers == sorted(powers)


def test_haigis_custom_constants_override_a_constant():
    body = {
        "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 3.2},
        "formula": "haigis",
        "a_constant": 118.7,
        "haigis_constants": {"a0": 1.80, "a1": 0.40, "a2": 0.10},
    }
    data = run_calculation(body)
    eye = data["right_eye"]

    assert eye["used_inputs"]["a0"] == 1.8
    assert eye["used_inputs"]["a1"] == 0.4
    assert eye["used_inputs"]["a2"] == 0.1
    assert eye["used_inputs"]["a_constant"] is None
    assert "a_constant" in eye["ignored_inputs"]
    assert "自定义 a0" in eye["constants"]


def test_haigis_constants_accepted_when_only_model_is_haigis():
    """回归：在线 Barrett 失败后切 Haigis，仅传 model 不带 formula 也要可用。"""
    body = {
        "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 3.2},
        "a_constant": 118.7,
        "model": "haigis",
        "haigis_constants": {"a0": 1.80, "a1": 0.40, "a2": 0.10},
    }
    data = run_calculation(body)

    assert data["calculation_model"] == "haigis"
    assert data["formula"] == "haigis"
    eye = data["right_eye"]
    assert eye["used_inputs"]["a0"] == 1.8
    assert eye["used_inputs"]["a_constant"] is None


def test_hoffer_q_uses_extracted_pacd_when_model_is_hoffer_q():
    body = reference_body()
    body["model"] = "hoffer_q"
    body["hoffer_q_pacd"] = 5.25
    data = run_calculation(body)

    eye = data["right_eye"]
    assert eye["used_inputs"]["pACD"] == 5.25
    assert "pACD=5.25 mm" in eye["constants"]


def test_hoffer_q_pacd_is_rejected_for_other_formulas():
    body = reference_body()
    body["hoffer_q_pacd"] = 5.25
    with pytest.raises(InputValidationError, match="hoffer_q_pacd"):
        CalculationRequest.from_mapping(body)


def test_haigis_constants_are_rejected_for_other_formulas():
    with pytest.raises(InputValidationError, match="haigis_constants"):
        CalculationRequest.from_mapping(
            {
                "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
                "formula": "srkt",
                "haigis_constants": {"a0": 1.8, "a1": 0.4, "a2": 0.1},
            }
        )


def test_haigis_missing_acd_uses_documented_default():
    data = run_calculation(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "formula": "haigis",
            "a_constant": 118.7,
        }
    )

    eye = data["right_eye"]
    assert eye["used_inputs"]["ACD"] == 3.2
    assert eye["used_inputs"]["ACD_defaulted"] is True
    assert eye["low_confidence"] is True
    assert any("缺少术前 ACD" in warning for warning in eye["warnings"])


def test_barrett_missing_optional_inputs_warns_without_silent_default():
    data = run_calculation(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "a_constant": 118.7,
            "model": "barrett_ii_offline",
        }
    )

    eye = data["right_eye"]
    assert eye["used_inputs"]["ACD"] is None
    assert eye["used_inputs"]["LenThickness"] is None
    assert eye["used_inputs"]["WTW"] is None
    assert eye["low_confidence"] is True
    assert any("未提供" in warning for warning in eye["warnings"])


def test_non_barrett_online_is_rejected_before_any_network_call(monkeypatch):
    called = False

    async def fail_online(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("不应调用官网")

    monkeypatch.setattr(formula.barrett_online, "calculate_barrett_iol", fail_online)

    request = CalculationRequest.from_mapping(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "formula": "srkt",
            "mode": "online",
        }
    )
    with pytest.raises(UnsupportedModeError, match="Barrett"):
        asyncio.run(formula.calculate(request))
    assert called is False


@pytest.mark.parametrize("bad_value", [True, float("nan"), float("inf"), "abc"])
def test_non_finite_and_boolean_inputs_are_rejected(bad_value):
    with pytest.raises(ValueError):
        CalculationRequest.from_mapping(
            {"right_eye": {"AL": bad_value, "K1": 43.5, "K2": 44.0}}
        )


@pytest.mark.parametrize("a_constant", [0, 50, 126, 200])
def test_invalid_a_constant_is_rejected(a_constant):
    with pytest.raises(ValueError, match="a_constant"):
        CalculationRequest.from_mapping(
            {
                "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
                "a_constant": a_constant,
                "model": "barrett_ii_offline",
            }
        )


def test_acd_out_of_physical_range_is_rejected():
    with pytest.raises(ValueError, match="ACD"):
        CalculationRequest.from_mapping(
            {
                "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 9.0},
                "a_constant": 118.7,
            }
        )


def test_out_of_range_axial_length_is_rejected_at_boundary():
    with pytest.raises(ValueError, match="AL"):
        CalculationRequest.from_mapping(
            {
                "right_eye": {"AL": 9.0, "K1": 43.5, "K2": 44.0},
                "a_constant": 118.7,
            }
        )


def test_both_eyes_are_calculated_independently():
    body = reference_body()
    body["left_eye"] = {
        "AL": 24.5,
        "K1": 42.5,
        "K2": 43.0,
        "ACD": 3.1,
        "Refraction": 0,
        "LenThickness": 4.4,
        "WTW": 11.7,
    }
    data = run_calculation(body)

    assert data["right_eye"]["biometry"] != data["left_eye"]["biometry"]
    assert data["right_eye"]["provided_inputs"]["AL"] == 23.5
    assert data["left_eye"]["provided_inputs"]["AL"] == 24.5


def test_toric_request_parsing_preserves_raw_eye_fields():
    request = ToricCalculationRequest.from_mapping(
        {
            "toric_right_eye": {
                "AL": "24.0",
                "K1": "43.0",
                "K1Axis": "10",
                "K2": "44.0",
                "K2Axis": "100",
                "ACD": "3.2",
            },
            "a_constant": 119.3,
            "k_index": "1.332",
            "cylinder_mode": "+ve",
        }
    )

    assert request.right_eye["AL"] == "24.0"
    assert request.right_eye["K1Axis"] == "10"
    assert request.k_index == 1.332
    assert request.cylinder_mode == "+ve"


def test_offline_calculation_does_not_open_network_sockets(monkeypatch):
    def blocked_connection(*args, **kwargs):
        raise AssertionError("离线计算不应创建网络连接")

    monkeypatch.setattr(socket, "create_connection", blocked_connection)
    data = run_calculation(reference_body())

    assert data["mode"] == "offline"
    assert data["right_eye"]["iol_options"]


@pytest.mark.parametrize(
    ("model", "expected_formula", "expected_mode"),
    [
        ("barrett_ii_offline", "barrett", "offline"),
        ("srkt", "srkt", "offline"),
        ("hoffer_q", "hoffer_q", "offline"),
        ("haigis", "haigis", "offline"),
    ],
)
def test_calculation_model_selects_formula_and_mode(
    model, expected_formula, expected_mode
):
    body = reference_body()
    body["model"] = model
    body["formula"] = "haigis"
    body["mode"] = "online"
    data = run_calculation(body)

    assert data["calculation_model"] == model
    assert data["formula"] == expected_formula
    assert data["mode"] == expected_mode


@pytest.mark.parametrize("model", ["barrett_ii_offline", "srkt", "hoffer_q", "haigis"])
def test_web_payload_with_only_model_works_for_every_formula(model):
    """模拟 Web 端切换公式后的实际 payload：只传 model，不传 formula/mode。"""
    body = {
        "patient_name": None,
        "a_constant": 118.7,
        "iol_model": "Personal Constant",
        "k_index": 1.3375,
        "right_eye": {
            "AL": 23.5,
            "K1": 43.5,
            "K2": 44.0,
            "ACD": 3.2,
            "Refraction": 0.0,
            "SiliconeOil": False,
        },
        "model": model,
    }
    if model == "haigis":
        # Web 端只有切到 Haigis 时才附加常数
        body["haigis_constants"] = {"a0": 1.8, "a1": 0.4, "a2": 0.1}

    data = run_calculation(body)

    assert data["calculation_model"] == model
    assert data["mode"] == "offline"
    assert data["right_eye"]["iol_options"]


def test_barrett_online_model_uses_online_adapter(monkeypatch):
    async def fake_online(**kwargs):
        return {"right_eye": {"iol_options": []}}

    monkeypatch.setattr(
        formula.barrett_online, "calculate_barrett_iol", fake_online
    )
    body = reference_body()
    body["model"] = "barrett_ii"
    data = run_calculation(body)

    assert data["calculation_model"] == "barrett_ii"
    assert data["formula"] == "barrett"
    assert data["mode"] == "online"


def test_unknown_calculation_model_is_rejected():
    body = reference_body()
    body["model"] = "barrett_v"
    with pytest.raises(ValueError, match="model 只支持"):
        run_calculation(body)


def test_formula_capabilities_are_declared_for_every_formula():
    capabilities = {item["name"]: item for item in formula.list_formulas()}

    assert capabilities["barrett"]["modes"] == ("offline", "online")
    for name in ("srkt", "hoffer_q", "haigis"):
        assert capabilities[name]["modes"] == ("offline",)
    assert capabilities["haigis"]["ignored_inputs"] == (
        "LenThickness",
        "WTW",
    )
    assert math.isfinite(run_calculation(reference_body())["right_eye"]["elp"])
