"""按公式返回候选晶体列表的契约测试。

/api/iol-models 同时承担两件事：
- 带 formula 时返回该公式的候选型号列表（Barrett 走官网/映射表，其余走 ULIB）
- 带 model 时返回单个型号的常数
"""

import asyncio
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from api import APIHandler
from formula import list_iol_models
from formula.data_model_map import BARRETT_TO_ULIB


def call(**kwargs):
    """直接调用 handler，绕过 HTTP 层。"""
    handler = APIHandler(env=None)
    request = types.SimpleNamespace(method="GET")
    return asyncio.run(handler.handle_barrett_iol_models(request, **kwargs))


def test_barrett_formula_returns_official_model_count():
    """Barrett 返回 18 个官网型号；官网不可达时用内置映射表兜底。"""
    models, info = list_iol_models("barrett")
    assert info["formula"] == "barrett"
    assert len(models) == len(BARRETT_TO_ULIB) == 18
    names = [m["name"] for m in models]
    assert "Alcon SN60WF" in names
    assert "AMO ZCB00" in names


def test_barrett_list_falls_back_instead_of_failing():
    """官网 403 时列表仍然可用，并在 warnings 与 source 里说明降级。"""
    models, info = list_iol_models("barrett")
    assert len(models) == 18
    if info["source"] == "barrett_local_map":
        assert info["warnings"], "降级必须留下说明"
        assert "官网" in info["warnings"][0]
    else:
        assert info["source"] == "barrett"


def test_non_barrett_formula_uses_ulib_snapshot():
    """其余公式返回完整 ULIB 快照，零网络请求。"""
    for formula in ("srkt", "hoffer_q", "haigis", "haigis-toric"):
        models, info = list_iol_models(formula)
        assert info["formula"] == formula
        assert info["source"] == "ulib"
        assert info["source_revision"] == "2016-10-31"
        assert len(models) == 304
        assert info["warnings"] == []


def test_calculation_model_names_are_accepted():
    """也接受 barrett_ii / barrett_ii_offline 这类计算模型名。"""
    for name in ("barrett_ii", "barrett_ii_offline"):
        models, info = list_iol_models(name)
        assert info["formula"] == "barrett"
        assert len(models) == 18


def test_missing_or_unknown_formula_defaults_to_barrett():
    """不传或传了不认识的值时按 Barrett 处理，不报错。"""
    for value in (None, "", "not-a-formula"):
        models, info = list_iol_models(value)
        assert info["formula"] == "barrett"
        assert len(models) == 18


def test_barrett_entries_carry_constants_and_unmapped_reason():
    """映射到的型号带可计算常数；未映射的给出原因而不是假常数。"""
    models, _ = list_iol_models("barrett")
    by_name = {m["name"]: m for m in models}

    zcb00 = by_name["AMO ZCB00"]
    assert zcb00["a_constant"] == 119.3
    assert zcb00["haigis"] == [-1.302, 0.21, 0.251]
    assert zcb00["pacd"] == 5.8
    assert zcb00["ulib_name"] == "AMO Tecnis 1 ZCB00"
    assert zcb00["match"] == "exact"

    # 未映射的型号不能凭空给出常数，必须带上原因。
    for name, ulib_name, _match, note in BARRETT_TO_ULIB:
        if ulib_name is None:
            entry = by_name[name]
            assert entry["a_constant"] is None, name
            assert entry["haigis"] is None, name
            assert entry["note"] == note, name


def test_barrett_entries_share_shape_with_ulib_entries():
    """两种来源的条目字段一致，前端可以用同一套渲染逻辑。"""
    barrett_models, _ = list_iol_models("barrett")
    ulib_models, _ = list_iol_models("srkt")
    common_keys = {"name", "a_constant", "haigis", "pacd", "samples", "preliminary"}
    for entry in barrett_models:
        assert common_keys <= set(entry)
    for entry in ulib_models:
        assert common_keys <= set(entry)


def test_endpoint_returns_list_for_formula():
    """端点带上 formula 时返回列表并标注来源。"""
    body, status = call(formula="haigis")
    assert status == 200
    assert body["success"] is True
    assert body["data"]["formula"] == "haigis"
    assert body["data"]["source"] == "ulib"
    assert len(body["data"]["models"]) == 304


def test_endpoint_still_supports_single_model_lookup():
    """单型号查询保持原样，不受 formula 参数影响。"""
    body, status = call(model_name="AMO ZCB00")
    assert status == 200
    data = body["data"]
    assert data["name"] == "AMO ZCB00"
    assert data["a_constant"] == 119.3
    assert data["source"] == "ulib"


def test_endpoint_rejects_non_get():
    """只支持 GET。"""
    handler = APIHandler(env=None)
    request = types.SimpleNamespace(method="POST")
    _, status = asyncio.run(
        handler.handle_barrett_iol_models(request, formula="haigis")
    )
    assert status == 405
