"""ULIB 晶体列表端点与前端选择器的数据契约测试。"""

import asyncio
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from api import APIHandler
from formula import list_ulib_model_details


def call_endpoint(method="GET"):
    handler = APIHandler(env=None)
    request = types.SimpleNamespace(method=method)
    return asyncio.run(handler.handle_ulib_models(request))


def test_endpoint_returns_all_models():
    """端点返回全部 304 款晶体，并带上来源信息。"""
    body, status = call_endpoint()
    assert status == 200
    assert body["success"] is True
    data = body["data"]
    assert len(data["models"]) == 304
    assert data["source"] == "ulib"
    assert data["source_revision"] == "2016-10-31"


def test_endpoint_rejects_non_get():
    """只支持 GET。"""
    body, status = call_endpoint("POST")
    assert status == 405
    assert "error" in body


def test_each_model_carries_computable_constants():
    """每项都要带上计算所需的常数，前端选中后可直接填入。"""
    models = list_ulib_model_details()
    assert len(models) == 304
    for model in models:
        assert isinstance(model["name"], str) and model["name"]
        assert set(model) == {
            "name",
            "a_constant",
            "haigis",
            "pacd",
            "samples",
            "preliminary",
        }
        # Haigis 三常数要么齐全、要么整体为空。
        assert model["haigis"] is None or len(model["haigis"]) == 3


def test_a_constant_prefers_optimized_srkt_value():
    """a_constant 取优化后的 SRK/T A，而不是名义 A。"""
    models = {m["name"]: m for m in list_ulib_model_details()}
    zcb00 = models["AMO Tecnis 1 ZCB00"]
    assert zcb00["a_constant"] == 119.3
    assert zcb00["haigis"] == [-1.302, 0.21, 0.251]
    assert zcb00["pacd"] == 5.8


def test_models_are_sorted_by_name():
    """列表按名称排序，便于前端展示与定位。"""
    names = [m["name"].lower() for m in list_ulib_model_details()]
    assert names == sorted(names)


def test_keyword_filter_works_like_frontend():
    """前端按关键词过滤的行为可用同一份数据复现。"""
    models = list_ulib_model_details()

    def search(keyword):
        terms = [t for t in keyword.lower().split() if t]
        return [m for m in models if all(t in m["name"].lower() for t in terms)]

    assert len(search("tecnis")) == 10
    assert any(m["name"] == "AMO Tecnis 1 ZCB00" for m in search("tecnis"))
    assert any(m["name"] == "AMO Tecnis 1 ZCB00" for m in search("tecnis zcb00"))
    assert search("zzz-not-a-lens") == []
    # 空关键词返回全部。
    assert len(search("")) == 304


def test_payload_size_stays_reasonable():
    """列表体积要控制住，避免每次切公式都传大响应。"""
    import json

    payload = json.dumps(
        list_ulib_model_details(), ensure_ascii=False, separators=(",", ":")
    )
    assert len(payload.encode()) < 60 * 1024
