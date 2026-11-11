import importlib
import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

formulas = importlib.import_module("formula")
barrett_offline = importlib.import_module("formula.barrett")
ulib_constants = importlib.import_module("formula.constants")

FORMULA_MODULES = {
    "barrett": formulas.barrett,
    "srkt": formulas.srkt,
    "hoffer_q": formulas.hoffer_q,
    "holladay1": formulas.holladay1,
    "haigis": formulas.haigis,
    "castrop": formulas.castrop,
}

# 本文件验证球镜公式的共同契约；散光所需轴位及三常数另有专门测试。
FORMULA_NAMES = list(FORMULA_MODULES)

REFERENCE_AL = 23.5
REFERENCE_K = 44.0
REFERENCE_A = 118.7


def refraction_from_exact_power(name, al, k, iol_power, a_constant=REFERENCE_A):
    """用各公式的反解或离线核心验证正反解一致性。"""
    if name == "barrett":
        return barrett_offline.predict_refraction(
            al, k, a_constant=a_constant, iol_power=iol_power
        )
    return FORMULA_MODULES[name].refraction_for_power(
        al, k, iol_power, a_constant=a_constant
    )


@pytest.mark.parametrize("name", FORMULA_NAMES)
def test_formula_returns_unified_nine_row_result(name):
    result = formulas.calculate_formula(name, REFERENCE_AL, REFERENCE_K)

    assert result["model"]
    assert result["model_note"]
    assert result["constants_text"]
    assert math.isfinite(result["iol_power"])
    assert math.isfinite(result["iol_power_exact"])
    assert math.isfinite(result["predicted_refraction"])
    assert math.isfinite(result["elp"])
    assert result["confidence"] in ("OK", "LOW_CONFIDENCE")
    assert result["low_confidence"] is (result["confidence"] == "LOW_CONFIDENCE")

    options = result["iol_options"]
    assert len(options) == 9
    powers = [float(row["iol_power"]) for row in options]
    assert powers == sorted(powers)
    recommended = [row for row in options if row["recommended"]]
    assert len(recommended) == 1
    assert float(recommended[0]["iol_power"]) == result["iol_power"]
    assert recommended[0]["iol_power"] == result["iol_power_text"]
    # 本地公式不知道具体晶体设计；不再硬编码 Biconvex。
    assert recommended[0]["optic"] is None
    assert len(recommended[0]["refraction"].split(".")[1]) == 2


@pytest.mark.parametrize("name", FORMULA_NAMES)
@pytest.mark.parametrize("target", [-2.0, 0.0, 1.0])
def test_formula_target_round_trip(name, target):
    result = formulas.calculate_formula(name, REFERENCE_AL, REFERENCE_K, target=target)
    refraction = refraction_from_exact_power(
        name,
        REFERENCE_AL,
        REFERENCE_K,
        result["iol_power_exact"],
    )

    assert refraction == pytest.approx(target, abs=1e-6)


@pytest.mark.parametrize("name", FORMULA_NAMES)
@pytest.mark.parametrize("target", [-2.0, 0.0, 1.0])
def test_recommended_refraction_tracks_target(name, target):
    result = formulas.calculate_formula(name, REFERENCE_AL, REFERENCE_K, target=target)

    assert abs(result["predicted_refraction"] - target) < 0.3


@pytest.mark.parametrize("name", FORMULA_NAMES)
def test_elp_is_independent_of_target(name):
    base = formulas.calculate_formula(name, REFERENCE_AL, REFERENCE_K, target=0.0)
    for target in (-2.0, 1.0):
        other = formulas.calculate_formula(
            name, REFERENCE_AL, REFERENCE_K, target=target
        )
        assert other["elp"] == pytest.approx(base["elp"], abs=1e-9)


@pytest.mark.parametrize("name", FORMULA_NAMES)
def test_step_one_degree_yields_integer_powers(name):
    result = formulas.calculate_formula(name, REFERENCE_AL, REFERENCE_K, step=1.0)

    for row in result["iol_options"]:
        power = float(row["iol_power"])
        assert power == int(power)
        assert row["iol_power"] == str(int(power))


