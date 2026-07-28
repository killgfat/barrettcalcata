import importlib
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

api = importlib.import_module("api")
webui = importlib.import_module("webui")
docs = importlib.import_module("docs")


@pytest.mark.asyncio
async def test_calculate_defaults_null_a_constant(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())
    captured = {}

    async def fake_calculate(**kwargs):
        captured.update(kwargs)
        return {"result": "ok"}

    monkeypatch.setattr(api, "calculate_iol", fake_calculate)

    result, status_code = await handler._handle_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0},
            "a_constant": None,
        }
    )

    assert status_code == 200
    assert result["success"] is True
    assert captured["a_constant"] == 119.3


@pytest.mark.asyncio
async def test_calculate_rounds_a_constant_and_acd_to_two_decimals(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())
    captured = {}

    async def fake_calculate(**kwargs):
        captured.update(kwargs)
        return {"result": "ok"}

    monkeypatch.setattr(api, "calculate_iol", fake_calculate)

    result, status_code = await handler._handle_calculate(
        {
            "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 2.456},
            "a_constant": 119.346,
        }
    )

    assert status_code == 200
    assert result["success"] is True
    assert captured["a_constant"] == 119.35
    assert captured["right_eye_params"]["ACD"] == 2.46


@pytest.mark.asyncio
async def test_calculate_rejects_null_required_eye_value():
    handler = api.APIHandler(SimpleNamespace())

    result, status_code = await handler._handle_calculate(
        {
            "right_eye": {"AL": None, "K1": 43.5, "K2": 44.0},
        }
    )

    assert status_code == 400
    assert result["error"] == "Bad Request"
    assert "右眼AL" in result["message"]


def test_web_ui_uses_supported_worker_endpoints():
    page = webui.get_webui_page()

    assert "fetch('/api/extract'" in page
    assert "fetch('/api/calculate'" in page
    assert "fetch('/api'," not in page


def test_openapi_documents_image_extraction_endpoint():
    specification = docs.get_openapi_spec()

    assert "/api/extract" in specification["paths"]
    assert "post" in specification["paths"]["/api/extract"]
