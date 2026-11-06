"""Castrop 公式（Langenbucher 2021）的实现与调度契约测试。"""

import asyncio
import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import formula
from formula import castrop
from formula.types import CalculationRequest, InputValidationError

REFERENCE_AL = 23.5
REFERENCE_K = 44.0
REFERENCE_ACD = 3.2
REFERENCE_LT = 4.6


def run_calculation(body):
    return asyncio.run(formula.calculate(CalculationRequest.from_mapping(body)))


def reference_body(**eye_overrides):
    eye = {
        "AL": REFERENCE_AL,
        "K1": 43.5,
        "K2": 44.5,
        "ACD": REFERENCE_ACD,
        "Refraction": 0,
        "LenThickness": REFERENCE_LT,
        "WTW": 11.9,
    }
    eye.update(eye_overrides)
    return {"right_eye": eye, "model": "castrop", "a_constant": 118.7}


# --- 几何与光学核心 ---------------------------------------------------------


def test_corneal_power_uses_thick_lens_model():
    """PCA/PCP 与厚透镜等效屈光度按论文参数逐项核对。"""
    cornea = castrop.corneal_power(REFERENCE_K)

    # RCA = 337.5/44 = 7.6705 mm，RCP = RCA*6.4/7.77
    assert cornea["r_front"] == pytest.approx(7.67045, abs=1e-5)
    assert cornea["r_back"] == pytest.approx(6.318006, abs=1e-5)
    # PCA = 0.376/0.0076705 = 49.019 D
    assert cornea["p_front"] == pytest.approx(49.019, abs=1e-2)
    # PCP = (1.336-1.376)/0.0063181 = -6.331 D
    assert cornea["p_back"] == pytest.approx(-6.331, abs=1e-2)
    # 厚透镜：49.019 - 6.331 - (0.55e-3/1.376)*49.019*(-6.331)
    assert cornea["p_cornea"] == pytest.approx(42.812, abs=1e-2)


def test_corneal_power_respects_keratometer_index():
    """K-index 1.332 与等效的 1.3375 读数给出同一前表面半径。"""
    # 1.332 折射率下的读数要乘 0.3375/0.332 才换算到 1.3375 基准，
    # 所以反向构造：alt_k * 0.3375/0.332 == REFERENCE_K。
    alt_k = REFERENCE_K * 0.332 / 0.3375
    assert castrop.corneal_power(REFERENCE_K, k_index=1.3375)[
        "r_front"
    ] == pytest.approx(castrop.corneal_power(alt_k, k_index=1.332)["r_front"])


def test_cooke_correction_matches_published_regression():
    assert castrop.corrected_al(23.5, 4.6) == pytest.approx(
        1.23854 + 0.95855 * 23.5 - 0.05467 * 4.6, abs=1e-12
    )


def test_elp_follows_paper_formula():
    """ELP = ACD + C*LT + H（论文 2021 原文的 Olsen 式）。"""
    result = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT
    )
    assert result["elp"] == pytest.approx(REFERENCE_ACD + 0.40 * REFERENCE_LT, abs=1e-9)

    shifted = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.424, "H": -0.312, "R": 0.077},
    )
    assert shifted["elp"] == pytest.approx(
        REFERENCE_ACD + 0.424 * REFERENCE_LT - 0.312, abs=1e-9
    )


def test_elp_models_match_iolcon_options():
    """三种 ELP 推导方式对应 IOLCon 的 ELP calculation 下拉。"""
    al_cor = castrop.corrected_al(REFERENCE_AL, REFERENCE_LT)
    r_front = castrop.corneal_power(REFERENCE_K)["r_front"]

    regression = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        elp_model="regression",
    )
    assert regression["elp"] == pytest.approx(
        0.045 * al_cor + 0.761 * REFERENCE_ACD - 0.042 * r_front + 0.40 * REFERENCE_LT,
        abs=1e-9,
    )

    no_r = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        elp_model="regression_no_r",
    )
    assert no_r["elp"] == pytest.approx(
        0.036 * al_cor + 0.753 * REFERENCE_ACD + 0.40 * REFERENCE_LT, abs=1e-9
    )


def test_explicit_elp_bypasses_constant_derivation():
    """调用方直接给 ELP（IOLCon 算出的位置）时不再走 C/H 推导。"""
    result = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        elp=5.30,
        constants={"C": 0.30, "H": 0.5, "R": 0.0},
    )
    assert result["elp"] == pytest.approx(5.30, abs=1e-9)
    assert result["castrop"]["elp_source"] == "provided"
    assert result["castrop"]["elp_model"] is None


