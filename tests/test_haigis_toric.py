"""Haigis-T 的独立光学、矢量约定及 API 回归测试；不访问外部网络。"""

import asyncio
import json
import math
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import formula
from api import APIHandler
from docs import get_openapi_spec
from formula import haigis, haigis_toric
from formula.common import astigmatism_vector, vector_astigmatism
from formula.types import CalculationRequest, HaigisConstants
from worker_ai import WorkerAI

CONSTANTS = {"a0": 1.4, "a1": 0.4, "a2": 0.1}


def solve(**overrides):
    params = {
        "al": 24,
        "k": 45,
        "k1": 44,
        "k2": 46,
        "k1_axis": 0,
        "k2_axis": 90,
        "acd": 3,
        "constants": CONSTANTS,
        "iol_spherical_equivalent": 20,
        "cylinder_powers": [0, 1.5, 2.25, 3, 3.75],
    }
    params.update(overrides)
    return haigis_toric.calculate(**params)


def request_body(**overrides):
    body = {
        "model": "haigis-toric",
        "haigis_constants": CONSTANTS,
        "right_eye": {
            "AL": 24,
            "K1": 44,
            "K2": 46,
            "K1Axis": 0,
            "K2Axis": 90,
            "ACD": 3,
            "iol_cylinder": 3,
            "iol_axis": 90,
            "iol_spherical_equivalent": 20,
            "cylinder_powers": [0, 1.5, 2.25, 3, 3.75],
        },
    }
    body.update(overrides)
    return body


@pytest.mark.parametrize(
    ("axis", "expected"), [(90, (-2, 0)), (0, (2, 0)), (45, (0, 2))]
)
def test_wtr_atr_oblique_full_cylinder_vectors(axis, expected):
    vector = astigmatism_vector(2, axis)
    assert vector == pytest.approx(expected, abs=1e-12)
    restored = vector_astigmatism(*vector)
    assert restored["cylinder"] == pytest.approx(2)
    assert restored["axis"] == pytest.approx(axis)
    assert restored["minus_cylinder_axis"] == pytest.approx((axis + 90) % 180)
    assert astigmatism_vector(2, axis + 180) == pytest.approx(vector)
    opposite = astigmatism_vector(-2, axis)
    zero = vector_astigmatism(vector[0] + opposite[0], vector[1] + opposite[1])
    assert zero["cylinder"] == 0
    assert zero["axis"] is None
    assert zero["minus_cylinder_axis"] is None


def test_oblique_vectors_add_with_double_angle():
    # 1 D@0 + 1 D@45 -> sqrt(2) D@22.5，不是轴位的普通角度加法。
    horizontal = astigmatism_vector(1, 0)
    oblique = astigmatism_vector(1, 45)
    result = vector_astigmatism(
        horizontal[0] + oblique[0], horizontal[1] + oblique[1]
    )
    assert result["cylinder"] == pytest.approx(math.sqrt(2))
    assert result["axis"] == pytest.approx(22.5)


def test_decimal_hand_calculated_reference_and_overcorrection_axis():
    # 手算：d=1.4+0.4*3+0.1*24=5 mm；t=5/1336，B=1336/19-20。
    # h=1.1883075953356445，Ci=3；f=1/(h²-(3t/2)²)。
    # Ca=(46-44)*331.5/337.5=1.9644444444444444 D@90。
    result = solve(iol_cylinder=3, iol_axis=90)
    assert result["elp"] == pytest.approx(5)
    assert result["corneal_factor"] == pytest.approx(0.7081935166422379)
    assert result["corneal_correction"] == pytest.approx(2.124580549926714)
    residual = result["residual_astigmatism"]
    assert residual["cylinder"] == pytest.approx(0.1601361054822692)
    assert residual["axis"] == pytest.approx(0, abs=1e-10)
    assert residual["minus_cylinder_axis"] == pytest.approx(90)
    assert residual["plane"] == "corneal"
    assert result["recommended_iol_cylinder"] == 3


@pytest.mark.parametrize("target", [-2, 0, 1])
def test_spherical_part_and_elp_are_exactly_reused(target):
    result = solve(target=target)
    sphere = haigis.calculate(
        24, 45, acd=3, constants=CONSTANTS, target=target
    )
    for field in (
        "elp",
        "iol_power",
        "iol_power_exact",
        "predicted_refraction",
        "iol_options",
        "constants_text",
    ):
        assert result[field] == sphere[field]
    assert result["elp"] == pytest.approx(5)


def test_target_changes_factor_via_selected_spherical_power():
    results = [
        solve(target=t, iol_spherical_equivalent=None) for t in (-2, 0, 1)
    ]
    assert all(row["elp"] == pytest.approx(5) for row in results)
    factors = [row["corneal_factor"] for row in results]
    assert factors[0] > factors[1] > factors[2]


