import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

api = importlib.import_module("api")
formula = importlib.import_module("formula")
webui = importlib.import_module("webui")
docs = importlib.import_module("docs")


@pytest.mark.asyncio
async def test_barrett_calculate_defaults_null_a_constant(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())
    captured = {}

    async def fake_calculate(request):
        captured["request"] = request
        return {"mode": "online"}

    monkeypatch.setattr(api, "calculate", fake_calculate)

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "a_constant": None,
            "mode": "online",
        }
    )

    assert status_code == 200
    assert result["success"] is True
    assert captured["request"].a_constant == 119.3


@pytest.mark.asyncio
async def test_barrett_calculate_rounds_a_constant_and_acd_to_two_decimals(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())
    captured = {}

    async def fake_calculate(request):
        captured["request"] = request
        return {"mode": "online"}

    monkeypatch.setattr(api, "calculate", fake_calculate)

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 2.456},
            "a_constant": 119.346,
            "mode": "online",
        }
    )

    assert status_code == 200
    assert result["success"] is True
    assert captured["request"].a_constant == 119.35
    assert captured["request"].right_eye.acd == 2.46


@pytest.mark.asyncio
async def test_barrett_calculate_normalizes_k_index(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())
    captured = {}

    async def fake_calculate(request):
        captured["request"] = request
        return {"mode": "online"}

    monkeypatch.setattr(api, "calculate", fake_calculate)

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "k_index": "1.3375",
            "mode": "online",
        }
    )

    assert status_code == 200
    assert result["success"] is True
    assert captured["request"].k_index == 1.3375


@pytest.mark.asyncio
async def test_barrett_calculate_rejects_unsupported_k_index():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "k_index": 1.34,
            "mode": "online",
        }
    )

    assert status_code == 400
    assert result["error"] == "Bad Request"
    assert "k_index" in result["message"]


@pytest.mark.asyncio
async def test_barrett_calculate_rejects_null_required_eye_value():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": None, "K1": 43.5, "K2": 44.0},
            "mode": "online",
        }
    )

    assert status_code == 400
    assert result["error"] == "Bad Request"
    assert "右眼AL" in result["message"]


@pytest.mark.asyncio
async def test_barrett_calculate_defaults_to_offline(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())

    async def fail_online(**kwargs):
        raise AssertionError("offline 模式不应调用官网")

    monkeypatch.setattr(formula.barrett_online, "calculate_barrett_iol", fail_online)

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {
                "AL": 23.5,
                "K1": 43.5,
                "K2": 44.0,
                "ACD": 3.2,
                "Refraction": 0,
                "LenThickness": "4.6",
                "WTW": "11.9",
            },
            "a_constant": 118.7,
        }
    )

    assert status_code == 200
    data = result["data"]
    assert data["mode"] == "offline"
    assert data["model"].startswith("BUII-ALK-offline")
    assert data["right_eye"]["iol_options"]
    assert data["right_eye"]["confidence"] in ("OK", "LOW_CONFIDENCE")
    assert data["left_eye"] is None


@pytest.mark.asyncio
async def test_barrett_calculate_offline_marks_low_confidence():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 21.0, "K1": 43.0, "K2": 44.0},
            "mode": "offline",
        }
    )

    assert status_code == 200
    eye = result["data"]["right_eye"]
    assert eye["confidence"] == "LOW_CONFIDENCE"
    assert any("AL=" in warning for warning in eye["warnings"])


@pytest.mark.asyncio
async def test_barrett_calculate_rejects_unknown_mode():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "mode": "bogus",
        }
    )

    assert status_code == 400
    assert result["error"] == "Bad Request"
    assert "mode" in result["message"]


@pytest.mark.asyncio
async def test_barrett_calculate_offline_rejects_out_of_range_al():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 9.0, "K1": 43.5, "K2": 44.0},
            "mode": "offline",
        }
    )

    assert status_code == 400
    assert "AL" in result["message"]


@pytest.mark.parametrize(
    ("formula", "expected_label"),
    [
        ("barrett", "Barrett Universal II"),
        ("srkt", "SRK/T"),
        ("hoffer_q", "Hoffer Q"),
        ("haigis", "Haigis"),
    ],
)
@pytest.mark.asyncio
async def test_barrett_calculate_dispatches_formula(formula, expected_label):
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 3.2},
            "formula": formula,
        }
    )

    assert status_code == 200
    data = result["data"]
    assert data["formula"] == formula
    assert data["formula_label"] == expected_label
    assert data["mode"] == "offline"
    assert data["right_eye"]["iol_options"]
    assert data["right_eye"]["constants"]
    assert data["right_eye"]["prediction"] == "offline"


@pytest.mark.asyncio
async def test_barrett_calculate_rejects_unknown_formula():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "formula": "holladay1",
        }
    )

    assert status_code == 400
    assert result["error"] == "Bad Request"
    assert "formula" in result["message"]


@pytest.mark.asyncio
async def test_barrett_calculate_rejects_online_for_non_barrett_formula():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "formula": "srkt",
            "mode": "online",
        }
    )

    assert status_code == 400
    assert result["error"] == "Bad Request"
    assert "Barrett" in result["message"]


@pytest.mark.asyncio
async def test_barrett_calculate_defaults_to_barrett_formula_offline():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_barrett_calculate(
        {"right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0}}
    )

    assert status_code == 200
    data = result["data"]
    assert data["formula"] == "barrett"
    assert data["formula_label"] == "Barrett Universal II"
    assert data["mode"] == "offline"


@pytest.mark.asyncio
async def test_barrett_calculate_online_reports_formula(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())

    async def fake_calculate(**kwargs):
        return {"right_eye": {"iol_options": []}}

    monkeypatch.setattr(formula.barrett_online, "calculate_barrett_iol", fake_calculate)

    result, status_code = await handler._handle_barrett_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "mode": "online",
        }
    )

    assert status_code == 200
    data = result["data"]
    assert data["formula"] == "barrett"
    assert data["formula_label"] == "Barrett Universal II"
    assert data["mode"] == "online"
    assert data["right_eye"]["iol_options"] == []


def test_web_ui_uses_supported_worker_endpoints():
    page = webui.get_webui_page()

    assert "fetch('/api/extract'" in page
    assert "fetch('/api/calculate'" in page
    assert "fetch('/api'," not in page
    assert 'id="kIndex"' in page
    assert "k_index:" in page
    assert "Barrett表单" not in page
    assert "337.5" not in page
    assert 'id="sphericalModeButton"' in page
    assert 'id="toricModeButton"' in page
    assert "setCalculationMode('toric')" in page
    assert 'id="toricSection" hidden' in page
    assert 'id="imageRecognitionSection"' in page
    assert "imageRecognitionSection.hidden = false" in page
    assert "imageUpload.value = '';" not in page


def test_openapi_documents_image_extraction_endpoint():
    specification = docs.get_openapi_spec()

    assert "/api/extract" in specification["paths"]
    assert "post" in specification["paths"]["/api/extract"]


def test_openapi_toric_uses_canonical_k_names():
    schema = docs.get_openapi_spec()["components"]["schemas"]["ToricEye"]
    assert schema["required"][:4] == ["K1", "K1Axis", "K2", "K2Axis"]
