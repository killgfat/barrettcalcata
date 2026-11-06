"""IOL晶体型号同步模块 - 从Barrett官方站点获取晶体型号及A常数

另外提供 ULIB 常数快照的本地查询入口，见 constants.py。
"""

import re
import time

import requests
from bs4 import BeautifulSoup

from . import constants as ulib_constants
from .config import DEFAULT_K_INDEX, to_barrett_k_index_value
from .data_model_map import BARRETT_TO_ULIB

# 内置 ULIB 快照只覆盖 ULIB 收录的型号，且 ULIB 已于 2016-10-31 停更。
# 查询顺序：先本地快照（零网络），未收录再走 Barrett 官网，官网失败时
# 放宽到 ULIB 的模糊匹配，并在结果里标记 source。
ULIB_SOURCE = "ulib"
BARRETT_SOURCE = "barrett"
# 官网清单取不到时回退到内置映射表，用这个值标明来源，便于调用方区分。
LOCAL_MAP_SOURCE = "barrett_local_map"


class IOLModelError(RuntimeError):
    """IOL 型号/常数查询失败。"""


BARRETT_CALCULATE_URL = "https://calc.apacrs.org/barrett_universal2105/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

_MODEL_LIST_TTL = 86400  # 24小时
_A_CONSTANT_TTL = 604800  # 7天

_model_list_cache = {"data": None, "ts": 0}
_a_constant_cache = {}
# 官网上一次失败的时刻。被 Cloudflare 拦截时每次重试都要等连接超时，
# 这里设一个冷却窗口，冷却期内直接用内置映射表，避免每个请求都卡住。
_model_list_failure = {"ts": 0, "error": None}
_FAILURE_COOLDOWN = 600  # 10 分钟


def _recent_failure(now):
    """返回冷却期内的失败信息，没有则返回 None。"""
    if _model_list_failure["error"] is None:
        return None
    if now - _model_list_failure["ts"] >= _FAILURE_COOLDOWN:
        return None
    return _model_list_failure["error"]


def _extract_hidden_fields(html):
    """从HTML中提取ASP.NET隐藏字段"""
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        match = re.search(
            rf'name=["\']{name}["\']\s+value=["\']([^"\']*)["\']',
            html,
            re.IGNORECASE,
        )
        if not match:
            match = re.search(
                rf'<input[^>]*name=["\']{name}["\'][^>]*'
                rf'value=["\']([^"\']*)["\'][^>]*>',
                html,
                re.IGNORECASE,
            )
        fields[name] = match.group(1) if match else ""
    return fields


def fetch_iol_model_list():
    """获取Barrett站点的IOL晶体型号列表（带缓存）"""
    now = time.time()
    if (
        _model_list_cache["data"] is not None
        and now - _model_list_cache["ts"] < _MODEL_LIST_TTL
    ):
        return _model_list_cache["data"]

    cooldown = _recent_failure(now)
    if cooldown is not None:
        raise IOLModelError(f"{cooldown}（冷却期内不再重试）")

    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        response = session.get(BARRETT_CALCULATE_URL, timeout=8)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        select = soup.find("select", {"id": "MainContent_IOLModel"})
        if not select:
            raise IOLModelError("无法找到IOL型号下拉列表")

        models = []
        for option in select.find_all("option"):
            name = option.get_text(strip=True)
            if name and name != "Personal Constant":
                models.append(name)
    except Exception as exc:  # 记录失败供后续请求降级
        _model_list_failure["ts"] = now
        _model_list_failure["error"] = str(exc)
        raise

    _model_list_failure["ts"] = 0
    _model_list_failure["error"] = None
    _model_list_cache["data"] = models
    _model_list_cache["ts"] = now
    return models


def fetch_model_constants(model_name):
    """按型号查询常数，优先使用手工映射与内置 ULIB 快照。

    查询顺序：
    1. Barrett 官网型号 → data_model_map.py 的手工映射 → ULIB 快照；
    2. ULIB 快照里的原始型号名（中国大陆/其他来源的输入可能是 ULIB 写法）；
    3. 回退到 Barrett 官网的 A 常数/Lens Factor 查询（可能发起网络请求）。

    第 3 步在官网被 Cloudflare 拦截时是高频失败点，调用方应能容忍异常。
    """
    mapped = ulib_constants.lookup_for_barrett_model(model_name)
    if mapped is not None:
        return mapped

    entry = ulib_constants.lookup(model_name)
    if entry is not None:
        return entry.to_model_result()

    result = fetch_model_a_constant(model_name)
    result["source"] = BARRETT_SOURCE
    result["source_revision"] = None
    result["ulib_name"] = None
    result["samples"] = None
    result["preliminary"] = False
    result["haigis_constants"] = None
    result["hoffer_q_pacd"] = None
    result["holladay1_sf"] = None
    result["srkt_a"] = None
    result["srk2_a"] = None
    result["nominal_a"] = result.get("a_constant")
    result["warnings"] = []
    return result


