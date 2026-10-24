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


def test_formula_specific_input_hints_exist():
    page = get_page()

    assert "SRK/T 由 A 常数和 K 自行推导 ACD" in page
    assert "Hoffer Q 由 A 常数和 AL/K 推导 pACD" in page
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


def test_calculate_payload_sends_formula_and_execution_mode():
    page = get_page()

    assert "formula:" in page
    assert "mode:" in page
    assert "mode: 'calculate'" not in page
    assert "fetch('/api/calculate'" in page
    assert "const formula = selectedFormula;" in page
    assert "formulaSelect" not in page
    assert "executionModeSelect" not in page
    assert "execution-mode-button" not in page
    assert "execution-mode-switch" not in page


def test_toric_mode_hides_formula_controls():
    page = get_page()

    assert "formulaSwitch.hidden = isToric;" in page
    assert "executionModeHint.hidden = isToric;" in page
    assert "syncFormulaControls();" in page


def test_page_does_not_claim_official_paper_implementation():
    page = get_page()

    assert "基于Barrett官方论文实现" not in page