@pytest.mark.parametrize("cylinder", [0, 1.5, 3, 6])
def test_residual_matches_independent_ray_propagation(cylinder):
    # 独立光线验证：折射 -> 房水平移 -> IOL 折射 -> 玻璃体平移。
    # 用试探入射聚散度 0/1 的视网膜高度解两子午线所需屈光矫正，
    # 不调用被测因子公式或 Haigis 的反解。
    def retina_height(corneal_power, iol_power, refraction):
        slope = refraction - corneal_power
        height = 1 + (0.005 / 1.336) * slope
        slope -= iol_power * height
        return height + (0.019 / 1.336) * slope

    def required_refraction(corneal_power, iol_power):
        y0 = retina_height(corneal_power, iol_power, 0)
        y1 = retina_height(corneal_power, iol_power, 1)
        return -y0 / (y1 - y0)

    r_flat = required_refraction(44 * 331.5 / 337.5, 20 + cylinder / 2)
    r_steep = required_refraction(46 * 331.5 / 337.5, 20 - cylinder / 2)
    result = solve(iol_cylinder=cylinder, iol_axis=90)
    assert result["residual_astigmatism"]["cylinder"] == pytest.approx(
        abs(r_flat - r_steep), abs=1e-10
    )


def test_factor_changes_with_elp_and_cylinder_without_fixed_ratio():
    shallow = solve(constants={"a0": 0.4, "a1": 0.4, "a2": 0.1})
    deep = solve(constants={"a0": 2.4, "a1": 0.4, "a2": 0.1})
    assert shallow["corneal_factor"] > deep["corneal_factor"]
    assert (
        solve(iol_cylinder=6, iol_axis=90)["corneal_factor"]
        > solve()["corneal_factor"]
    )


@pytest.mark.parametrize("rotation", [0, 45, 90, 135, 179])
def test_rotating_eye_and_implant_preserves_residual_magnitude(rotation):
    base = solve(iol_cylinder=2, iol_axis=100)
    rotated = solve(
        k1_axis=rotation,
        k2_axis=(90 + rotation) % 180,
        iol_cylinder=2,
        iol_axis=(100 + rotation) % 180,
    )
    a = base["residual_astigmatism"]
    b = rotated["residual_astigmatism"]
    assert b["cylinder"] == pytest.approx(a["cylinder"])
    assert b["axis"] == pytest.approx((a["axis"] + rotation) % 180)


def test_continuous_recommendation_cancels_astigmatism():
    first = solve()
    corrected = solve(
        iol_cylinder=first["recommended_iol_cylinder_exact"],
        iol_axis=first["recommended_axis"],
    )
    assert corrected["residual_astigmatism"]["cylinder"] == 0
    assert corrected["residual_astigmatism"]["axis"] is None
    options = first["toric_options"]
    assert len([o for o in options if o["recommended"]]) == 1
    chosen = next(o for o in options if o["recommended"])
    assert chosen["residual_astigmatism"]["cylinder"] == min(
        o["residual_astigmatism"]["cylinder"] for o in options
    )


def test_misalignment_increases_residual_and_options_use_optimal_axis():
    first = solve()
    cylinder = first["recommended_iol_cylinder_exact"]
    aligned = solve(iol_cylinder=cylinder, iol_axis=90)
    rotated = solve(iol_cylinder=cylinder, iol_axis=120)
    assert aligned["residual_astigmatism"]["cylinder"] == 0
    # 同量矢量旋转 30 度，残余等于原始柱镜量值。
    assert rotated["residual_astigmatism"]["cylinder"] == pytest.approx(
        first["net_astigmatism"]["cylinder"]
    )
    assert all(o["axis"] == 90 for o in rotated["toric_options"])


def test_ignoring_pca_overcorrects_wtr_and_undercorrects_atr():
    for flat_axis, steep_axis, residual_axis in [(0, 90, 0), (90, 0, 0)]:
        ignored = solve(k1_axis=flat_axis, k2_axis=steep_axis)
        included = solve(
            k1_axis=flat_axis, k2_axis=steep_axis, posterior_mode="estimated"
        )
        if steep_axis == 90:
            assert (
                ignored["recommended_iol_cylinder_exact"]
                > included["recommended_iol_cylinder_exact"]
            )
        else:
            assert (
                ignored["recommended_iol_cylinder_exact"]
                < included["recommended_iol_cylinder_exact"]
            )
        actual = solve(
            k1_axis=flat_axis,
            k2_axis=steep_axis,
            posterior_mode="estimated",
            iol_cylinder=ignored["recommended_iol_cylinder_exact"],
            iol_axis=ignored["recommended_axis"],
        )
        assert actual["residual_astigmatism"]["cylinder"] == pytest.approx(
            0.30
        )
        assert actual["residual_astigmatism"]["axis"] == pytest.approx(
            residual_axis, abs=1e-10
        )
        assert any(
            "UNVERIFIED-PENDING-PRIMARY" in w for w in actual["warnings"]
        )