def _barrett_entry(model_name, mapped=None, note=""):
    """把一条 Barrett 型号整理成与 ULIB 列表同构的条目。

    ULIB 有对应条目时带上可计算常数；没有对应条目时只保留型号名，
    并把原因写进 note —— 前端据此禁用选中，而不是给用户一个假的常数。
    """
    if mapped is None:
        mapped = ulib_constants.lookup_for_barrett_model(model_name)
    base = {
        "name": model_name,
        "source": ULIB_SOURCE if mapped else BARRETT_SOURCE,
        "a_constant": None,
        "haigis": None,
        "pacd": None,
        "sf": None,
        "samples": None,
        "preliminary": False,
        "lens_factor": None,
        "ulib_name": None,
        "match": None,
        "note": "",
    }
    if mapped is None:
        base["note"] = note
        return base

    haigis = mapped.get("haigis_constants")
    base.update(
        {
            "a_constant": mapped.get("a_constant"),
            "haigis": list(haigis) if haigis else None,
            "pacd": mapped.get("hoffer_q_pacd"),
            "sf": mapped.get("holladay1_sf"),
            "samples": mapped.get("samples"),
            "preliminary": mapped.get("preliminary", False),
            "ulib_name": mapped.get("ulib_name"),
            "match": mapped.get("match"),
            "note": mapped.get("note") or "",
        }
    )
    return base


def list_iol_models(formula=None):
    """按公式返回可选晶体列表。

    Barrett 系列走官网型号清单（含 Lens Factor 语义），其余公式走内置
    ULIB 快照。官网不可达时退回本地的人工映射表 —— 那张表本身就是从
    官网清单整理来的，能保证下拉框至少有 18 个型号可选，不会因为外部
    站点拒绝请求而整体失败。

    返回 (条目列表, 附加信息 dict)。附加信息里的 source 标明列表主体来自
    哪里，warnings 记录降级原因。
    """
    normalized = resolve_model_formula(formula)
    if normalized == "castrop":
        # ULIB 快照停在 2016-10-31，Castrop 2021 年才发表，表里没有 C/H/R，
        # 也就没有可选的晶体条目。返回空列表 + 说明，避免前端拿一批
        # 查不到常数的型号名去误导用户。
        return [], {
            "formula": "castrop",
            "source": "none",
            "source_url": None,
            "source_revision": None,
            "warnings": [
                (
                    "Castrop 的 C/H/R 不在内置 ULIB 快照中，服务端不提供"
                    "型号列表；请用 castrop_constants 传入 C/H/R，"
                    "或直接用 castrop_elp 指定 ELP"
                )
            ],
            "constants_available": False,
        }

    if normalized != "barrett":
        models = ulib_constants.list_models()
        return models, {
            "formula": normalized,
            "source": ULIB_SOURCE,
            "source_url": ulib_constants.ULIB_SOURCE_URL,
            "source_revision": ulib_constants.ULIB_SOURCE_REVISION,
            "warnings": [],
            "constants_available": True,
        }

    # 本地映射表已经记录每个 Barrett 型号对应的 ULIB 条目和未映射原因，
    # 官网清单只是它的超集校验；先建好索引，两种来源都用同一套组装逻辑。
    local_notes = {row[0]: row[3] for row in BARRETT_TO_ULIB}
    warnings = []
    try:
        names = fetch_iol_model_list()
        source = BARRETT_SOURCE
    except Exception as exc:  # noqa: BLE001 - 外部站点失败要能降级
        names = [row[0] for row in BARRETT_TO_ULIB]
        source = LOCAL_MAP_SOURCE
        warnings.append(
            f"Barrett 官网型号列表不可用（{exc}），"
            f"改用内置映射表的 {len(names)} 个型号；"
            "映射表未覆盖的型号不会出现在列表中"
        )
    models = [
        _barrett_entry(name, note=local_notes.get(name, "")) for name in names
    ]
    return models, {
        "formula": "barrett",
        "source": source,
        "source_url": BARRETT_CALCULATE_URL,
        "source_revision": ulib_constants.ULIB_SOURCE_REVISION,
        "warnings": warnings,
    }


