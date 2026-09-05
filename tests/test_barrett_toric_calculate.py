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
    assert result["K1"] == 41.5
    assert result["K1Axis"] == 84
    assert result["K2"] == 43.85
    assert result["K2Axis"] == 174
    assert result["ACD"] == 3.25
    assert result["incision_location"] == 10


def test_worker_ai_cleans_k_axes_for_toric_reuse():
    worker = api.WorkerAI()
    cleaned = worker._validate_and_clean_data(
        {
            "right_eye": {
                "AL": "24.43 mm",
                "K1": "41.50 D",
                "K1Axis": "84°",
                "K2": "43.85 D",
                "K2Axis": "174°",
            },
            "left_eye": {"K1_axis": 91, "K2Axis": 181},
        }
    )
    assert cleaned["right_eye"]["K1Axis"] == 84.0
    assert cleaned["right_eye"]["K2Axis"] == 174.0
    assert cleaned["left_eye"]["K1Axis"] == 91.0
    assert cleaned["left_eye"]["K2Axis"] is None


def test_worker_ai_consensus_allows_one_degree_axis_tolerance():
    worker = api.WorkerAI()
    data_points = [
        {
            "patient_name": "Test",
            "a_constant": 119,
            "right_eye": {
                "AL": 24.43,
                "K1": 41.5,
                "K1Axis": 84.0,
                "K2": 43.85,
                "K2Axis": 174.0,
                "ACD": 3.25,
            },
            "left_eye": {},
        },
        {
            "patient_name": "Test",
            "a_constant": 119,
            "right_eye": {
                "AL": 24.43,
                "K1": 41.5,
                "K1Axis": 84.5,
                "K2": 43.85,
                "K2Axis": 174.5,
                "ACD": 3.25,
            },
            "left_eye": {},
        },
        {
            "patient_name": "Test",
            "a_constant": 119,
            "right_eye": {
                "AL": 24.43,
                "K1": 41.5,
                "K1Axis": 84.0,
                "K2": 43.85,
                "K2Axis": 174.0,
                "ACD": 3.25,
            },
            "left_eye": {},
        },
    ]

    result = worker._perform_consensus_analysis(
        [{"data": data} for data in data_points]
    )

    assert result["details"]["right_eye.K1Axis"]["has_consensus"]
    assert result["details"]["right_eye.K2Axis"]["has_consensus"]
    assert result["consensus_data"]["right_eye"]["K1Axis"] == pytest.approx(84.1667)
    assert result["consensus_data"]["right_eye"]["K2Axis"] == pytest.approx(174.1667)


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


def test_normalize_toric_eye_defaults_incision_location_to_135():
    eye = sample_eye()
    eye.pop("IncisionLocation")
    result = barrett_toric_calculate.normalize_toric_eye_params(eye, "右眼")
    assert result["incision_location"] == 135.0


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

    payload = fake_session.post_payloads[-1]
    assert payload["ctl00$MainContent$Aconstant"] == "119.35"
    assert payload["ctl00$MainContent$OpticalACD"] == "3.25"
    assert payload["ctl00$MainContent$DoctorName"] == ""
    assert payload["ctl00$MainContent$LensFactor"] == " 2.04"
    assert payload["ctl00$MainContent$MeasuredK"] == "41.50"
    assert payload["ctl00$MainContent$MeasuredK0"] == "43.85"
    assert payload["ctl00$MainContent$MeasuredAxis"] == "84.00"
    assert payload["ctl00$MainContent$MeasuredAxis0"] == "174.00"
    assert payload["ctl00$MainContent$AxLength"] == "24.43"
    assert payload["ctl00$MainContent$Eye Select"] == "Rad1"
    assert payload["ctl00$MainContent$RadioButtonList1"] == "337.5"
    assert payload["ctl00$MainContent$RadioButtonList2"] == "-1"
    assert "ctl00$MainContent$Cylinder" not in payload
    assert result["right_eye"]["iol_options"][0]["toric_power"] == "T5"
    assert result["right_eye"]["toric_axis"] == 175
    assert (
        result["right_eye"]["axis_image"]["source_url"]
        == barrett_toric_calculate.BARRETT_TORIC_IMAGE_URL
    )