def test_measured_pca_uses_optical_axis_and_can_be_oblique():
    measured = solve(
        posterior_mode="measured", posterior_cylinder=0.4, posterior_axis=45
    )
    vector = measured["net_astigmatism"]["vector"]
    assert vector["x"] == pytest.approx(-2 * 331.5 / 337.5)
    assert vector["y"] == pytest.approx(0.4)
    assert 45 < measured["recommended_axis"] < 90


def test_sica_flattens_incision_meridian_and_oblique_incision_rotates_axis():
    base = solve()
    steep = solve(incision_sia=0.4, incision_location=90)
    flat = solve(incision_sia=0.4, incision_location=180)
    oblique = solve(incision_sia=0.4, incision_location=45)
    assert steep["net_astigmatism"]["cylinder"] == pytest.approx(
        base["net_astigmatism"]["cylinder"] - 0.4
    )
    assert flat["net_astigmatism"]["cylinder"] == pytest.approx(
        base["net_astigmatism"]["cylinder"] + 0.4
    )
    assert (
        steep["recommended_iol_cylinder_exact"]
        < base["recommended_iol_cylinder_exact"]
        < flat["recommended_iol_cylinder_exact"]
    )
    assert oblique["recommended_axis"] > 90
    assert (
        solve(incision_sia=0.4, incision_location=270)["net_astigmatism"]
        == steep["net_astigmatism"]
    )


@pytest.mark.parametrize("source", ["TK", "TCRP"])
def test_total_measurement_replaces_anterior_and_pca_not_added_twice(source):
    measured = solve(
        posterior_mode="total",
        total_cylinder=1.1,
        total_axis=80,
        total_source=source,
        incision_sia=0.2,
        incision_location=80,
    )
    assert measured["posterior_astigmatism"] is None
    assert measured["net_astigmatism"]["cylinder"] == pytest.approx(0.9)
    assert measured["net_astigmatism"]["axis"] == pytest.approx(80)
    assert measured["iol_power_exact"] == solve()["iol_power_exact"]


def test_missing_inventory_does_not_invent_discrete_cylinder_steps():
    result = solve(cylinder_powers=None)
    assert result["toric_options"] == []
    assert result["recommended_iol_cylinder"] is None
    assert result["recommended_iol_cylinder_exact"] > 0


def test_zero_astigmatism_has_no_axis_and_recommends_available_zero_cylinder():
    result = solve(k1=45, k2=45)
    assert result["recommended_axis"] is None
    assert result["recommended_iol_cylinder"] == 0
    assert result["recommended_iol_cylinder_exact"] == 0
    assert result["residual_astigmatism"]["cylinder"] == 0
    assert result["residual_astigmatism"]["axis"] is None


def test_openapi_describes_local_toric_parameters_and_required_constants():
    spec = get_openapi_spec()
    eye_schema = spec["components"]["schemas"]["HaigisToricEye"]
    assert "ACD" in eye_schema["required"]
    assert "K1Axis" in eye_schema["required"]
    assert "default" not in eye_schema["properties"]["ACD"]
    assert eye_schema["properties"]["posterior_mode"]["default"] == "none"
    request_schema = spec["paths"]["/api/calculate"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    toric_branch = request_schema["allOf"][0]["oneOf"][1]
    # 三常数可直接给，也可由命中 ULIB 的 iol_model 查表得到。
    assert toric_branch["anyOf"] == [
        {"required": ["haigis_constants"]},
        {"required": ["iol_model"]},
    ]
    assert toric_branch["properties"]["model"]["enum"] == ["haigis-toric"]
    json.dumps(spec, allow_nan=False)


def test_k_index_equivalent_radii_have_same_optics():
    alternative = solve(
        k=45 * 0.332 / 0.3375,
        k1=44 * 0.332 / 0.3375,
        k2=46 * 0.332 / 0.3375,
        k_index=1.332,
    )
    assert alternative["net_astigmatism"]["cylinder"] == pytest.approx(
        solve()["net_astigmatism"]["cylinder"]
    )
    assert alternative["iol_power_exact"] == pytest.approx(
        solve()["iol_power_exact"]
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"al": 9},
        {"k1": 10, "k2": 80},
        {"k1": 46, "k2": 44},
        {"k": 44},
        {"acd": None},
        {"acd": 9},
        {"constants": None},
        {"constants": {"a0": 1.4, "a1": 0.4}},
        {"constants": {"a0": 20, "a1": 0.4, "a2": 0.1}},
        {"constants": {"a0": -10, "a1": 0, "a2": 0}},
        {"iol_cylinder": -1},
        {"iol_cylinder": 3},
        {"iol_axis": 181},
        {"k2_axis": 45},
        {"k2_axis": True},
        {"k1_axis": None},
        {"posterior_mode": []},
        {"posterior_mode": "measured"},
        {"posterior_cylinder": 0.3, "posterior_axis": 0},
        {"posterior_mode": "total", "total_source": "TK", "total_axis": 0},
        {
            "posterior_mode": "total",
            "total_source": "TK",
            "total_axis": 0,
            "total_cylinder": 1,
            "posterior_cylinder": 0.3,
        },
        {"total_cylinder": 1},
        {"incision_sia": 0.3},
        {"incision_sia": -0.3},
        {"incision_location": 361},
        {"cylinder_powers": []},
        {"cylinder_powers": "3"},
        {"cylinder_powers": [0, float("nan")]},
        {"target": 31},
        {"iol_spherical_equivalent": -11},
        {"iol_spherical_equivalent": 46},
        {"iol_spherical_equivalent": -1e300},
        {"iol_cylinder": 1000, "iol_axis": 90},
    ],
)
def test_invalid_or_ambiguous_inputs_are_rejected(overrides):
    with pytest.raises(ValueError):
        solve(**overrides)


