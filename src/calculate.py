import httpx
import re
import json
from urllib.parse import unquote
from bs4 import BeautifulSoup


def parse_iol_results(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    result = {}

    surgeon_info = soup.find("input", {"id": "MainContent_SurgeonID"})
    if surgeon_info:
        result["surgeon_info"] = surgeon_info.get("value", "")

    patient_info = soup.find("input", {"id": "MainContent_PatientID"})
    if patient_info:
        result["patient_info"] = patient_info.get("value", "")

    right_biometry = soup.find("input", {"id": "MainContent_Biomtery"})
    if right_biometry:
        result["right_eye"] = {"biometry": right_biometry.get("value", "")}

    right_prediction = soup.find("input", {"id": "MainContent_Prediction"})
    if right_prediction:
        result["right_eye"]["prediction"] = right_prediction.get("value", "")

    right_constants = soup.find("input", {"id": "MainContent_Constants"})
    if right_constants:
        result["right_eye"]["constants"] = right_constants.get("value", "")

    left_biometry = soup.find("input", {"id": "MainContent_Biometry0"})
    if left_biometry:
        result["left_eye"] = {"biometry": left_biometry.get("value", "")}

    left_prediction = soup.find("input", {"id": "MainContent_Prediction0"})
    if left_prediction:
        result["left_eye"]["prediction"] = left_prediction.get("value", "")

    left_constants = soup.find("input", {"id": "MainContent_Constants0"})
    if left_constants:
        result["left_eye"]["constants"] = left_constants.get("value", "")

    right_grid = soup.find("table", {"id": "MainContent_GridView1"})
    if right_grid:
        right_iol_data = []
        rows = right_grid.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                iol_power = cells[0].get_text(strip=True)
                optic = cells[1].get_text(strip=True)
                refraction = cells[2].get_text(strip=True)

                row_classes = row.get("class") or []
                is_recommended = "LightSteelBlue" in row_classes

                right_iol_data.append(
                    {
                        "iol_power": iol_power,
                        "optic": optic,
                        "refraction": refraction,
                        "recommended": is_recommended,
                    }
                )

        if "right_eye" not in result:
            result["right_eye"] = {}
        result["right_eye"]["iol_options"] = right_iol_data

    left_grid = soup.find("table", {"id": "MainContent_GridView2"})
    if left_grid:
        left_iol_data = []
        rows = left_grid.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                iol_power = cells[0].get_text(strip=True)
                optic = cells[1].get_text(strip=True)
                refraction = cells[2].get_text(strip=True)

                row_classes = row.get("class") or []
                is_recommended = "LightSteelBlue" in row_classes

                left_iol_data.append(
                    {
                        "iol_power": iol_power,
                        "optic": optic,
                        "refraction": refraction,
                        "recommended": is_recommended,
                    }
                )

        if "left_eye" not in result:
            result["left_eye"] = {}
        result["left_eye"]["iol_options"] = left_iol_data

    return result


async def calculate_iol(
    right_eye_params=None, left_eye_params=None, a_constant=119, patient_name=None
):
    if not right_eye_params and not left_eye_params:
        raise ValueError("至少需要提供右眼或左眼参数")

    if right_eye_params:
        if not all(key in right_eye_params for key in ["AL", "K1", "K2"]):
            raise ValueError("右眼缺少必须参数：AL, K1, K2")

    if left_eye_params:
        if not all(key in left_eye_params for key in ["AL", "K1", "K2"]):
            raise ValueError("左眼缺少必须参数：AL, K1, K2")

    def set_defaults(params):
        if params:
            params.setdefault("ACD", 3)
            params.setdefault("Refraction", 0)
            params.setdefault("LenThickness", "")
            params.setdefault("WTW", "")
        return params

    right_eye_params = set_defaults(right_eye_params)
    left_eye_params = set_defaults(left_eye_params)

    patient_name = patient_name if patient_name else "1"

    url = "https://calc.apacrs.org/barrett_universal2105/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        with httpx.Client(headers=headers, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            content = response.text

            viewstate_match = re.search(
                r'name=["\']__VIEWSTATE["\']\s+value=["\']([^"\']*)["\']',
                content,
                re.IGNORECASE,
            )
            viewstate = viewstate_match.group(1) if viewstate_match else ""

            viewstate_generator_match = re.search(
                r'name=["\']__VIEWSTATEGENERATOR["\']\s+value=["\']([^"\']*)["\']',
                content,
                re.IGNORECASE,
            )
            viewstate_generator = (
                viewstate_generator_match.group(1) if viewstate_generator_match else ""
            )

            event_validation_match = re.search(
                r'name=["\']__EVENTVALIDATION["\']\s+value=["\']([^"\']*)["\']',
                content,
                re.IGNORECASE,
            )
            event_validation = (
                event_validation_match.group(1) if event_validation_match else ""
            )

            if not viewstate:
                input_matches = re.findall(
                    r'<input[^>]*name=["\']__VIEWSTATE["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                    content,
                    re.IGNORECASE,
                )
                if input_matches:
                    viewstate = input_matches[0]

            if not viewstate_generator:
                input_matches = re.findall(
                    r'<input[^>]*name=["\']__VIEWSTATEGENERATOR["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                    content,
                    re.IGNORECASE,
                )
                if input_matches:
                    viewstate_generator = input_matches[0]

            if not event_validation:
                input_matches = re.findall(
                    r'<input[^>]*name=["\']__EVENTVALIDATION["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                    content,
                    re.IGNORECASE,
                )
                if input_matches:
                    event_validation = input_matches[0]

            post_data = {
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstate_generator,
                "__EVENTVALIDATION": event_validation,
                "ctl00$MainContent$RadioButtonList1": "337.5",
                "ctl00$MainContent$Button1": "Calculate",
                "ctl00$MainContent$DoctorName": "1",
                "ctl00$MainContent$PatientName": patient_name,
                "ctl00$MainContent$PatientNo": "",
                "ctl00$MainContent$LensFactor": "",
                "ctl00$MainContent$Aconstant": str(a_constant),
                "ctl00$MainContent$IOLModel": "Personal Constant",
                "ctl00$MainContent$Axlength": str(right_eye_params["AL"])
                if right_eye_params
                else "",
                "ctl00$MainContent$MeasuredK1": str(right_eye_params["K1"])
                if right_eye_params
                else "",
                "ctl00$MainContent$MeasuredK2": str(right_eye_params["K2"])
                if right_eye_params
                else "",
                "ctl00$MainContent$OpticalACD": str(right_eye_params["ACD"])
                if right_eye_params
                else "",
                "ctl00$MainContent$Refraction": str(right_eye_params["Refraction"])
                if right_eye_params
                else "",
                "ctl00$MainContent$LensThickness": str(right_eye_params["LenThickness"])
                if right_eye_params
                else "",
                "ctl00$MainContent$WTW": str(right_eye_params["WTW"])
                if right_eye_params
                else "",
                "ctl00$MainContent$Axlength0": str(left_eye_params["AL"])
                if left_eye_params
                else "",
                "ctl00$MainContent$MeasuredK10": str(left_eye_params["K1"])
                if left_eye_params
                else "",
                "ctl00$MainContent$MeasuredK20": str(left_eye_params["K2"])
                if left_eye_params
                else "",
                "ctl00$MainContent$OpticalACD0": str(left_eye_params["ACD"])
                if left_eye_params
                else "",
                "ctl00$MainContent$Refraction0": str(left_eye_params["Refraction"])
                if left_eye_params
                else "",
                "ctl00$MainContent$LensThickness0": str(left_eye_params["LenThickness"])
                if left_eye_params
                else "",
                "ctl00$MainContent$WTW0": str(left_eye_params["WTW"])
                if left_eye_params
                else "",
            }

            post_response = client.post(url, data=post_data)
            post_response.raise_for_status()
            post_content = post_response.text

            new_viewstate_match = re.search(
                r'<input[^>]*name=["\']__VIEWSTATE["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                post_content,
                re.IGNORECASE,
            )
            new_viewstate = new_viewstate_match.group(1) if new_viewstate_match else ""

            new_viewstate_generator_match = re.search(
                r'<input[^>]*name=["\']__VIEWSTATEGENERATOR["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                post_content,
                re.IGNORECASE,
            )
            new_viewstate_generator = (
                new_viewstate_generator_match.group(1)
                if new_viewstate_generator_match
                else ""
            )

            new_event_validation_match = re.search(
                r'<input[^>]*name=["\']__EVENTVALIDATION["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                post_content,
                re.IGNORECASE,
            )
            new_event_validation = (
                new_event_validation_match.group(1)
                if new_event_validation_match
                else ""
            )

            lens_factor_match = re.search(
                r'<input[^>]*name=["\']ctl00\$MainContent\$LensFactor["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                post_content,
                re.IGNORECASE,
            )
            lens_factor = lens_factor_match.group(1) if lens_factor_match else ""

            if not new_viewstate:
                input_matches = re.findall(
                    r'<input[^>]*name=["\']__VIEWSTATE["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                    post_content,
                    re.IGNORECASE,
                )
                if input_matches:
                    new_viewstate = input_matches[0]

            if not new_viewstate_generator:
                input_matches = re.findall(
                    r'<input[^>]*name=["\']__VIEWSTATEGENERATOR["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                    post_content,
                    re.IGNORECASE,
                )
                if input_matches:
                    new_viewstate_generator = input_matches[0]

            if not new_event_validation:
                input_matches = re.findall(
                    r'<input[^>]*name=["\']__EVENTVALIDATION["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
                    post_content,
                    re.IGNORECASE,
                )
                if input_matches:
                    new_event_validation = input_matches[0]

            third_post_data = {
                "__EVENTTARGET": "ctl00$MainContent$menuTabs",
                "__EVENTARGUMENT": "1",
                "__LASTFOCUS": "",
                "__VIEWSTATE": new_viewstate,
                "__VIEWSTATEGENERATOR": new_viewstate_generator,
                "__EVENTVALIDATION": new_event_validation,
                "ctl00$MainContent$DoctorName": "1",
                "ctl00$MainContent$PatientName": patient_name,
                "ctl00$MainContent$PatientNo": "",
                "ctl00$MainContent$LensFactor": lens_factor,
                "ctl00$MainContent$Aconstant": str(a_constant),
                "ctl00$MainContent$IOLModel": "Personal Constant",
                "ctl00$MainContent$Axlength": str(right_eye_params["AL"])
                if right_eye_params
                else "",
                "ctl00$MainContent$MeasuredK1": str(right_eye_params["K1"])
                if right_eye_params
                else "",
                "ctl00$MainContent$MeasuredK2": str(right_eye_params["K2"])
                if right_eye_params
                else "",
                "ctl00$MainContent$OpticalACD": str(right_eye_params["ACD"])
                if right_eye_params
                else "",
                "ctl00$MainContent$Refraction": str(right_eye_params["Refraction"])
                if right_eye_params
                else "",
                "ctl00$MainContent$LensThickness": str(right_eye_params["LenThickness"])
                if right_eye_params
                else "",
                "ctl00$MainContent$WTW": str(right_eye_params["WTW"])
                if right_eye_params
                else "",
                "ctl00$MainContent$Axlength0": str(left_eye_params["AL"])
                if left_eye_params
                else "",
                "ctl00$MainContent$MeasuredK10": str(left_eye_params["K1"])
                if left_eye_params
                else "",
                "ctl00$MainContent$MeasuredK20": str(left_eye_params["K2"])
                if left_eye_params
                else "",
                "ctl00$MainContent$OpticalACD0": str(left_eye_params["ACD"])
                if left_eye_params
                else "",
                "ctl00$MainContent$Refraction0": str(left_eye_params["Refraction"])
                if left_eye_params
                else "",
                "ctl00$MainContent$LensThickness0": str(left_eye_params["LenThickness"])
                if left_eye_params
                else "",
                "ctl00$MainContent$WTW0": str(left_eye_params["WTW"])
                if left_eye_params
                else "",
            }

            third_response = client.post(url, data=third_post_data)
            third_response.raise_for_status()

            parsed_result = parse_iol_results(third_response.text)

            return parsed_result

    except httpx.RequestError as e:
        raise Exception(f"请求错误: {e}")
    except Exception as e:
        raise Exception(f"其他错误: {e}")


def get_hello_message():
    return "Hello World!"