@pytest.mark.parametrize("name", FORMULA_NAMES)
def test_short_eye_is_low_confidence(name):
    result = formulas.calculate_formula(name, 21.0, 44.0)

    assert result["low_confidence"] is True
    assert any("AL=" in warning for warning in result["warnings"])


@pytest.mark.parametrize("name", FORMULA_NAMES)
def test_out_of_range_axial_length_is_rejected(name):
    with pytest.raises(ValueError, match="AL"):
        formulas.calculate_formula(name, 9.0, 44.0)


def test_srkt_frozen_reference_values():
    # 输入与来源：Retzlaff 1990 的 SRK/T，A=118.7；target=0 时与
    # scripts/calibrate_offline.py::srkt_power 逐位一致（差 <1e-13）。
    # AL=23.5 走 Lcor=AL 分支，AL=26.0 走 Lcor 多项式分支。
    assert formulas.srkt.calculate(23.5, 44.0)["iol_power_exact"] == pytest.approx(
        20.3958680004, abs=1e-6
    )
    assert formulas.srkt.calculate(26.0, 42.0)["iol_power_exact"] == pytest.approx(
        15.0054401494, abs=1e-6
    )
    # 非零 target 按 Retzlaff 1990 附录公式 (10)，与校准脚本 srkt_power 一致。
    assert formulas.srkt.calculate(23.5, 44.0, target=1.0)[
        "iol_power_exact"
    ] == pytest.approx(18.9019240704, abs=1e-6)


def test_srkt_target_derivative_is_clinically_directed():
    # 非零 target 只通过 K' 进入光学部分；dP/dRx 应为负、量级约 1 D/D。
    low = formulas.srkt.calculate(23.5, 44.0, target=-1.0)["iol_power_exact"]
    high = formulas.srkt.calculate(23.5, 44.0, target=1.0)["iol_power_exact"]
    derivative = (high - low) / 2.0
    assert -1.8 < derivative < -0.8


def test_hoffer_q_frozen_reference_values():
    # 输入与来源：Hoffer 1993 公式，A=118.7，target=0。
    # AL=22.0 走 m=1/g=28 分支；AL=23.5/24.5 走 m=-1/g=23.5 分支。
    assert formulas.hoffer_q.calculate(22.0, 44.0)["iol_power_exact"] == pytest.approx(
        25.7341015593, abs=1e-6
    )
    assert formulas.hoffer_q.calculate(23.0, 44.0)["iol_power_exact"] == pytest.approx(
        21.9969036891, abs=1e-6
    )
    assert formulas.hoffer_q.calculate(23.5, 44.0)["iol_power_exact"] == pytest.approx(
        20.2261181952, abs=1e-6
    )
    # AL 超出 18.5-31.0 时仅 Q 修正使用截断值，光学计算仍用原始 AL。
    assert formulas.hoffer_q.calculate(32.0, 44.0)["iol_power_exact"] == pytest.approx(
        -3.7617436309, abs=1e-6
    )
    assert formulas.hoffer_q.calculate(24.5, 43.0)["iol_power_exact"] == pytest.approx(
        18.2360205273, abs=1e-6
    )


@pytest.mark.parametrize("target", [-2.0, 0.0, 1.0])
@pytest.mark.parametrize("k_index", [1.3375, 1.332])
def test_hoffer_q_explicit_pacd_target_round_trip(target, k_index):
    result = formulas.hoffer_q.calculate(
        REFERENCE_AL, REFERENCE_K, target=target, k_index=k_index, pacd=6.0
    )
    refraction = formulas.hoffer_q.refraction_for_power(
        REFERENCE_AL,
        REFERENCE_K,
        result["iol_power_exact"],
        k_index=k_index,
        pacd=6.0,
    )

    assert refraction == pytest.approx(target, abs=1e-6)