def test_toric_payload_accepts_canonical_k_names(monkeypatch):
    fake_session = FakeSession()
    monkeypatch.setattr(
        barrett_toric_calculate.requests, "Session", lambda: fake_session
    )
    eye = sample_eye()
    eye = {
        "K1": eye["K1"],
        "K1Axis": eye["K1Axis"],
        "K2": eye["K2"],
        "K2Axis": eye["K2Axis"],
        "AL": eye["AxialLength"],
        "ACD": eye["ACD"],
        "SIA": eye["SIA"],
        "IncisionLocation": eye["IncisionLocation"],
        "LensThickness": eye["LensThickness"],
        "WTW": eye["WTW"],
    }
    asyncio.run(barrett_toric_calculate.calculate_barrett_toric_iol(right_eye_params=eye))
    payload = fake_session.post_payloads[-1]
    assert payload["ctl00$MainContent$MeasuredK"] == "41.50"
    assert payload["ctl00$MainContent$MeasuredAxis"] == "84.00"
    assert payload["ctl00$MainContent$MeasuredK0"] == "43.85"
    assert payload["ctl00$MainContent$MeasuredAxis0"] == "174.00"


def test_toric_default_incision_angle_is_135_in_ui_and_openapi():
    page = webui.get_webui_page()
    assert 'id="toricRightIncision" value="135"' in page
    assert 'id="toricLeftIncision" value="135"' in page
    assert (
        docs.get_openapi_spec()["components"]["schemas"]["ToricEye"]["properties"]
        ["incision_location"]["default"]
        == 135
    )


def test_current_toric_result_parser_reads_official_fields_and_tables():
    html = """
    <input id="MainContent_PatientName" value="Test">
    <input id="MainContent_MeasuredK" value="41.50">
    <input id="MainContent_MeasuredAxis" value="84">
    <input id="MainContent_MeasuredK0" value="43.85">
    <input id="MainContent_MeasuredAxis0" value="174">
    <input id="MainContent_AxLength" value="24.43">
    <input id="MainContent_OpticalACD" value="3.25">
    <table id="MainContent_GridView1">
      <tr><th>IOL Power</th><th>Toric Power</th><th>Refraction</th></tr>
      <tr><td>20.0 S.E.</td><td>T6</td><td>-0.35 S.E.</td></tr>
    </table>
    <table id="MainContent_GridView2">
      <tr><th>Toric Power</th><th>IOL Cylinder</th><th>Residual Astigmatism</th></tr>
      <tr><td>T6</td><td>3.75</td><td>-0.12 Cyl Axis 85</td></tr>
    </table>
    """
    result = barrett_toric_calculate.parse_toric_results(
        html, selected_eye="right_eye"
    )
    eye = result["right_eye"]
    assert eye["K1"] == 41.5
    assert eye["K1Axis"] == 84
    assert eye["K2"] == 43.85
    assert eye["K2Axis"] == 174
    assert eye["AL"] == 24.43
    assert eye["iol_options"][0]["toric_power"] == "T6"
    assert eye["toric_options"][0]["axis"] == 85
    assert eye["toric_axis"] == 85


def test_toric_tab_postback_matches_web_forms_successful_controls():
    form = barrett_toric_calculate._successful_form_fields(
        """
        <input type='hidden' name='__VIEWSTATE' value='v'>
        <input type='hidden' name='__EVENTVALIDATION' value='e'>
        <input name='ctl00$MainContent$LensFactor' value=' 2.04'>
        <input name='ctl00$MainContent$RadioButtonList1' value='337.5'
               disabled='disabled' checked='checked'>
        <input name='ctl00$MainContent$Button1' value='Calculate'>
        <input name='ctl00$MainContent$NetCornealAstig'
               value='Net Astigmatism: 2.65 D @ 175 Degrees'>
        """
    )
    payload = barrett_toric_calculate._calculate_payload(
        form,
        None,
        None,
        a_constant=119.3,
        patient_name="Test",
        iol_model="Personal Constant",
        k_index=1.3375,
        cylinder_mode="-ve",
        event_target="ctl00$MainContent$menuTabs",
        event_argument="2",
    )
    assert payload["ctl00$MainContent$LensFactor"] == " 2.04"
    assert payload["ctl00$MainContent$NetCornealAstig"].startswith("Net Astigmatism")
    assert "ctl00$MainContent$Button1" not in payload
    assert payload["ctl00$MainContent$RadioButtonList1"] == "337.5"


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
    assert page.index('for="toricRightAL"') < page.index('for="toricRightFlatK"')
    assert page.index('for="toricRightFlatK"') < page.index(
        'for="toricRightFlatAxis"'
    )
    assert page.index('for="toricRightFlatAxis"') < page.index(
        'for="toricRightSteepK"'
    )
