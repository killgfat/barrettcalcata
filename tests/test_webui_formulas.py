"""Web UI 公式切换与执行方式开关的静态断言。"""

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

webui = importlib.import_module("webui")


def get_page() -> str:
    """返回 Web UI 的 HTML 页面文本。"""
    return webui.get_webui_page()


def test_formula_and_execution_mode_controls_exist():
    page = get_page()

    assert 'id="formulaSwitch"' in page
    assert 'id="executionModeControls"' in page
    assert 'id="executionModeHint"' in page
    assert 'id="formulaInputHint"' in page
    assert 'class="param-hint mode-switch-hint"' in page


def test_formula_switch_is_a_segmented_control_under_mode_switch():
    page = get_page()

    assert 'class="formula-switch" id="formulaSwitch"' in page
    assert page.index('id="sphericalModeButton"') < page.index('id="formulaSwitch"')
    assert page.index('id="formulaSwitch"') < page.index('id="executionModeControls"')
    for formula in ("barrett", "hoffer_q", "srkt", "haigis"):
        assert 'data-formula="' + formula + '"' in page


def test_default_formula_is_barrett_and_default_mode_is_online():
    page = get_page()

    barrett = page.index('data-formula="barrett"')
    assert barrett < page.index('data-formula="hoffer_q"')
    assert 'class="formula-button active" data-formula="barrett"' in page
    assert 'class="toggle-switch" id="executionModeSwitch"' in page
    assert 'role="switch" aria-checked="true"' in page
    assert 'id="executionModeState">在线<' in page
    assert "let selectedExecutionMode = 'online';" in page
    assert "updateExecutionToggle" in page


def test_formula_options_cover_all_supported_formulas():
    page = get_page()

    for label in ("Barrett Universal II", "Hoffer Q", "SRK/T", "Haigis"):
        assert label in page


def test_execution_mode_hint_wording_is_accurate():
    page = get_page()

    assert "在线调用 Barrett 官网，不保证稳定性" in page
    assert (
        "本地近似实现（Gaussian 聚散度 + 公开校准网格，非官方公式复刻），不保证准确性"
    ) in page
    assert "本地实现，基于公开发表公式；不保证准确性" in page


def test_haigis_constants_inputs_exist_and_are_optional():
    page = get_page()

    assert 'class="haigis-constants" id="haigisConstants" hidden' in page
    for field in ("a0", "a1", "a2"):
        assert 'id="haigisA' + field[-1] + '"' in page
    assert "readHaigisConstants" in page
    assert "payload.haigis_constants" in page


def test_formula_specific_input_hints_exist():
    page = get_page()

    assert "SRK/T 由 A 常数和 K 自行推导 ACD" in page
    assert "Hoffer Q 可使用报告中的 pACD" in page
    assert "Haigis 使用实测 ACD" in page
    assert "Barrett 本地/在线均使用 ACD" in page


def test_acd_no_longer_claims_a_global_3_00_default():
    page = get_page()

    assert page.count('placeholder="留空由公式决定"') == 2
    assert 'placeholder="默认3.00"' not in page
    assert 'min="0.5" max="8"' in page


def test_result_summary_shows_confidence_constants_and_input_usage():
    page = get_page()

    assert "formatUsedInputs" in page
    assert "used_inputs" in page
    assert "ignored_inputs" in page
    assert "置信度" in page
    assert "常数：" in page
    assert "警告：" in page
    assert "sortedOptions" in page
    assert "parseFloat(a.iol_power) - parseFloat(b.iol_power)" in page


def test_calculate_payload_sends_calculation_model():
    page = get_page()

    assert "fetch('/api/calculate'" in page
    assert "resolveCalculationModel" in page
    assert "return 'barrett_ii_offline' :" not in page
    assert "barrett_ii_offline" in page
    assert "barrett_ii'" in page
    assert "model: calculationModel" in page
    assert "formulaSelect" not in page
    assert "executionModeSelect" not in page
    assert "execution-mode-button" not in page
    assert "execution-mode-switch" not in page


def test_toric_mode_hides_formula_controls():
    page = get_page()

    assert "formulaSwitch.hidden = isToric;" in page
    assert "executionModeHint.hidden = isToric;" in page
    assert "syncFormulaControls();" in page


def test_select_formula_preserves_user_inputs_and_execution_mode():
    """切换公式不能清空输入，也不能强制重置执行模式。"""
    page = get_page()

    # 提取 selectFormula 函数体
    start = page.index("function selectFormula(name)")
    # 找到函数结束（下一个顶级 function）
    rest = page[start:]
    end = rest.index("\n        function ", 10)
    body = rest[:end]

    # 不允许在切换公式时清空输入或重置执行模式
    assert ".value = ''" not in body
    assert '.value = ""' not in body
    assert "selectedExecutionMode = 'online'" not in body
    assert "selectedExecutionMode = 'offline'" not in body
    # 必须重新验证表单（不同公式对必填项要求可能不同）
    assert "validateForm()" in body


def test_select_formula_shows_preservation_hint_when_data_present():
    """已有数据时切换公式应提示"参数已保留"。"""
    page = get_page()

    assert "hasAnyEyeData" in page
    assert "已保留之前填写/识别的参数" in page


def test_ai_formula_constants_are_filled_and_submitted():
    """Haigis 三常数与 Hoffer Q pACD 识别后可自动回填并用于计算。"""
    page = get_page()

    assert 'id="hofferQPacdControls"' in page
    assert 'id="hofferQPacd"' in page
    assert "const constants = data.haigis_constants" in page
    assert "haigisA0.value = Number(constants.a0).toFixed(3)" in page
    assert "data.hoffer_q_pacd" in page
    assert "payload.hoffer_q_pacd = hofferQPacdValue" in page


def test_page_does_not_claim_official_paper_implementation():
    page = get_page()

    assert "基于Barrett官方论文实现" not in page