@pytest.mark.parametrize("target", [-2.0, 0.0, 1.0])
def test_hoffer_q_ulib_pacd_target_round_trip(target):
    entry = ulib_constants.lookup("Alcon SN60WF")
    assert entry is not None
    assert entry.pacd is not None
    result = formulas.hoffer_q.calculate(
        REFERENCE_AL, REFERENCE_K, target=target, pacd=entry.pacd
    )
    refraction = formulas.hoffer_q.refraction_for_power(
        REFERENCE_AL,
        REFERENCE_K,
        result["iol_power_exact"],
        pacd=entry.pacd,
    )

    assert refraction == pytest.approx(target, abs=1e-6)


@pytest.mark.parametrize("a_constant", [112.0, 118.7, 125.0])
def test_hoffer_q_explicit_pacd_ignores_a_constant(a_constant):
    reference = formulas.hoffer_q.calculate(
        REFERENCE_AL, REFERENCE_K, pacd=6.0
    )
    result = formulas.hoffer_q.calculate(
        REFERENCE_AL, REFERENCE_K, a_constant=a_constant, pacd=6.0
    )
    reference_refraction = formulas.hoffer_q.refraction_for_power(
        REFERENCE_AL, REFERENCE_K, 21.5, pacd=6.0
    )
    refraction = formulas.hoffer_q.refraction_for_power(
        REFERENCE_AL,
        REFERENCE_K,
        21.5,
        a_constant=a_constant,
        pacd=6.0,
    )

    assert result["iol_power_exact"] == pytest.approx(
        reference["iol_power_exact"], abs=1e-9
    )
    assert refraction == pytest.approx(reference_refraction, abs=1e-9)


def test_hoffer_q_refraction_default_pacd_preserves_legacy_call():
    # 旧位置参数与冻结正视度数保持兼容；None 仍表示由 A 常数推导。
    args = (REFERENCE_AL, REFERENCE_K, 20.2261181952, REFERENCE_A, 1.3375)
    refraction = formulas.hoffer_q.refraction_for_power(*args)

    assert refraction == pytest.approx(0.0, abs=1e-6)
    assert formulas.hoffer_q.refraction_for_power(
        *args, pacd=None
    ) == pytest.approx(refraction, abs=1e-9)


@pytest.mark.parametrize(
    "pacd", [float("nan"), float("inf"), float("-inf"), "invalid", True]
)
def test_hoffer_q_refraction_rejects_invalid_pacd(pacd):
    with pytest.raises(ValueError, match="pACD"):
        formulas.hoffer_q.refraction_for_power(
            REFERENCE_AL, REFERENCE_K, 21.5, pacd=pacd
        )


def test_holladay1_frozen_reference_values():
    # 输入与来源：Holladay 1988，A=118.7 -> SF=0.5663*118.7-65.60=1.6238 mm。
    # AL=23.5 走 AG=12.5*AL/23.45=12.526 < 13.5 分支；
    # AL=32.0 走 AG 截断到 13.5 分支。
    assert formulas.holladay1.calculate(23.5, 44.0)["iol_power_exact"] == pytest.approx(
        19.5288944156, abs=1e-6
    )
    assert formulas.holladay1.calculate(26.0, 42.0)["iol_power_exact"] == pytest.approx(
        14.1931574682, abs=1e-6
    )
    assert formulas.holladay1.calculate(22.0, 44.0)["iol_power_exact"] == pytest.approx(
        24.7706889787, abs=1e-6
    )
    assert formulas.holladay1.calculate(32.0, 44.0)["iol_power_exact"] == pytest.approx(
        -3.9072598172, abs=1e-6
    )
    assert formulas.holladay1.calculate(24.5, 43.0)["iol_power_exact"] == pytest.approx(
        17.6120724160, abs=1e-6
    )


def test_holladay1_elp_matches_published_geometry():
    # 论文式：ELP = 0.56 + (rag - sqrt(rag^2 - AG^2/4)) + SF。
    result = formulas.holladay1.calculate(23.5, 44.0)
    sf = 0.5663 * 118.7 - 65.60
    radius = 337.5 / 44.0
    diameter = 12.5 * 23.5 / 23.45
    height = radius - math.sqrt(radius * radius - diameter * diameter / 4.0)

    assert result["elp"] == pytest.approx(0.56 + height + sf, abs=1e-9)
    # 角膜半径不小于 7 mm：K=60 D 时 rag 截断到 7 mm。
    high_k = formulas.holladay1.calculate(23.5, 60.0)
    assert high_k["elp"] == pytest.approx(
        0.56 + (7.0 - math.sqrt(49.0 - diameter * diameter / 4.0)) + sf,
        abs=1e-9,
    )


