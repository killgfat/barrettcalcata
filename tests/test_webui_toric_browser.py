"""散光 Web 表单浏览器回归；使用临时 Playwright 测试依赖。

运行：uv run --with playwright pytest tests/test_webui_toric_browser.py
首次运行需：uv run --with playwright playwright install chromium
可用 PLAYWRIGHT_CHROMIUM_EXECUTABLE 指定本地 Chromium。
未安装 Playwright 时，普通 pytest 跳过此模块。
"""

import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from formula.formula import calculate
from formula.types import CalculationRequest
from webui import get_webui_page


@pytest.fixture
def ui():
    """以真实页面和本地 Haigis-T 结果运行，所有网络均拦截。"""
    with (
        ThreadPoolExecutor(max_workers=1) as calculations,
        sync_playwright() as playwright,
    ):
        launch = {"headless": True}
        if executable := os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
            launch["executable_path"] = executable
        browser = playwright.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def respond(route):
            request = route.request
            if request.method == "POST":
                body = request.post_data_json
                requests.append((request.url, body))
                if request.url.endswith("/api/calculate"):
                    data = calculations.submit(
                        lambda: asyncio.run(
                            calculate(CalculationRequest.from_mapping(body))
                        )
                    ).result()
                else:
                    data = {
                        "right_eye": {
                            "iol_options": [
                                {
                                    "iol_power": 20,
                                    "toric_power": "T3",
                                    "axis": 90,
                                    "refraction": 0,
                                }
                            ],
                            "axis_image": {"toric_axis": 90},
                        }
                    }
                route.fulfill(json={"success": True, "data": data})
            elif "/api/iol-models" in request.url:
                route.fulfill(json={"success": True, "data": {"models": []}})
            else:
                route.fulfill(content_type="text/html", body=get_webui_page())

        page.route("http://iol.test/**", respond)
        # 禁止测试流量触达 Barrett 站点（含图像）。
        page.route("https://**/*", lambda route: route.abort())
        page.goto("http://iol.test/")
        yield page, requests
        assert not errors
        browser.close()


def fill(page, values):
    """批量填写并触发表单原生 input/change 事件。"""
    for field, value in values.items():
        page.locator("#" + field).fill(str(value))


def start_haigis(page):
    """启用 Haigis-T 右眼并填写最小可计算参数。"""
    page.locator("#toricModeButton").click()
    page.locator('[data-toric-formula="haigis-toric"]').click()
    page.locator("#toricRightEyeEnabled").check()
    fill(
        page,
        {
            "haigisA0": 1.4,
            "haigisA1": 0.4,
            "haigisA2": 0.1,
            "toricRightAL": 24,
            "toricRightFlatK": 44,
            "toricRightFlatAxis": 0,
            "toricRightSteepK": 46,
            "toricRightSteepAxis": 90,
            "toricRightMeasuredACD": 3,
        },
    )


def test_required_values_and_all_enabled_eyes(ui):
    page, _ = ui
    start_haigis(page)
    button = page.locator("#toricCalculateBtn")
    assert button.is_enabled()
    fill(page, {"toricRightMeasuredACD": ""})
    assert button.is_disabled()  # 不把 Barrett 默认 3.00 充当实测 ACD。
    fill(page, {"toricRightMeasuredACD": 3})
    page.locator("#toricLeftEyeEnabled").check()
    assert button.is_disabled()
    page.locator("#toricLeftEyeEnabled").uncheck()
    fill(page, {"haigisA1": ""})
    assert button.is_disabled()
    fill(page, {"haigisA1": 0.4, "toricRightSteepAxis": 80})
    assert button.is_disabled()
    fill(page, {"toricRightSteepAxis": 90, "toricRightIolCylinder": 3})
    assert button.is_disabled()
    fill(page, {"toricRightIolAxis": 90, "toricRightCylinderPowers": "0,,3"})
    assert button.is_disabled()
    fill(page, {"toricRightCylinderPowers": "0, 1.5, 2.25, 3"})
    assert button.is_enabled()
    fill(page, {"toricRightSIA": 0.3, "toricRightHaigisIncision": ""})
    assert button.is_disabled()
    fill(page, {"toricRightHaigisIncision": 135})
    assert button.is_enabled()


