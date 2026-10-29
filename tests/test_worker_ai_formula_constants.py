"""图片识别中公式常数的提取、清洗与多数决测试（不调用外部 API）。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from worker_ai import WorkerAI


def eye_data():
    return {
        "AL": 23.5,
        "K1": 43.5,
        "K1Axis": 10,
        "K2": 44.0,
        "K2Axis": 100,
        "ACD": 3.2,
    }


def extracted_data(**overrides):
    data = {
        "patient_name": "测试",
        "a_constant": 118.7,
        "haigis_constants": None,
        "hoffer_q_pacd": None,
        "right_eye": eye_data(),
        "left_eye": eye_data(),
    }
    data.update(overrides)
    return data


def test_clean_data_preserves_haigis_constants_and_hoffer_q_pacd():
    worker = WorkerAI(api_key="test")
    cleaned = worker._validate_and_clean_data(
        extracted_data(
            haigis_constants={"a0": "1.800", "a1": "0.400", "a2": "0.100"},
            hoffer_q_pacd="5.25 mm",
        )
    )

    assert cleaned["haigis_constants"] == {"a0": 1.8, "a1": 0.4, "a2": 0.1}
    assert cleaned["hoffer_q_pacd"] == 5.25


def test_clean_data_rejects_incomplete_haigis_constants():
    worker = WorkerAI(api_key="test")
    cleaned = worker._validate_and_clean_data(
        extracted_data(haigis_constants={"a0": 1.8, "a1": 0.4})
    )

    assert cleaned["haigis_constants"] is None
    assert cleaned["hoffer_q_pacd"] is None


def test_consensus_preserves_formula_constants_without_external_calls():
    worker = WorkerAI(api_key="test")
    data = extracted_data(
        haigis_constants={"a0": 1.8, "a1": 0.4, "a2": 0.1},
        hoffer_q_pacd=5.25,
    )
    result = worker._perform_consensus_analysis(
        [{"data": data.copy()} for _ in range(3)]
    )

    assert result["consensus_data"]["haigis_constants"] == {
        "a0": 1.8,
        "a1": 0.4,
        "a2": 0.1,
    }
    assert result["consensus_data"]["hoffer_q_pacd"] == 5.25


def test_disagreeing_formula_constants_do_not_affect_consensus():
    """表单没印 Haigis/pACD 或识别不一致时，不能拉低整体共识判定。"""
    worker = WorkerAI(api_key="test")
    data_a = extracted_data(
        haigis_constants={"a0": 1.8, "a1": 0.4, "a2": 0.1}, hoffer_q_pacd=5.25
    )
    data_b = extracted_data(
        haigis_constants={"a0": 1.9, "a1": 0.4, "a2": 0.1}, hoffer_q_pacd=6.10
    )
    data_c = extracted_data()

    result = worker._perform_consensus_analysis(
        [{"data": data_a}, {"data": data_b}, {"data": data_c}]
    )

    # 三次不一致 -> 留空，交给用户决定；但不进入 failed_fields
    assert result["consensus_data"]["haigis_constants"] is None
    assert result["consensus_data"]["hoffer_q_pacd"] is None
    assert "haigis_constants" not in result["details"]
    assert "hoffer_q_pacd" not in result["details"]
    assert result["consensus_reached"] is True


def test_missing_optional_constants_do_not_block_consensus():
    worker = WorkerAI(api_key="test")
    result = worker._perform_consensus_analysis(
        [{"data": extracted_data()} for _ in range(3)]
    )

    assert result["consensus_reached"] is True
    assert result["consensus_data"]["haigis_constants"] is None
    assert result["consensus_data"]["hoffer_q_pacd"] is None