# 公式名与计算模型名的对照；两个入口都接受，避免调用方记两套名字。
FORMULA_NAMES = (
    "barrett",
    "srkt",
    "hoffer_q",
    "holladay1",
    "haigis",
    "castrop",
    "haigis-toric",
)
CALCULATION_MODELS = {
    "barrett_ii_offline": ("barrett", "offline"),
    "barrett_ii": ("barrett", "online"),
    "srkt": ("srkt", "offline"),
    "hoffer_q": ("hoffer_q", "offline"),
    "holladay1": ("holladay1", "offline"),
    "haigis": ("haigis", "offline"),
    "castrop": ("castrop", "offline"),
    "haigis-toric": ("haigis-toric", "offline"),
}


def resolve_model_formula(formula=None):
    """把 model 名或 formula 名统一成公式名。

    接受 `barrett`、`srkt`、`hoffer_q`、`holladay1`、`haigis`、
    `castrop`、`haigis-toric`，
    也接受 `barrett_ii` / `barrett_ii_offline` 这类计算模型名。空值或无法
    识别的值一律按 Barrett 处理：那是唯一一套依赖官网型号清单的公式，
    退回它的列表比报 400 更有用。
    """
    if formula is None:
        return "barrett"
    name = str(formula).strip().lower()
    if not name:
        return "barrett"
    if name in FORMULA_NAMES:
        return name
    mapped = CALCULATION_MODELS.get(name)
    return mapped[0] if mapped else "barrett"


def lookup_ulib_constants(model_name):
    """只查内置 ULIB 快照与型号映射；未收录返回 None，不发网络请求。"""
    mapped = ulib_constants.lookup_for_barrett_model(model_name)
    if mapped is not None:
        return mapped
    entry = ulib_constants.lookup(model_name)
    if entry is None:
        return None
    return entry.to_model_result()


def fetch_model_a_constant(model_name):
    """获取指定晶体型号的A常数和Lens Factor（带缓存）"""
    now = time.time()
    cached = _a_constant_cache.get(model_name)
    if cached and now - cached["ts"] < _A_CONSTANT_TTL:
        return {"a_constant": cached["a_constant"], "lens_factor": cached["lens_factor"]}

    session = requests.Session()
    session.headers.update(_HEADERS)

    response = session.get(BARRETT_CALCULATE_URL)
    response.raise_for_status()

    fields = _extract_hidden_fields(response.text)

    post_data = {
        "__EVENTTARGET": "ctl00$MainContent$IOLModel",
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": fields["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": fields["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": fields["__EVENTVALIDATION"],
        "ctl00$MainContent$IOLModel": model_name,
        "ctl00$MainContent$DoctorName": "",
        "ctl00$MainContent$PatientName": "",
        "ctl00$MainContent$PatientNo": "",
        "ctl00$MainContent$LensFactor": "",
        "ctl00$MainContent$Aconstant": "",
        "ctl00$MainContent$RadioButtonList1": to_barrett_k_index_value(
            DEFAULT_K_INDEX
        ),
        "ctl00$MainContent$Axlength": "",
        "ctl00$MainContent$MeasuredK1": "",
        "ctl00$MainContent$MeasuredK2": "",
        "ctl00$MainContent$OpticalACD": "",
        "ctl00$MainContent$Refraction": "0",
        "ctl00$MainContent$LensThickness": "",
        "ctl00$MainContent$WTW": "",
        "ctl00$MainContent$Axlength0": "",
        "ctl00$MainContent$MeasuredK10": "",
        "ctl00$MainContent$MeasuredK20": "",
        "ctl00$MainContent$OpticalACD0": "",
        "ctl00$MainContent$Refraction0": "0",
        "ctl00$MainContent$LensThickness0": "",
        "ctl00$MainContent$WTW0": "",
    }

    post_response = session.post(BARRETT_CALCULATE_URL, data=post_data)
    post_response.raise_for_status()

    soup = BeautifulSoup(post_response.text, "html.parser")

    a_input = soup.find("input", {"id": "MainContent_Aconstant"})
    lf_input = soup.find("input", {"id": "MainContent_LensFactor"})

    a_constant = None
    lens_factor = None

    if a_input:
        val = a_input.get("value", "").strip()
        if val:
            try:
                a_constant = round(float(val), 2)
            except ValueError:
                pass

    if lf_input:
        val = lf_input.get("value", "").strip()
        if val:
            try:
                lens_factor = round(float(val), 2)
            except ValueError:
                pass

    if a_constant is None:
        raise IOLModelError(f"无法获取 {model_name} 的A常数")

    _a_constant_cache[model_name] = {
        "a_constant": a_constant,
        "lens_factor": lens_factor,
        "ts": now,
    }

    return {"a_constant": a_constant, "lens_factor": lens_factor}