@pytest.mark.parametrize("mode", ["none", "measured", "total", "estimated"])
def test_haigis_payload_and_actual_result(ui, mode):
    page, requests = ui
    start_haigis(page)
    fill(
        page,
        {
            "toricRightIolCylinder": 3,
            "toricRightIolAxis": 90,
            "toricRightCylinderPowers": "0, 1.5, 2.25, 3",
            "toricRightRefraction": -1,
        },
    )
    # 先输入 PCA 再换模式；隐藏字段不能导致重复计入 PCA。
    page.locator("#toricRightPosteriorMode").select_option("measured")
    assert page.locator("#toricCalculateBtn").is_disabled()
    fill(
        page,
        {"toricRightPosteriorCylinder": 0.3, "toricRightPosteriorAxis": 0},
    )
    page.locator("#toricRightPosteriorMode").select_option(mode)
    if mode == "total":
        assert page.locator("#toricRightPosteriorCylinder").is_hidden()
        assert page.locator("#toricCalculateBtn").is_disabled()
        fill(page, {"toricRightTotalCylinder": 1.7, "toricRightTotalAxis": 90})
        page.locator("#toricRightTotalSource").select_option("TCRP")
    if mode == "estimated":
        assert (
            "UNVERIFIED-PENDING-PRIMARY"
            in page.locator("#toricRightPosteriorHint").inner_text()
        )
    page.locator("#toricCalculateBtn").click()
    page.locator("#toricResultsContent .result-card").wait_for()
    url, body = requests[-1]
    assert url.endswith("/api/calculate")
    assert body["model"] == "haigis-toric"
    assert body["haigis_constants"] == {"a0": 1.4, "a1": 0.4, "a2": 0.1}
    assert "a_constant" not in body
    assert "cylinder_mode" not in body
    eye = body["right_eye"]
    assert eye["ACD"] == 3
    assert eye["Refraction"] == -1
    assert eye["posterior_mode"] == mode
    assert eye["cylinder_powers"] == [0, 1.5, 2.25, 3]
    assert ("posterior_cylinder" in eye) == (mode == "measured")
    assert ("total_cylinder" in eye) == (mode == "total")
    assert "lens_thickness" not in eye
    assert "WTW" not in eye
    text = page.locator("#toricResultsContent").inner_text()
    assert "预期残余散光（角膜平面）" in text
    assert "等效负柱镜轴位" in text
    assert "UNVERIFIED-PENDING-PRIMARY" in text
    assert "原版 Barrett Toric" not in text
    assert "NaN" not in text


def test_barrett_path_and_switching_preserve_inputs(ui):
    page, requests = ui
    start_haigis(page)
    fill(page, {"toricRightIolCylinder": 3, "toricRightIolAxis": 90})
    page.locator('[data-toric-formula="barrett"]').click()
    assert page.locator("#haigisConstants").is_hidden()
    assert page.locator("#toricRightMeasuredACD").is_hidden()
    assert page.locator("#toricRightIolCylinder").is_hidden()
    assert page.locator("#toricCylinderMode").is_visible()
    fill(page, {"toricRightLT": 4.5, "toricRightWTW": 12})
    page.locator("#toricCalculateBtn").click()
    page.locator("#toricResultsContent .axis-result").wait_for()
    url, body = requests[-1]
    assert url.endswith("/api/calculate-toric")
    assert body["right_eye"]["lens_thickness"] == 4.5
    assert body["right_eye"]["incision_location"] == 135
    assert "iol_cylinder" not in body["right_eye"]
    assert "haigis_constants" not in body
    page.locator('[data-toric-formula="haigis-toric"]').click()
    assert page.locator("#toricRightMeasuredACD").input_value() == "3"
    assert page.locator("#toricRightIolCylinder").input_value() == "3"
    assert page.locator("#haigisA1").input_value() == "0.4"
    page.locator("#sphericalModeButton").click()
    page.locator('[data-formula="haigis"]').click()
    assert page.locator("#haigisConstants").is_visible()
    assert page.locator("#haigisA0").input_value() == "1.4"
    page.locator('[data-formula="barrett"]').click()
    assert page.locator("#executionModeControls").is_visible()


def test_ai_prefill_measured_acd_and_shared_constants(ui):
    page, _ = ui
    page.evaluate(
        """fillFormData({haigis_constants: {a0: 1.4, a1: 0.4, a2: 0.1},
            right_eye: {AL: 24, K1: 44, K1Axis: 0, K2: 46,
                        K2Axis: 90, ACD: 3.21}})"""
    )
    page.locator("#toricModeButton").click()
    page.locator('[data-toric-formula="haigis-toric"]').click()
    assert page.locator("#toricRightMeasuredACD").input_value() == "3.21"
    assert page.locator("#toricCalculateBtn").is_enabled()


@pytest.mark.parametrize("width", [390, 1280])
def test_responsive_form_and_results(ui, width):
    page, _ = ui
    page.set_viewport_size({"width": width, "height": 844})
    start_haigis(page)
    page.locator("#toricRightPosteriorMode").select_option("total")
    fill(page, {"toricRightTotalCylinder": 1.7, "toricRightTotalAxis": 90})
    page.locator("#toricCalculateBtn").click()
    page.locator("#toricResultsContent .result-card").wait_for()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