def test_explicit_elp_matches_derived_elp():
    """给定 ELP 与推导出的 ELP 相同时，两条路径必须给出同一度数。"""
    derived = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.40, "H": 0.0, "R": 0.0},
    )
    explicit = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        elp=derived["elp"],
        constants={"C": 0.40, "H": 0.0, "R": 0.0},
    )
    assert explicit["iol_power_exact"] == pytest.approx(
        derived["iol_power_exact"], abs=1e-9
    )


def test_reference_power_is_stable():
    """冻结参考值：AL 23.5 / K 44 / ACD 3.2 / LT 4.6，target=0。"""
    result = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT
    )
    assert result["iol_power_exact"] == pytest.approx(21.2633, abs=1e-4)
    assert result["elp"] == pytest.approx(5.04, abs=1e-9)


@pytest.mark.parametrize("target", [-2.0, -0.5, 0.0, 1.0, 2.0])
def test_target_round_trip(target):
    """精确度数代回反解必须回到目标屈光度。"""
    result = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        target=target,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.424, "H": -0.312, "R": 0.077},
    )
    back = castrop.refraction_for_power(
        REFERENCE_AL,
        REFERENCE_K,
        result["iol_power_exact"],
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.424, "H": -0.312, "R": 0.077},
    )
    assert back == pytest.approx(target, abs=1e-6)


def test_r_offset_shifts_target_refraction():
    """R 作用于目标屈光度：R 增大等效于目标更负。"""
    base = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.40, "H": 0.0, "R": 0.0},
    )
    shifted = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.40, "H": 0.0, "R": 0.5},
    )
    # R=+0.5 等价于把目标改成 -0.5 D（术后近视留得更深），需要更高度数。
    assert shifted["iol_power_exact"] > base["iol_power_exact"]
    # 与直接给 -0.5 D 目标等价。
    explicit = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        target=-0.5,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.40, "H": 0.0, "R": 0.0},
    )
    assert shifted["iol_power_exact"] == pytest.approx(
        explicit["iol_power_exact"], abs=1e-9
    )


def test_elp_increase_raises_required_power():
    """IOL 后移（ELP 增大）缩短其到视网膜的距离，需要更高度数。"""
    front = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT, elp=4.8
    )
    back = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT, elp=5.6
    )
    assert back["iol_power_exact"] > front["iol_power_exact"]


def test_al_correction_can_be_disabled():
    with_correction = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT
    )
    without = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        al_correction=False,
    )
    assert with_correction["castrop"]["al_corrected"] != REFERENCE_AL
    assert without["castrop"]["al_corrected"] == REFERENCE_AL
    assert any("Cooke" in warning for warning in without["warnings"])


def test_missing_acd_and_lt_fall_back_with_warnings():
    result = castrop.calculate(REFERENCE_AL, REFERENCE_K)

    assert result["castrop"]["acd"] == 3.2
    assert result["castrop"]["lt"] == 4.6
    assert result["castrop"]["acd_defaulted"] is True
    assert result["castrop"]["lt_defaulted"] is True
    assert any("缺少术前 ACD" in warning for warning in result["warnings"])
    assert any("缺少晶状体厚度" in warning for warning in result["warnings"])


def test_missing_constants_warn_but_still_compute():
    result = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT
    )

    assert result["castrop"]["constants_provided"] is False
    assert result["castrop"]["C"] == 0.40
    assert result["low_confidence"] is True
    assert any("C=0.40" in warning for warning in result["warnings"])

    provided = castrop.calculate(
        REFERENCE_AL,
        REFERENCE_K,
        acd=REFERENCE_ACD,
        lt=REFERENCE_LT,
        constants={"C": 0.424, "H": -0.312, "R": 0.077},
    )
    assert provided["castrop"]["constants_provided"] is True
    assert provided["warnings"] == []


def test_table_has_nine_rows_and_one_recommendation():
    result = castrop.calculate(
        REFERENCE_AL, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT
    )
    options = result["iol_options"]
    assert len(options) == 9
    powers = [float(row["iol_power"]) for row in options]
    assert powers == sorted(powers)
    assert [row["recommended"] for row in options].count(True) == 1


# --- 输入校验 ---------------------------------------------------------------


@pytest.mark.parametrize("bad_c", [0.1, 0.9])
def test_out_of_range_c_is_rejected(bad_c):
    with pytest.raises(ValueError, match="Castrop C"):
        castrop.calculate(
            REFERENCE_AL,
            REFERENCE_K,
            acd=REFERENCE_ACD,
            lt=REFERENCE_LT,
            constants={"C": bad_c, "H": 0.0, "R": 0.0},
        )


@pytest.mark.parametrize("bad_h", [-2.0, 2.0])
def test_out_of_range_h_is_rejected(bad_h):
    with pytest.raises(ValueError, match="Castrop H"):
        castrop.calculate(
            REFERENCE_AL,
            REFERENCE_K,
            acd=REFERENCE_ACD,
            lt=REFERENCE_LT,
            constants={"C": 0.40, "H": bad_h, "R": 0.0},
        )


