import asyncio
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

barrett_calculate = importlib.import_module("barrett_calculate")


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

        if len(self.post_payloads) == 1:
            return FakeResponse(
                """
                <input name="__VIEWSTATE" value="viewstate2">
                <input name="__VIEWSTATEGENERATOR" value="generator2">
                <input name="__EVENTVALIDATION" value="validation2">
                <input name="ctl00$MainContent$LensFactor" value="lensfactor">
                """
            )

        return FakeResponse("<html></html>")


def test_barrett_calculate_formats_a_constant_and_acd_to_two_decimals(monkeypatch):
    fake_session = FakeSession()

    monkeypatch.setattr(barrett_calculate.requests, "Session", lambda: fake_session)
    monkeypatch.setattr(
        barrett_calculate,
        "parse_iol_results",
        lambda html: {"success": True},
    )

    result = asyncio.run(
        barrett_calculate.calculate_barrett_iol(
            right_eye_params={
                "AL": 23.5,
                "K1": 43.5,
                "K2": 44.0,
                "ACD": 2.4,
            },
            a_constant=119.3,
        )
    )

    assert result == {"success": True}
    assert fake_session.post_payloads[0]["ctl00$MainContent$Aconstant"] == "119.30"
    assert fake_session.post_payloads[0]["ctl00$MainContent$OpticalACD"] == "2.40"
    assert fake_session.post_payloads[1]["ctl00$MainContent$Aconstant"] == "119.30"
    assert fake_session.post_payloads[1]["ctl00$MainContent$OpticalACD"] == "2.40"


def test_barrett_calculate_converts_selected_k_index_to_barrett_form_value(monkeypatch):
    fake_session = FakeSession()

    monkeypatch.setattr(barrett_calculate.requests, "Session", lambda: fake_session)
    monkeypatch.setattr(
        barrett_calculate,
        "parse_iol_results",
        lambda html: {"success": True},
    )

    asyncio.run(
        barrett_calculate.calculate_barrett_iol(
            right_eye_params={
                "AL": 23.5,
                "K1": 43.5,
                "K2": 44.0,
            },
            k_index=1.3375,
        )
    )

    assert (
        fake_session.post_payloads[0]["ctl00$MainContent$RadioButtonList1"] == "337.5"
    )


def test_barrett_calculate_converts_alternate_k_index_to_barrett_form_value(
    monkeypatch,
):
    fake_session = FakeSession()

    monkeypatch.setattr(barrett_calculate.requests, "Session", lambda: fake_session)
    monkeypatch.setattr(
        barrett_calculate,
        "parse_iol_results",
        lambda html: {"success": True},
    )

    asyncio.run(
        barrett_calculate.calculate_barrett_iol(
            right_eye_params={
                "AL": 23.5,
                "K1": 43.5,
                "K2": 44.0,
            },
            k_index=1.332,
        )
    )

    assert fake_session.post_payloads[0]["ctl00$MainContent$RadioButtonList1"] == "332"
