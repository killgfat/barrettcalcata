import asyncio
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


barrett_toric_calculate = importlib.import_module("barrett_toric_calculate")
api = importlib.import_module("api")
docs = importlib.import_module("docs")
webui = importlib.import_module("webui")


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.post_payloads = []

    def get(self, url):
        return FakeResponse(
            """
            <input name="__VIEWSTATE" value="viewstate">
            <input name="__VIEWSTATEGENERATOR" value="generator">
            <input name="__EVENTVALIDATION" value="validation">
            """
        )

    def post(self, url, data):
        self.post_payloads.append(data)
        return FakeResponse(
            """
            <input id="MainContent_ToricAxis" value="175">
            <table id="MainContent_GridView1">
              <tr><th>IOL Power</th><th>Toric</th><th>Axis</th><th>Refraction</th></tr>
              <tr><td>20.0</td><td>T5</td><td>175</td><td>-0.12</td></tr>
            </table>
            """
        )


def sample_eye():
    return {
        "K1": 41.5,
        "K1Axis": 84,
        "K2": 43.85,
        "K2Axis": 174,
        "AxialLength": 24.43,
        "ACD": 3.25,
        "Refraction": 0,
        "SIA": 0,
        "IncisionLocation": 10,
        "LensThickness": 4.21,
        "WTW": 11.8,
    }


def test_normalize_toric_eye_accepts_iol_master_aliases():
    result = barrett_toric_calculate.normalize_toric_eye_params(sample_eye(), "右眼")

    assert result["flat_k"] == 41.5
    assert result["flat_axis"] == 84
    assert result["steep_k"] == 43.85
    assert result["steep_axis"] == 174
    assert result["ACD"] == 3.25
    assert result["incision_location"] == 10


def test_normalize_toric_eye_rejects_missing_geometry_and_out_of_range_axis():
    with pytest.raises(ValueError, match="晶体厚度"):
        barrett_toric_calculate.normalize_toric_eye_params(
            {
                "flat_k": 41,
                "flat_axis": 0,
                "steep_k": 43,
                "steep_axis": 90,
                "AL": 24,
                "WTW": 11,
            },
            "右眼",
        )

    invalid = sample_eye()
    invalid["K1Axis"] = 181
    with pytest.raises(ValueError, match="Flat Axis"):
        barrett_toric_calculate.normalize_toric_eye_params(invalid, "右眼")


def test_barrett_toric_calculate_formats_payload_and_returns_axis_image(monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(
        barrett_toric_calculate.requests, "Session", lambda: fake_session
    )

    result = asyncio.run(
        barrett_toric_calculate.calculate_barrett_toric_iol(
            right_eye_params=sample_eye(),
            a_constant=119.346,
            k_index=1.3375,
        )
    )

    payload = fake_session.post_payloads[0]
    assert payload["ctl00$MainContent$Aconstant"] == "119.35"
    assert payload["ctl00$MainContent$OpticalACD"] == "3.25"
    assert payload["ctl00$MainContent$FlatAxis"] == "84.00"
    assert payload["ctl00$MainContent$SteepAxis"] == "174.00"
    assert payload["ctl00$MainContent$RadioButtonList1"] == "337.5"
    assert result["right_eye"]["iol_options"][0]["toric_power"] == "T5"
    assert result["right_eye"]["toric_axis"] == 175
    assert (
        result["right_eye"]["axis_image"]["source_url"]
        == barrett_toric_calculate.BARRETT_TORIC_IMAGE_URL
    )


@pytest.mark.asyncio
async def test_barrett_toric_api_handler_uses_independent_calculator(monkeypatch):
    handler = api.APIHandler(SimpleNamespace())
    captured = {}

    async def fake_calculate(**kwargs):
        captured.update(kwargs)
        return {"right_eye": {"axis_image": {"source_url": "image"}}}

    monkeypatch.setattr(api, "calculate_barrett_toric_iol", fake_calculate)
    result, status_code = await handler._handle_barrett_toric_calculate(
        {
            "right_eye": sample_eye(),
            "a_constant": 119.3,
            "k_index": 1.332,
            "cylinder_mode": "+ve",
        }
    )

    assert status_code == 200
    assert result["success"] is True
    assert captured["cylinder_mode"] == "+ve"
    assert captured["k_index"] == 1.332


def test_barrett_toric_endpoint_is_documented_and_rendered():
    specification = docs.get_openapi_spec()
    assert "/api/calculate-toric" in specification["paths"]
    assert "ToricEye" in specification["components"]["schemas"]

    page = webui.get_webui_page()
    assert "fetch('/api/calculate-toric'" in page
    assert 'id="toricRightFlatAxis"' in page
    assert 'id="toricResultsSection"' in page
    assert "Eye%20Background%20360.jpg" in page