def test_elp_longer_than_axial_length_is_rejected():
    with pytest.raises(ValueError, match="ELP"):
        castrop.calculate(
            REFERENCE_AL,
            REFERENCE_K,
            acd=REFERENCE_ACD,
            lt=REFERENCE_LT,
            elp=30.0,
        )


def test_unknown_elp_model_is_rejected():
    with pytest.raises(ValueError, match="castrop_elp_model"):
        castrop.normalize_elp_model("deep-learning")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "acd_lt"),
        ("", "acd_lt"),
        ("ELP = ACD + C*LT + H", None),
        ("regression", "regression"),
        ("with ACD, AL and LT", "regression_no_r"),
        ("ACD_AL_R_LT", "regression"),
    ],
)
def test_elp_model_aliases(raw, expected):
    if expected is None:
        with pytest.raises(ValueError):
            castrop.normalize_elp_model(raw)
        return
    assert castrop.normalize_elp_model(raw) == expected


# --- 调度层契约 -------------------------------------------------------------


def test_model_castrop_dispatches_offline():
    data = run_calculation(reference_body())

    assert data["calculation_model"] == "castrop"
    assert data["formula"] == "castrop"
    assert data["formula_label"] == "Castrop"
    assert data["mode"] == "offline"
    eye = data["right_eye"]
    assert eye["used_inputs"]["C"] == 0.40
    assert eye["used_inputs"]["ELP"] == pytest.approx(5.04, abs=1e-9)
    assert eye["used_inputs"]["a_constant"] is None
    assert "a_constant" in eye["ignored_inputs"]
    assert eye["castrop_details"]["elp_source"] == "acd_lt"


def test_iolcon_constants_are_used_and_accepted():
    body = reference_body()
    body["castrop_constants"] = {"C": 0.424, "H": -0.312, "R": 0.077}
    data = run_calculation(body)

    eye = data["right_eye"]
    assert eye["used_inputs"]["C"] == 0.424
    assert eye["used_inputs"]["H"] == -0.312
    assert eye["used_inputs"]["R"] == 0.077
    assert data["constants_source"]["source"] == "castrop_constants"
    assert eye["warnings"] == []


def test_ulib_snapshot_never_overrides_castrop_constants():
    """选中 ULIB 型号也不能替换 C/H/R —— 表里根本没有这三列。"""
    body = reference_body(ACD=3.2)
    body["iol_model"] = "Alcon SN60WF"
    body["castrop_constants"] = {"C": 0.424, "H": -0.312, "R": 0.077}
    data = run_calculation(body)

    eye = data["right_eye"]
    assert eye["used_inputs"]["C"] == 0.424
    assert data["constants_source"]["source"] == "castrop_constants"
    assert data["constants_source"]["ulib_supported"] is False


def test_paper_default_is_reported_as_low_confidence():
    data = run_calculation(reference_body())
    assert data["constants_source"]["source"] == "paper_default"
    assert data["right_eye"]["low_confidence"] is True


def test_explicit_elp_is_accepted_at_api_boundary():
    body = reference_body()
    body["castrop_elp"] = 5.25
    body["castrop_elp_model"] = "regression"
    data = run_calculation(body)

    assert data["right_eye"]["elp"] == pytest.approx(5.25, abs=1e-9)
    assert data["right_eye"]["used_inputs"]["ELP_source"] == "provided"


def test_castrop_parameters_are_rejected_for_other_formulas():
    body = reference_body()
    body["model"] = "srkt"
    body["castrop_elp"] = 5.0
    with pytest.raises(InputValidationError, match="castrop"):
        CalculationRequest.from_mapping(body)


def test_castrop_online_is_rejected():
    body = reference_body()
    body.pop("model")
    body["formula"] = "castrop"
    body["mode"] = "online"
    with pytest.raises(ValueError, match="Barrett"):
        asyncio.run(formula.calculate(CalculationRequest.from_mapping(body)))


def test_capabilities_declare_castrop():
    capabilities = {item["name"]: item for item in formula.list_formulas()}
    castrop_caps = capabilities["castrop"]

    assert castrop_caps["modes"] == ("offline",)
    assert castrop_caps["required_inputs"] == ("AL", "K1", "K2")
    # ACD/LT 有默认值但属于核心输入，要在 optional 里明确列出。
    assert "ACD" in castrop_caps["optional_inputs"]
    assert "LenThickness" in castrop_caps["optional_inputs"]
    assert "a_constant" in castrop_caps["ignored_inputs"]


