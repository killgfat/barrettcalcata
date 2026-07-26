"""IOL晶体型号同步模块 - 从Barrett官方站点获取晶体型号及A常数"""

import re
import time

import requests
from bs4 import BeautifulSoup

BARRETT_URL = "https://calc.apacrs.org/barrett_universal2105/"

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

    session = requests.Session()
    session.headers.update(_HEADERS)
    response = session.get(BARRETT_URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    select = soup.find("select", {"id": "MainContent_IOLModel"})
    if not select:
        raise Exception("无法找到IOL型号下拉列表")

    models = []
    for option in select.find_all("option"):
        name = option.get_text(strip=True)
        if name and name != "Personal Constant":
            models.append(name)

    _model_list_cache["data"] = models
    _model_list_cache["ts"] = now
    return models


def fetch_model_a_constant(model_name):
    """获取指定晶体型号的A常数和Lens Factor（带缓存）"""
    now = time.time()
    cached = _a_constant_cache.get(model_name)
    if cached and now - cached["ts"] < _A_CONSTANT_TTL:
        return {"a_constant": cached["a_constant"], "lens_factor": cached["lens_factor"]}

    session = requests.Session()
    session.headers.update(_HEADERS)

    response = session.get(BARRETT_URL)
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
        "ctl00$MainContent$RadioButtonList1": "337.5",
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

    post_response = session.post(BARRETT_URL, data=post_data)
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
        raise Exception(f"无法获取 {model_name} 的A常数")

    _a_constant_cache[model_name] = {
        "a_constant": a_constant,
        "lens_factor": lens_factor,
        "ts": now,
    }

    return {"a_constant": a_constant, "lens_factor": lens_factor}
