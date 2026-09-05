"""Barrett Universal II Toric calculator integration.

The public Barrett Toric calculator is an ASP.NET Web Forms application.  The
ordinary Universal II calculator has a separate implementation in
``barrett_calculate.py``; this module deliberately keeps the toric request/response
flow isolated so changes to either upstream form do not leak into the other
calculator.
"""

from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from barrett_config import (
    DEFAULT_K_INDEX,
    normalize_k_index,
    to_barrett_k_index_value,
)

BARRETT_TORIC_URL = "https://calc.apacrs.org/toric_calculator20/Toric%20Calculator.aspx"
BARRETT_TORIC_IMAGE_URL = (
    "https://calc.apacrs.org/toric_calculator20/Resources/Eye%20Background%20360.jpg"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

_DEFAULT_ACD = 3.00
_DEFAULT_REFRACTION = 0.0
_DEFAULT_INCISION_SIA = 0.0
_DEFAULT_INCISION_LOCATION = 0.0
_DEFAULT_CYLINDER_MODE = "-ve"


def _first_present(params: dict[str, Any], names: tuple[str, ...]) -> Any:
    """Return the first non-empty value from a set of accepted aliases."""
    for name in names:
        value = params.get(name)
        if value is not None and (not isinstance(value, str) or value.strip()):
            return value
    return None


def _number(value: Any, default: float | None = None) -> float | None:
    """Convert a request value to a finite float, preserving missing values."""
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _required_number(
    value: Any,
    field_name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Validate a required finite number and an optional medical range."""
    parsed = _number(value)
    if parsed is None:
        raise ValueError(f"{field_name} 必须是有效数值")
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} 必须不小于 {minimum:g}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field_name} 必须不大于 {maximum:g}")
    return parsed


def _optional_number(
    value: Any,
    default: float,
    field_name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    """Normalize an optional numeric field and validate explicit values."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return _required_number(value, field_name, minimum, maximum)


def normalize_toric_eye_params(
    params: dict[str, Any] | None,
    eye_name: str = "眼部",
) -> dict[str, Any] | None:
    """Normalize one eye's Barrett Toric parameters.

    The API uses the same canonical names as the non-toric calculator:
    ``K1``, ``K1Axis``, ``K2`` and ``K2Axis``.  Descriptive ``flat_*`` /
    ``steep_*`` names remain accepted as backwards-compatible aliases.

    ``lens_thickness`` and ``WTW`` are required by the official Toric form;
    unlike the non-toric calculator they are not silently guessed.
    """
    if not params:
        return None
    if not isinstance(params, dict):
        raise TypeError(f"{eye_name}参数必须是JSON对象")

    flat_k = _required_number(
        _first_present(params, ("flat_k", "FlatK", "K1", "k1")),
        f"{eye_name}Flat K",
        30,
        60,
    )
    flat_axis = _required_number(
        _first_present(
            params,
            ("flat_axis", "FlatAxis", "K1Axis", "K1_axis", "flatKAxis"),
        ),
        f"{eye_name}Flat Axis",
        0,
        180,
    )
    steep_k = _required_number(
        _first_present(params, ("steep_k", "SteepK", "K2", "k2")),
        f"{eye_name}Steep K",
        30,
        60,
    )
    steep_axis = _required_number(
        _first_present(
            params,
            ("steep_axis", "SteepAxis", "K2Axis", "K2_axis", "steepKAxis"),
        ),
        f"{eye_name}Steep Axis",
        0,
        180,
    )
    axial_length = _required_number(
        _first_present(
            params,
            ("AL", "al", "axial_length", "AxialLength", "Axlength"),
        ),
        f"{eye_name}AL",
        12,
        38,
    )
    acd = _optional_number(
        _first_present(params, ("ACD", "acd", "OpticalACD")),
        _DEFAULT_ACD,
        f"{eye_name}ACD",
        0,
        6,
    )
    target_refraction = _optional_number(
        _first_present(
            params,
            ("target_refraction", "Refraction", "refraction", "TargetRefraction"),
        ),
        _DEFAULT_REFRACTION,
        f"{eye_name}目标屈光度",
    )
    incision_sia = _optional_number(
        _first_present(params, ("incision_sia", "IncisionSIA", "SIA", "sia")),
        _DEFAULT_INCISION_SIA,
        f"{eye_name}切口SIA",
        0,
        2,
    )
    incision_location = _optional_number(
        _first_present(
            params,
            (
                "incision_location",
                "IncisionLocation",
                "incision_axis",
                "IncisionAxis",
            ),
        ),
        _DEFAULT_INCISION_LOCATION,
        f"{eye_name}切口位置",
        0,
        360,
    )
    lens_thickness = _required_number(
        _first_present(
            params,
            ("lens_thickness", "LenThickness", "LensThickness", "LT"),
        ),
        f"{eye_name}晶体厚度",
        2,
        8,
    )
    wtw = _required_number(
        _first_present(params, ("WTW", "wtw", "white_to_white", "WhiteToWhite")),
        f"{eye_name}WTW",
        8,
        14,
    )

    # Keep the public shape aligned with the ordinary Barrett calculator.
    # Legacy flat/steep keys are retained so older clients do not break.
    return {
        "K1": flat_k,
        "K1Axis": flat_axis,
        "K2": steep_k,
        "K2Axis": steep_axis,
        "flat_k": flat_k,
        "flat_axis": flat_axis,
        "steep_k": steep_k,
        "steep_axis": steep_axis,
        "AL": axial_length,
        "ACD": round(acd, 2),
        "Refraction": target_refraction,
        "incision_sia": incision_sia,
        "incision_location": incision_location,
        "lens_thickness": lens_thickness,
        "WTW": wtw,
    }


def _format(value: Any, places: int = 2) -> str:
    """Format a numeric form value without scientific notation."""
    if value is None or value == "":
        return ""
    return f"{float(value):.{places}f}"


def _hidden_fields(html_content: str) -> dict[str, str]:
    """Extract ASP.NET Web Forms hidden fields with flexible attribute order."""
    soup = BeautifulSoup(html_content, "html.parser")
    fields: dict[str, str] = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        element = soup.find("input", attrs={"name": name})
        fields[name] = element.get("value", "") if element else ""
    return fields


def _successful_form_fields(html_content: str) -> dict[str, str]:
    """Extract controls that a browser would submit from the current form."""
    soup = BeautifulSoup(html_content, "html.parser")
    fields: dict[str, str] = {}
    for element in soup.find_all(["input", "select", "textarea"]):
        name = element.get("name")
        if not name or element.has_attr("disabled"):
            continue
        if element.name == "input":
            input_type = element.get("type", "text").lower()
            if input_type in {"button", "file", "image", "reset", "submit"}:
                continue
            if input_type in {"checkbox", "radio"} and not element.has_attr("checked"):
                continue
            # Text controls without a value attribute submit an empty string;
            # only checkbox/radio controls use the HTML default value "on".
            fields[name] = element.get(
                "value", "on" if input_type in {"checkbox", "radio"} else ""
            )
        elif element.name == "select":
            selected = element.find("option", selected=True) or element.find("option")
            fields[name] = (
                selected.get("value", selected.get_text()) if selected else ""
            )
        else:
            fields[name] = element.get_text()
    return fields


def _input_value(element: Any) -> str:
    """Read text/value from an HTML form element."""
    if element.name == "input":
        return element.get("value", "").strip()
    return element.get_text(" ", strip=True)


def _find_form_value(soup: BeautifulSoup, candidates: tuple[str, ...]) -> str | None:
    """Find a value by id/name, tolerating a changed ASP.NET prefix."""
    elements = soup.find_all(["input", "select", "textarea"])
    for candidate in candidates:
        for element in elements:
            if element.get("id", "").lower() == candidate.lower():
                value = _input_value(element)
                if value:
                    return value
            if element.get("name", "").lower() == candidate.lower():
                value = _input_value(element)
                if value:
                    return value
    return None


def _number_from_text(value: str | None) -> float | None:
    """Parse the first finite decimal number from result text."""
    if not value:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", ""))
    return _number(match.group(0)) if match else None


def _row_result(row: Any, headers: list[str]) -> dict[str, Any] | None:
    """Convert a likely toric result table row into a normalized option."""
    cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
    if not cells:
        return None
    text = " ".join(cells)
    if not re.search(r"\d", text):
        return None

    option: dict[str, Any] = {}
    for index, cell in enumerate(cells):
        header = headers[index].lower() if index < len(headers) else ""
        number = _number_from_text(cell)
        if any(token in header for token in ("toric", "cylinder", "cyl")):
            option["toric_power"] = cell
        elif "axis" in header:
            option["axis"] = number if number is not None else cell
        elif any(token in header for token in ("sphere", "power", "iol")):
            option.setdefault("iol_power", cell)
        elif any(token in header for token in ("refraction", "residual", "spherical")):
            option["refraction"] = cell

    if "iol_power" not in option:
        option["iol_power"] = cells[0]

    # Barrett tables frequently render the T-power and axis in one cell,
    # without useful column headers.  Preserve both values when present.
    toric_match = re.search(r"\bT\s*([0-9]+)\b", text, re.IGNORECASE)
    if "toric_power" not in option and toric_match:
        option["toric_power"] = f"T{toric_match.group(1)}"
    axis_match = re.search(
        r"(?:axis|@)\s*[:=]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if "axis" not in option and axis_match:
        option["axis"] = _number(axis_match.group(1))

    option.setdefault("refraction", "")
    option.setdefault("recommended", False)
    return option


def _parse_result_tables(soup: BeautifulSoup, eye_index: int) -> list[dict[str, Any]]:
    """Parse the official result grid and compatible table variants."""
    candidates = (
        f"MainContent_GridView{eye_index}",
        f"GridView{eye_index}",
        f"MainContent_ToricGridView{eye_index}",
    )
    tables = []
    for candidate in candidates:
        table = soup.find("table", attrs={"id": candidate})
        if table and table not in tables:
            tables.append(table)
    if not tables and eye_index == 1:
        tables = [
            table
            for table in soup.find_all("table")
            if re.search(
                r"(result|toric|prediction|grid)",
                " ".join(table.get("class", [])) + " " + table.get("id", ""),
                re.IGNORECASE,
            )
        ]

    options: list[dict[str, Any]] = []
    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [
            cell.get_text(" ", strip=True) for cell in rows[0].find_all(["th", "td"])
        ]
        for row in rows[1:]:
            parsed = _row_result(row, headers)
            if parsed:
                options.append(parsed)
    return options


def _axis_value(soup: BeautifulSoup, names: tuple[str, ...]) -> float | None:
    """Find a numeric axis result in an element or nearby result text."""
    value = _find_form_value(soup, names)
    parsed = _number_from_text(value)
    if parsed is not None:
        return parsed
    for name in names:
        element = soup.find(id=re.compile(re.escape(name), re.IGNORECASE))
        if element:
            parsed = _number_from_text(element.get_text(" ", strip=True))
            if parsed is not None:
                return parsed
    return None


def _net_astigmatism_axis(soup: BeautifulSoup) -> float | None:
    """Extract the recommended toric axis from the official net-astigmatism field."""
    value = _find_form_value(soup, ("MainContent_NetCornealAstig",))
    if not value:
        return None
    match = re.search(r"@\s*(\d+(?:\.\d+)?)", value)
    return _number(match.group(1)) if match else None


def parse_toric_results(
    html_content: str, selected_eye: str | None = None
) -> dict[str, Any]:
    """Parse Barrett Toric output into the API's stable result shape."""
    soup = BeautifulSoup(html_content, "html.parser")
    result: dict[str, Any] = {}

    for key, candidates in {
        "surgeon_info": ("MainContent_SurgeonID", "MainContent_DoctorName"),
        "patient_info": ("MainContent_PatientID", "MainContent_PatientName"),
    }.items():
        value = _find_form_value(soup, candidates)
        if value is not None:
            result[key] = value

    eye_specs = {
        "right_eye": {
            "suffix": "",
            "index": 1,
            "K1": ("MainContent_K1", "MainContent_FlatK", "MainContent_MeasuredK1"),
            "K1Axis": ("MainContent_K1Axis", "MainContent_FlatAxis"),
            "K2": (
                "MainContent_K2",
                "MainContent_SteepK",
                "MainContent_MeasuredK2",
            ),
            "K2Axis": ("MainContent_K2Axis", "MainContent_SteepAxis"),
            "AL": ("MainContent_AxialLength", "MainContent_Axlength"),
            "ACD": ("MainContent_OpticalACD",),
            "axis": (
                "MainContent_ToricAxis",
                "MainContent_IOLAxis",
                "MainContent_ResultAxis",
                "MainContent_Axis",
            ),
        },
        "left_eye": {
            "suffix": "0",
            "index": 2,
            "K1": (
                "MainContent_K10",
                "MainContent_FlatK0",
                "MainContent_MeasuredK10",
            ),
            "K1Axis": ("MainContent_K1Axis0", "MainContent_FlatAxis0"),
            "K2": (
                "MainContent_K20",
                "MainContent_SteepK0",
                "MainContent_MeasuredK20",
            ),
            "K2Axis": ("MainContent_K2Axis0", "MainContent_SteepAxis0"),
            "AL": ("MainContent_AxialLength0", "MainContent_Axlength0"),
            "ACD": ("MainContent_OpticalACD0",),
            "axis": (
                "MainContent_ToricAxis0",
                "MainContent_IOLAxis0",
                "MainContent_ResultAxis0",
                "MainContent_Axis0",
            ),
        },
    }

    if selected_eye in {"right_eye", "left_eye"}:
        # 当前官方页面使用同一组字段，通过 Rad1/Rad2 切换眼别。
        current_spec = {
            "suffix": "",
            "index": 1,
            "K1": (
                "MainContent_MeasuredK",
                "MainContent_FlatK",
                "MainContent_K1",
            ),
            "K1Axis": (
                "MainContent_MeasuredAxis",
                "MainContent_FlatAxis",
                "MainContent_K1Axis",
            ),
            "K2": (
                "MainContent_MeasuredK0",
                "MainContent_SteepK",
                "MainContent_K2",
            ),
            "K2Axis": (
                "MainContent_MeasuredAxis0",
                "MainContent_SteepAxis",
                "MainContent_K2Axis",
            ),
            "AL": (
                "MainContent_AxLength",
                "MainContent_AxialLength",
                "MainContent_Axlength",
            ),
            "ACD": ("MainContent_OpticalACD",),
            "axis": (
                "MainContent_ToricAxis",
                "MainContent_IOLAxis",
                "MainContent_ResultAxis",
                "MainContent_Axis",
            ),
        }
        eye_specs = {selected_eye: current_spec}

    for eye_name, spec in eye_specs.items():
        options = _parse_result_tables(soup, spec["index"])
        toric_options = (
            _parse_result_tables(soup, 2)
            if selected_eye in {"right_eye", "left_eye"}
            else []
        )
        eye_result: dict[str, Any] = {}
        axis = _net_astigmatism_axis(soup) or _axis_value(soup, spec["axis"])
        if options:
            eye_result["iol_options"] = options
            axis_values = [
                option.get("axis")
                for option in options
                if option.get("axis") is not None
            ]
            if axis is None and axis_values:
                axis = axis_values[0]
        if toric_options:
            eye_result["toric_options"] = toric_options
            if axis is None:
                axis_values = [
                    option.get("axis")
                    for option in toric_options
                    if option.get("axis") is not None
                ]
                if axis_values:
                    axis = axis_values[0]
        for field in ("K1", "K1Axis", "K2", "K2Axis", "AL", "ACD"):
            value = _find_form_value(soup, spec[field])
            if value is not None:
                eye_result[field] = _number_from_text(value)
        # Legacy result aliases for callers that used the first Toric API.
        if "K1" in eye_result:
            eye_result["flat_k"] = eye_result["K1"]
        if "K1Axis" in eye_result:
            eye_result["flat_axis"] = eye_result["K1Axis"]
        if "K2" in eye_result:
            eye_result["steep_k"] = eye_result["K2"]
        if "K2Axis" in eye_result:
            eye_result["steep_axis"] = eye_result["K2Axis"]
        # Historical parser output used lowercase ``al``/``acd`` keys.
        if "AL" in eye_result:
            eye_result["al"] = eye_result["AL"]
        if "ACD" in eye_result:
            eye_result["acd"] = eye_result["ACD"]
        if axis is not None:
            eye_result["toric_axis"] = axis
        if eye_result:
            result[eye_name] = eye_result

    return result


def build_axis_image_metadata(
    eye_params: dict[str, Any],
    eye_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build metadata used by the Web UI to overlay axes on Barrett's image."""
    eye_result = eye_result or {}
    options = eye_result.get("iol_options") or []
    toric_axis = eye_result.get("toric_axis")
    if toric_axis is None and options:
        toric_axis = options[0].get("axis")
    fallback_svg = _build_axis_fallback_svg(
        flat_axis=eye_params.get("K1Axis", eye_params.get("flat_axis")),
        steep_axis=eye_params.get("K2Axis", eye_params.get("steep_axis")),
        toric_axis=toric_axis,
        incision_location=eye_params.get("incision_location"),
    )
    return {
        "source_url": BARRETT_TORIC_IMAGE_URL,
        "fallback_url": "data:image/svg+xml;charset=utf-8,"
        + quote(fallback_svg, safe=""),
        "alt": "Barrett Toric Calculator 眼轴位图",
        "K1Axis": eye_params.get("K1Axis", eye_params.get("flat_axis")),
        "K2Axis": eye_params.get("K2Axis", eye_params.get("steep_axis")),
        "flat_axis": eye_params.get("K1Axis", eye_params.get("flat_axis")),
        "steep_axis": eye_params.get("K2Axis", eye_params.get("steep_axis")),
        "toric_axis": toric_axis,
        "incision_location": eye_params.get("incision_location"),
    }


def _build_axis_fallback_svg(
    *,
    flat_axis: Any,
    steep_axis: Any,
    toric_axis: Any,
    incision_location: Any,
) -> str:
    """Create a self-contained fallback when the official image is blocked."""
    lines = []
    for angle, color, width in (
        (flat_axis, "#2563eb", 3),
        (steep_axis, "#ea580c", 3),
        (toric_axis, "#16a34a", 5),
        (incision_location, "#7c3aed", 2),
    ):
        if angle is None:
            continue
        try:
            normalized = float(angle)
        except (TypeError, ValueError):
            continue
        lines.append(
            f'<line x1="32" y1="180" x2="328" y2="180" '
            f'stroke="{color}" stroke-width="{width}" '
            f'transform="rotate({normalized:g} 180 180)" />'
        )
    ticks = []
    for angle in range(0, 360, 30):
        ticks.append(
            f'<line x1="180" y1="12" x2="180" y2="24" '
            f'stroke="#64748b" stroke-width="1" '
            f'transform="rotate({angle} 180 180)" />'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 360">'
        '<rect width="360" height="360" fill="#f0fdfa"/>'
        '<circle cx="180" cy="180" r="164" fill="#ecfeff" '
        'stroke="#0f766e" stroke-width="2"/>'
        '<circle cx="180" cy="180" r="132" fill="none" '
        'stroke="#99f6e4" stroke-width="1"/>'
        + "".join(ticks)
        + "".join(lines)
        + '<circle cx="180" cy="180" r="4" fill="#0f172a"/>'
        '<text x="180" y="348" text-anchor="middle" '
        'font-family="Arial,sans-serif" font-size="14" fill="#334155">Barrett Toric axis</text>'
        "</svg>"
    )


def _build_current_official_eye_payload(
    payload: dict[str, str], eye_params: dict[str, Any]
) -> None:
    """Populate the field names used by the current Toric Calculator V2 page."""
    fields = {
        "K1": "MeasuredK", "K1Axis": "MeasuredAxis",
        "K2": "MeasuredK0", "K2Axis": "MeasuredAxis0",
        "AL": "AxLength", "ACD": "OpticalACD",
        "Refraction": "Refraction", "incision_sia": "InducedCyl",
        "incision_location": "IncisionAxis", "lens_thickness": "LensThickness",
        "WTW": "WTW",
    }
    for field, official_name in fields.items():
        value = eye_params.get(field)
        if value is None:
            value = {
                "K1": eye_params.get("flat_k"),
                "K1Axis": eye_params.get("flat_axis"),
                "K2": eye_params.get("steep_k"),
                "K2Axis": eye_params.get("steep_axis"),
            }.get(field)
        payload[f"ctl00$MainContent${official_name}"] = _format(value)


def _calculate_payload(
    form_fields: dict[str, str],
    right_eye_params: dict[str, Any] | None,
    left_eye_params: dict[str, Any] | None,
    *,
    a_constant: float,
    patient_name: str,
    iol_model: str,
    k_index: float,
    cylinder_mode: str,
    eye_select: str = "Rad1",
    event_target: str = "",
    event_argument: str = "",
) -> dict[str, str]:
    """Construct the ASP.NET payload for calculation or result-tab requests."""
    payload = dict(form_fields)
    payload.update({
        "__EVENTTARGET": event_target,
        "__EVENTARGUMENT": event_argument,
        "__LASTFOCUS": "",
        "ctl00$MainContent$Koptional1": "",
        "ctl00$MainContent$Koptional2": "",
        "ctl00$MainContent$IOLPower": "",
        "ctl00$MainContent$DoctorName": "",
        "ctl00$MainContent$PatientName": patient_name,
        "ctl00$MainContent$PatientNo": "",
        "ctl00$MainContent$Aconstant": _format(a_constant),
        "ctl00$MainContent$IOLModel": iol_model,
        "ctl00$MainContent$Eye Select": eye_select,
        # Although the inputs are rendered disabled, the official page's
        # client-side form submission includes these selected radio values.
        "ctl00$MainContent$RadioButtonList1": to_barrett_k_index_value(k_index),
        "ctl00$MainContent$RadioButtonList2": {
            "+ve": "1", "+": "1", "-ve": "-1", "-": "-1"
        }.get(cylinder_mode, cylinder_mode),
    })
    if not payload.get("ctl00$MainContent$LensFactor", "").strip():
        payload["ctl00$MainContent$LensFactor"] = " 2.04"
    if event_target:
        payload.pop("ctl00$MainContent$Button1", None)
    else:
        payload["ctl00$MainContent$Button1"] = "Calculate"
    selected_params = right_eye_params if eye_select == "Rad1" else left_eye_params
    _build_current_official_eye_payload(payload, selected_params or {})
    return payload


def _eye_selection_payload(
    form_fields: dict[str, str], eye_select: str
) -> dict[str, str]:
    """Build the radio-button postback used to activate an eye on the page."""
    payload = dict(form_fields)
    payload.update(
        {
            "__EVENTTARGET": f"ctl00$MainContent${eye_select}",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
            "ctl00$MainContent$Eye Select": eye_select,
        }
    )
    payload.pop("ctl00$MainContent$Button1", None)
    return payload


def _request(session: requests.Session, method: str, url: str, **kwargs: Any) -> Any:
    """Call a requests session with a bounded timeout and test-friendly fallback."""
    try:
        return getattr(session, method)(url, timeout=30, **kwargs)
    except TypeError:
        # Lightweight fake sessions in unit tests often omit timeout support.
        return getattr(session, method)(url, **kwargs)


def _persist_response_cookies(
    session: requests.Session, response: Any
) -> None:
    """Persist upstream cookies for runtimes with a limited Session jar."""
    cookies = getattr(response, "cookies", None)
    if cookies is None:
        return
    try:
        for cookie in cookies:
            session.cookies.set(
                cookie.name,
                cookie.value,
                domain=getattr(cookie, "domain", None),
                path=getattr(cookie, "path", None),
            )
    except (AttributeError, TypeError):
        # Native requests already manages its cookie jar; this is only a
        # compatibility guard for the Workers Python HTTP implementation.
        return


async def calculate_barrett_toric_iol(
    right_eye_params: dict[str, Any] | None = None,
    left_eye_params: dict[str, Any] | None = None,
    a_constant: float = 119.30,
    patient_name: str | None = None,
    iol_model: str | None = None,
    k_index: float = DEFAULT_K_INDEX,
    cylinder_mode: str = _DEFAULT_CYLINDER_MODE,
) -> dict[str, Any]:
    """Calculate Barrett Universal II Toric power and alignment.

    The function intentionally mirrors :func:`barrett_calculate.calculate_barrett_iol` while
    using the separate Toric calculator URL and its meridian-specific fields.
    """
    if not right_eye_params and not left_eye_params:
        raise ValueError("至少需要提供右眼或左眼散光参数")

    right_eye_params = normalize_toric_eye_params(right_eye_params, "右眼")
    left_eye_params = normalize_toric_eye_params(left_eye_params, "左眼")
    normalized_a = _required_number(a_constant, "a_constant", 112, 125)
    normalized_k = normalize_k_index(k_index)
    patient = str(patient_name).strip() if patient_name else "1"
    model = (
        iol_model
        if iol_model and iol_model != "Personal Constant"
        else "Personal Constant"
    )
    mode = str(cylinder_mode or _DEFAULT_CYLINDER_MODE).strip()
    if mode not in {"+ve", "-ve", "+", "-"}:
        raise ValueError("cylinder_mode 只支持 +ve 或 -ve")

    session = requests.Session()
    session.headers.update(_HEADERS)
    session.headers.update(
        {
            "Referer": BARRETT_TORIC_URL,
            "Origin": "https://calc.apacrs.org",
        }
    )
    try:
        response = _request(session, "get", BARRETT_TORIC_URL)
        response.raise_for_status()
        _persist_response_cookies(session, response)
        if "Just a moment" in response.text or "cf-chl" in response.text:
            raise RuntimeError("Barrett Toric 官方页面当前需要完成 Cloudflare 验证")
        form_fields = _successful_form_fields(response.text)

        parsed: dict[str, Any] = {}
        current_form_fields = form_fields
        multiple_eyes = bool(right_eye_params and left_eye_params)
        for eye_name, eye_params, eye_select in (
            ("right_eye", right_eye_params, "Rad1"),
            ("left_eye", left_eye_params, "Rad2"),
        ):
            if not eye_params:
                continue
            # The current page requires an eye-selection postback before the
            # calculate event.  This establishes the per-eye server state and
            # refreshes ASP.NET's hidden validation fields.
            if current_form_fields.get("ctl00$MainContent$Eye Select") != eye_select:
                selection_response = _request(
                    session,
                    "post",
                    BARRETT_TORIC_URL,
                    data=_eye_selection_payload(current_form_fields, eye_select),
                )
                selection_response.raise_for_status()
                _persist_response_cookies(session, selection_response)
                current_form_fields = _successful_form_fields(selection_response.text)
            payload = _calculate_payload(
                current_form_fields,
                eye_params if eye_select == "Rad1" else None,
                eye_params if eye_select == "Rad2" else None,
                a_constant=normalized_a,
                patient_name=patient,
                iol_model=model,
                k_index=normalized_k,
                cylinder_mode=mode,
                eye_select=eye_select,
            )
            calculation_response = _request(
                session, "post", BARRETT_TORIC_URL, data=payload
            )
            calculation_response.raise_for_status()
            _persist_response_cookies(session, calculation_response)
            current_form_fields = _successful_form_fields(calculation_response.text)
            eye_result = parse_toric_results(
                calculation_response.text, selected_eye=eye_name
            )

            # Results are rendered on the Toric IOL tab after calculation.
            has_output = any(
                eye.get("iol_options") or eye.get("toric_options")
                for eye in (eye_result.get(eye_name, {}),)
            )
            if not has_output and not multiple_eyes:
                tab_payload = _calculate_payload(
                    current_form_fields,
                    eye_params if eye_select == "Rad1" else None,
                    eye_params if eye_select == "Rad2" else None,
                    a_constant=normalized_a,
                    patient_name=patient,
                    iol_model=model,
                    k_index=normalized_k,
                    cylinder_mode=mode,
                    eye_select=eye_select,
                    event_target="ctl00$MainContent$menuTabs",
                    event_argument="2",
                )
                tab_response = _request(
                    session, "post", BARRETT_TORIC_URL, data=tab_payload
                )
                tab_response.raise_for_status()
                _persist_response_cookies(session, tab_response)
                current_form_fields = _successful_form_fields(tab_response.text)
                eye_result = parse_toric_results(
                    tab_response.text, selected_eye=eye_name
                )
            if eye_name in eye_result:
                parsed[eye_name] = eye_result[eye_name]

        # With both eyes present, the official workflow calculates each eye
        # first and only then opens the Toric IOL tab.  Loading that tab between
        # calculations causes the ASP.NET page state to reject the next eye.
        if multiple_eyes:
            for eye_name, eye_params, eye_select in (
                ("right_eye", right_eye_params, "Rad1"),
                ("left_eye", left_eye_params, "Rad2"),
            ):
                if not eye_params:
                    continue
                if (
                    current_form_fields.get("ctl00$MainContent$Eye Select")
                    != eye_select
                ):
                    selection_response = _request(
                        session,
                        "post",
                        BARRETT_TORIC_URL,
                        data=_eye_selection_payload(
                            current_form_fields, eye_select
                        ),
                    )
                    selection_response.raise_for_status()
                    _persist_response_cookies(session, selection_response)
                    current_form_fields = _successful_form_fields(
                        selection_response.text
                    )
                tab_response = _request(
                    session,
                    "post",
                    BARRETT_TORIC_URL,
                    data=_calculate_payload(
                        current_form_fields,
                        eye_params if eye_select == "Rad1" else None,
                        eye_params if eye_select == "Rad2" else None,
                        a_constant=normalized_a,
                        patient_name=patient,
                        iol_model=model,
                        k_index=normalized_k,
                        cylinder_mode=mode,
                        eye_select=eye_select,
                        event_target="ctl00$MainContent$menuTabs",
                        event_argument="2",
                    ),
                )
                tab_response.raise_for_status()
                _persist_response_cookies(session, tab_response)
                tab_result = parse_toric_results(
                    tab_response.text, selected_eye=eye_name
                )
                if eye_name in tab_result:
                    parsed.setdefault(eye_name, {}).update(tab_result[eye_name])
                current_form_fields = _successful_form_fields(tab_response.text)

        for eye_name, eye_params in (
            ("right_eye", right_eye_params),
            ("left_eye", left_eye_params),
        ):
            if eye_params:
                eye_result = parsed.setdefault(eye_name, {})
                eye_result["axis_image"] = build_axis_image_metadata(
                    eye_params, eye_result
                )

        parsed["formula"] = "Barrett Universal II Toric"
        parsed["source_url"] = BARRETT_TORIC_URL
        parsed["cylinder_mode"] = mode
        return parsed
    except requests.exceptions.HTTPError as exc:
        if getattr(exc.response, "status_code", None) in {403, 429}:
            raise RuntimeError(
                "Barrett Toric 官方计算器暂时拒绝了自动请求（可能需要浏览器验证），"
                "请稍后重试"
            ) from exc
        response = getattr(exc, "response", None)
        detail = ""
        if response is not None:
            try:
                detail = (response.text or "").strip()[:240]
            except Exception:
                detail = ""
        suffix = f" ({detail})" if detail else ""
        raise RuntimeError(f"请求 Barrett Toric 官方计算器失败: {exc}{suffix}") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"请求 Barrett Toric 官方计算器失败: {exc}") from exc