def test_holladay1_explicit_sf_overrides_a_constant():
    # 显式 SF 与 ULIB 优化值是同一条路径：ELP 平移量正好等于 SF 之差。
    derived = formulas.holladay1.calculate(23.5, 44.0, a_constant=118.7)
    explicit = formulas.holladay1.calculate(23.5, 44.0, sf=1.84)
    derived_sf = 0.5663 * 118.7 - 65.60

    assert explicit["elp"] - derived["elp"] == pytest.approx(
        1.84 - derived_sf, abs=1e-9
    )
    assert explicit["warnings"] == []
    assert "未提供晶体专属 SF" in derived["warnings"][0]


def test_holladay1_target_is_applied_through_corneal_plane():
    # 目标屈光度只进入光学部分，ELP 不变；dP/dRx 应为负、量级约 1 D/D。
    low = formulas.holladay1.calculate(23.5, 44.0, target=-1.0)["iol_power_exact"]
    high = formulas.holladay1.calculate(23.5, 44.0, target=1.0)["iol_power_exact"]
    derivative = (high - low) / 2.0

    assert -1.8 < derivative < -0.8


def test_haigis_frozen_reference_value():
    # 输入与来源：Haigis 2000 三常数（a1=0.4, a2=0.1），
    # A=118.7 -> a0=1.7143，实测 ACD=3.2 mm，target=0。
    result = formulas.haigis.calculate(23.5, 44.0, acd=3.2)

    # Dc = 331.5 / r（Haigis 的 1.3315 约定），不是直接用 1.3375 的 K。
    assert result["iol_power_exact"] == pytest.approx(21.3347964482, abs=1e-6)
    assert result["elp"] == pytest.approx(5.3443, abs=1e-3)


def test_haigis_without_custom_constants_warns_about_iol_master_difference():
    result = formulas.haigis.calculate(REFERENCE_AL, REFERENCE_K, acd=3.2)

    assert result["low_confidence"] is True
    assert any("IOL Master" in warning for warning in result["warnings"])


def test_haigis_without_acd_warns_and_downgrades_confidence():
    result = formulas.haigis.calculate(REFERENCE_AL, REFERENCE_K)

    assert result["low_confidence"] is True
    assert any("缺少术前 ACD" in warning for warning in result["warnings"])


def test_k_index_1332_is_normalized_to_reference():
    alt_k = REFERENCE_K * 0.3375 / 0.332

    result = formulas.srkt.calculate(23.5, REFERENCE_K, k_index=1.332)
    reference = formulas.srkt.calculate(23.5, alt_k)

    assert result["iol_power_exact"] == pytest.approx(
        reference["iol_power_exact"], abs=1e-9
    )


def test_normalize_formula_accepts_defaults_and_case():
    assert formulas.normalize_formula(None) == "barrett"
    assert formulas.normalize_formula("") == "barrett"
    assert formulas.normalize_formula("  SRKT ") == "srkt"
    assert formulas.normalize_formula("Hoffer_Q") == "hoffer_q"
    assert formulas.FORMULA_NAMES == (
        "barrett",
        "srkt",
        "hoffer_q",
        "holladay1",
        "haigis",
        "castrop",
        "haigis-toric",
    )


def test_normalize_formula_rejects_unknown_name():
    with pytest.raises(ValueError, match="formula 只支持"):
        formulas.normalize_formula("holladay2")


def test_get_formula_label_returns_display_name():
    assert formulas.get_formula_label("barrett") == "Barrett Universal II"
    assert formulas.get_formula_label("srkt") == "SRK/T"
    assert formulas.get_formula_label("hoffer_q") == "Hoffer Q"
    assert formulas.get_formula_label("holladay1") == "Holladay 1"
    assert formulas.get_formula_label("haigis") == "Haigis"
    assert formulas.get_formula_label("castrop") == "Castrop"