@pytest.mark.parametrize("bad", [True, float("inf"), float("nan"), "abc"])
def test_non_finite_inputs_rejected(bad):
    for name in [
        "al",
        "acd",
        "iol_spherical_equivalent",
        "iol_cylinder",
        "k1_axis",
    ]:
        with pytest.raises(ValueError):
            solve(**{name: bad})


def test_dispatch_model_constants_rounding_and_both_eyes_without_network(
    monkeypatch,
):
    def no_network(*args, **kwargs):
        raise AssertionError("本地散光计算不应访问网络")

    monkeypatch.setattr(socket, "create_connection", no_network)
    body = request_body()
    body["right_eye"]["ACD"] = 3.004
    body["left_eye"] = {
        **body["right_eye"],
        "K1Axis": 90,
        "K2Axis": 180,
        "iol_axis": 0,
    }
    # 验证 worker_ai 已有三常数输出可直接打通 model=haigis-toric。
    cleaned = WorkerAI(api_key="test")._validate_and_clean_data(body)
    body["haigis_constants"] = cleaned["haigis_constants"]
    request = CalculationRequest.from_mapping(body)
    result = asyncio.run(formula.calculate(request))
    assert result["formula"] == "haigis-toric"
    assert result["calculation_model"] == "haigis-toric"
    assert result["mode"] == "offline"
    assert result["formula_capabilities"]["supports_toric"] is True
    for name in ["right_eye", "left_eye"]:
        eye = result[name]
        assert eye["used_inputs"]["a0"] == 1.4
        assert eye["used_inputs"]["ACD"] == 3
        assert eye["used_inputs"]["a_constant"] is None
        assert "a_constant" in eye["ignored_inputs"]
        assert eye["low_confidence"] is True
        assert eye["toric_options"]
    assert result["right_eye"]["residual_astigmatism"][
        "axis"
    ] == pytest.approx(0, abs=1e-10)
    assert result["left_eye"]["residual_astigmatism"]["axis"] == pytest.approx(
        90
    )
    json.dumps(result, allow_nan=False)


def test_legacy_formula_dispatch_and_sync_entry():
    body = request_body()
    body.pop("model")
    body["formula"] = "haigis-toric"
    assert (
        asyncio.run(formula.calculate(CalculationRequest.from_mapping(body)))[
            "calculation_model"
        ]
        == "haigis-toric"
    )
    sync = formula.calculate_formula(
        "haigis-toric",
        24,
        45,
        acd=3,
        k1=44,
        k2=46,
        k1_axis=0,
        k2_axis=90,
        constants=HaigisConstants(**CONSTANTS),
    )
    assert sync["elp"] == pytest.approx(5)


@pytest.mark.asyncio
async def test_api_success_and_missing_axis_validation():
    handler = APIHandler(SimpleNamespace())
    response, status = await handler._handle_barrett_calculate(request_body())
    assert status == 200
    assert response["success"] is True
    assert response["data"]["right_eye"]["corneal_factor"] == pytest.approx(
        0.7081935166422379
    )
    body = request_body()
    del body["right_eye"]["K1Axis"]
    response, status = await handler._handle_barrett_calculate(body)
    assert status == 400
    assert response["error"] == "Bad Request"