def test_both_eyes_are_calculated_independently():
    body = reference_body()
    body["left_eye"] = {
        "AL": 25.5,
        "K1": 42.5,
        "K2": 43.0,
        "ACD": 3.4,
        "Refraction": 0,
        "LenThickness": 4.2,
    }
    data = run_calculation(body)

    assert float(data["right_eye"]["recommended_power"]) > float(
        data["left_eye"]["recommended_power"]
    )
    assert data["right_eye"]["elp"] != data["left_eye"]["elp"]


def test_a_constant_is_ignored_only_when_a_dedicated_constant_exists():
    """A 常数在四套公式里的角色：兜底、被专用常数取代、完全不参与。"""
    eye = {
        "AL": 23.5,
        "K1": 43.5,
        "K2": 44.5,
        "ACD": 3.2,
        "LenThickness": 4.6,
    }

    def state(**overrides):
        body = {
            "right_eye": dict(eye),
            "a_constant": 118.7,
            **overrides,
        }
        return run_calculation(body)["right_eye"]

    # Hoffer Q：没有 pACD 时由 A 常数推导 pACD，A 必须留在 used_inputs。
    plain = state(model="hoffer_q")
    assert plain["used_inputs"]["a_constant"] == 118.7
    assert "a_constant" not in plain["ignored_inputs"]

    # Hoffer Q：给了 pACD 后 A 常数不再参与。
    with_pacd = state(model="hoffer_q", hoffer_q_pacd=5.25)
    assert with_pacd["used_inputs"]["a_constant"] is None
    assert "a_constant" in with_pacd["ignored_inputs"]

    # Haigis：同理，三常数取代由 A 常数近似出来的 a0。
    haigis_plain = state(model="haigis")
    assert haigis_plain["used_inputs"]["a_constant"] == 118.7
    assert "a_constant" not in haigis_plain["ignored_inputs"]

    haigis_const = state(
        model="haigis",
        haigis_constants={"a0": 1.8, "a1": 0.4, "a2": 0.1},
    )
    assert haigis_const["used_inputs"]["a_constant"] is None
    assert "a_constant" in haigis_const["ignored_inputs"]

    # Castrop：有没有 C/H/R，A 常数都不参与。
    castrop_plain = state(model="castrop")
    assert castrop_plain["used_inputs"]["a_constant"] is None
    assert "a_constant" in castrop_plain["ignored_inputs"]

    castrop_const = state(
        model="castrop",
        castrop_constants={"C": 0.424, "H": -0.312, "R": 0.077},
    )
    assert castrop_const["used_inputs"]["a_constant"] is None
    assert "a_constant" in castrop_const["ignored_inputs"]


def test_castrop_result_is_independent_of_a_constant():
    """Castrop 没有 A 常数到 C/H/R 的换算关系，改 A 不能影响结果。"""
    eye = {
        "AL": 23.5,
        "K1": 43.5,
        "K2": 44.5,
        "ACD": 3.2,
        "LenThickness": 4.6,
    }
    resolved = []
    for a_constant in (112.0, 118.7, 125.0):
        data = run_calculation(
            {
                "model": "castrop",
                "right_eye": dict(eye),
                "a_constant": a_constant,
                "castrop_constants": {"C": 0.424, "H": -0.312, "R": 0.077},
            }
        )["right_eye"]
        resolved.append(
            (data["castrop_details"]["elp"], float(data["recommended_power"]))
        )
    assert len(set(resolved)) == 1


def test_iol_model_list_is_empty_for_castrop():
    """ULIB 没有 Castrop 的 C/H/R，服务端就不该给出型号列表。"""
    models, info = formula.list_iol_models("castrop")

    assert info["formula"] == "castrop"
    assert info["source"] == "none"
    assert info["constants_available"] is False
    assert models == []
    assert info["warnings"], "必须说明为什么不提供型号"
    assert "castrop_constants" in info["warnings"][0]


def test_other_formulas_still_return_their_model_list():
    """空列表只针对 Castrop，其它 ULIB 公式不受影响。"""
    for name in ("srkt", "hoffer_q", "haigis", "haigis-toric"):
        models, info = formula.list_iol_models(name)
        assert info["constants_available"] is True
        assert models and info["source"] == "ulib"


def test_short_eye_is_low_confidence():
    result = castrop.calculate(21.0, REFERENCE_K, acd=REFERENCE_ACD, lt=REFERENCE_LT)
    assert result["low_confidence"] is True
    assert any("AL=" in warning for warning in result["warnings"])


def test_all_numbers_are_reported_as_rounded_floats():
    data = run_calculation(reference_body())
    eye = data["right_eye"]

    assert math.isfinite(eye["elp"])
    assert eye["elp"] == round(eye["elp"], 2)
    assert eye["predicted_refraction"] == round(eye["predicted_refraction"], 2)
    assert isinstance(eye["castrop_details"]["p_cornea"], float)
