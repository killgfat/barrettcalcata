import re

import requests
from bs4 import BeautifulSoup


def parse_iol_results(html_content):
    """
    解析IOL计算结果的HTML内容，提取关键数据

    参数:
    html_content: HTML内容字符串

    返回:
    包含解析结果的字典
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = {}

    # 提取患者信息
    surgeon_info = soup.find("input", {"id": "MainContent_SurgeonID"})
    if surgeon_info:
        result["surgeon_info"] = surgeon_info.get("value", "")

    patient_info = soup.find("input", {"id": "MainContent_PatientID"})
    if patient_info:
        result["patient_info"] = patient_info.get("value", "")

    # 提取右眼数据
    right_biometry = soup.find("input", {"id": "MainContent_Biomtery"})
    if right_biometry:
        result["right_eye"] = {"biometry": right_biometry.get("value", "")}

    right_prediction = soup.find("input", {"id": "MainContent_Prediction"})
    if right_prediction:
        result["right_eye"]["prediction"] = right_prediction.get("value", "")

    right_constants = soup.find("input", {"id": "MainContent_Constants"})
    if right_constants:
        result["right_eye"]["constants"] = right_constants.get("value", "")

    # 提取左眼数据
    left_biometry = soup.find("input", {"id": "MainContent_Biometry0"})
    if left_biometry:
        result["left_eye"] = {"biometry": left_biometry.get("value", "")}

    left_prediction = soup.find("input", {"id": "MainContent_Prediction0"})
    if left_prediction:
        result["left_eye"]["prediction"] = left_prediction.get("value", "")

    left_constants = soup.find("input", {"id": "MainContent_Constants0"})
    if left_constants:
        result["left_eye"]["constants"] = left_constants.get("value", "")

    # 提取右眼IOL表格数据
    right_grid = soup.find("table", {"id": "MainContent_GridView1"})
    if right_grid:
        right_iol_data = []
        rows = right_grid.find_all("tr")[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                iol_power = cells[0].get_text(strip=True)
                optic = cells[1].get_text(strip=True)
                refraction = cells[2].get_text(strip=True)

                # 检查是否为推荐行（高亮显示）
                is_recommended = "LightSteelBlue" in row.get("class", [])

                right_iol_data.append(
                    {
                        "iol_power": iol_power,
                        "optic": optic,
                        "refraction": refraction,
                        "recommended": is_recommended,
                    }
                )

        result["right_eye"]["iol_options"] = right_iol_data

    # 提取左眼IOL表格数据
    left_grid = soup.find("table", {"id": "MainContent_GridView2"})
    if left_grid:
        left_iol_data = []
        rows = left_grid.find_all("tr")[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                iol_power = cells[0].get_text(strip=True)
                optic = cells[1].get_text(strip=True)
                refraction = cells[2].get_text(strip=True)

                # 检查是否为推荐行（高亮显示）
                is_recommended = "LightSteelBlue" in row.get("class", [])

                left_iol_data.append(
                    {
                        "iol_power": iol_power,
                        "optic": optic,
                        "refraction": refraction,
                        "recommended": is_recommended,
                    }
                )

        result["left_eye"]["iol_options"] = left_iol_data

    return result


async def calculate_iol(
    right_eye_params=None, left_eye_params=None, a_constant=119.30, patient_name=None
):
    """
    计算IOL度数

    参数:
    right_eye_params: 右眼参数字典，包含AL, K1, K2, ACD, Refraction, LenThickness, WTW
    left_eye_params: 左眼参数字典，包含AL, K1, K2, ACD, Refraction, LenThickness, WTW
    a_constant: A常数，默认119.30
    patient_name: 患者姓名，如果没有提供则使用默认值"1"

    返回:
    计算结果字典
    """

    # 验证必须参数
    if not right_eye_params and not left_eye_params:
        raise ValueError("至少需要提供右眼或左眼参数")

    def normalize_optional_number(value, default=None, decimal_places=None):
        if value is None:
            return default

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default

        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return default

        if decimal_places is not None:
            normalized = round(normalized, decimal_places)

        return normalized

    def format_decimal_for_request(value, decimal_places=2):
        if value is None:
            return ""
        return f"{float(value):.{decimal_places}f}"

    def normalize_eye_params(params, eye_name):
        if not params:
            return None

        normalized = dict(params)
        required_params = ["AL", "K1", "K2"]
        missing_params = []

        for field in required_params:
            normalized[field] = normalize_optional_number(normalized.get(field), None)
            if normalized[field] is None:
                missing_params.append(field)

        if missing_params:
            raise ValueError(f"{eye_name}缺少必须参数：{', '.join(missing_params)}")

        normalized["ACD"] = normalize_optional_number(
            normalized.get("ACD"), 3.00, decimal_places=2
        )
        normalized["Refraction"] = normalize_optional_number(
            normalized.get("Refraction"), 0.0
        )
        normalized["LenThickness"] = (
            ""
            if normalized.get("LenThickness") is None
            else str(normalized.get("LenThickness")).strip()
        )
        normalized["WTW"] = (
            "" if normalized.get("WTW") is None else str(normalized.get("WTW")).strip()
        )

        return normalized

    right_eye_params = normalize_eye_params(right_eye_params, "右眼")
    left_eye_params = normalize_eye_params(left_eye_params, "左眼")
    a_constant = normalize_optional_number(a_constant, 119.30, decimal_places=2)

    # 设置患者姓名，如果没有提供则使用默认值"1"
    patient_name = patient_name if patient_name else "1"

    url = "https://calc.apacrs.org/barrett_universal2105/"

    # 创建一个会话对象来管理cookie
    session = requests.Session()

    # 设置请求头，模拟浏览器行为
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    session.headers.update(headers)

    # 第一步：发送GET请求获取__VIEWSTATE, __EVENTVALIDATION, __VIEWSTATEGENERATOR和cookie
    try:
        response = session.get(url)
        response.raise_for_status()

        # 从HTML中提取隐藏字段的值
        content = response.text

        # 使用更灵活的正则表达式提取__VIEWSTATE
        viewstate_match = re.search(
            r'name=["\']__VIEWSTATE["\']\s+value=["\']([^"\']*)["\']',
            content,
            re.IGNORECASE,
        )
        viewstate = viewstate_match.group(1) if viewstate_match else ""

        # 提取__VIEWSTATEGENERATOR
        viewstate_generator_match = re.search(
            r'name=["\']__VIEWSTATEGENERATOR["\']\s+value=["\']([^"\']*)["\']',
            content,
            re.IGNORECASE,
        )
        viewstate_generator = (
            viewstate_generator_match.group(1) if viewstate_generator_match else ""
        )

        # 提取__EVENTVALIDATION
        event_validation_match = re.search(
            r'name=["\']__EVENTVALIDATION["\']\s+value=["\']([^"\']*)["\']',
            content,
            re.IGNORECASE,
        )
        event_validation = (
            event_validation_match.group(1) if event_validation_match else ""
        )

        # 如果仍然没有找到，尝试其他方法
        if not viewstate:
            # 尝试查找所有input标签
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

        # 构建POST请求的数据
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
            "ctl00$MainContent$Aconstant": format_decimal_for_request(a_constant),
            "ctl00$MainContent$IOLModel": "Personal Constant",
            # 右眼参数（无后缀）
            "ctl00$MainContent$Axlength": str(right_eye_params["AL"])
            if right_eye_params
            else "",
            "ctl00$MainContent$MeasuredK1": str(right_eye_params["K1"])
            if right_eye_params
            else "",
            "ctl00$MainContent$MeasuredK2": str(right_eye_params["K2"])
            if right_eye_params
            else "",
            "ctl00$MainContent$OpticalACD": format_decimal_for_request(
                right_eye_params["ACD"]
            )
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
            # 左眼参数（带0后缀）
            "ctl00$MainContent$Axlength0": str(left_eye_params["AL"])
            if left_eye_params
            else "",
            "ctl00$MainContent$MeasuredK10": str(left_eye_params["K1"])
            if left_eye_params
            else "",
            "ctl00$MainContent$MeasuredK20": str(left_eye_params["K2"])
            if left_eye_params
            else "",
            "ctl00$MainContent$OpticalACD0": format_decimal_for_request(
                left_eye_params["ACD"]
            )
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

        # 第二步：发送POST请求
        post_response = session.post(url, data=post_data)
        post_response.raise_for_status()

        # 第三步：从第二次POST响应中提取新的验证参数和LensFactor
        post_content = post_response.text

        # 提取新的__VIEWSTATE - 使用更精确的正则表达式
        new_viewstate_match = re.search(
            r'<input[^>]*name=["\']__VIEWSTATE["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
            post_content,
            re.IGNORECASE,
        )
        new_viewstate = new_viewstate_match.group(1) if new_viewstate_match else ""

        # 提取新的__VIEWSTATEGENERATOR
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

        # 提取新的__EVENTVALIDATION
        new_event_validation_match = re.search(
            r'<input[^>]*name=["\']__EVENTVALIDATION["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
            post_content,
            re.IGNORECASE,
        )
        new_event_validation = (
            new_event_validation_match.group(1) if new_event_validation_match else ""
        )

        # 提取LensFactor值 - 更精确的正则表达式
        lens_factor_match = re.search(
            r'<input[^>]*name=["\']ctl00\$MainContent\$LensFactor["\'][^>]*value=["\']([^"\']*)["\'][^>]*>',
            post_content,
            re.IGNORECASE,
        )
        lens_factor = lens_factor_match.group(1) if lens_factor_match else ""

        # 如果没有找到，尝试其他方法
        if not new_viewstate:
            # 尝试查找所有input标签
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

        # 构建第三次POST请求的数据（切换到Universal Formula标签页）
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
            "ctl00$MainContent$Aconstant": format_decimal_for_request(a_constant),
            "ctl00$MainContent$IOLModel": "Personal Constant",
            # 右眼参数（无后缀）
            "ctl00$MainContent$Axlength": str(right_eye_params["AL"])
            if right_eye_params
            else "",
            "ctl00$MainContent$MeasuredK1": str(right_eye_params["K1"])
            if right_eye_params
            else "",
            "ctl00$MainContent$MeasuredK2": str(right_eye_params["K2"])
            if right_eye_params
            else "",
            "ctl00$MainContent$OpticalACD": format_decimal_for_request(
                right_eye_params["ACD"]
            )
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
            # 左眼参数（带0后缀）
            "ctl00$MainContent$Axlength0": str(left_eye_params["AL"])
            if left_eye_params
            else "",
            "ctl00$MainContent$MeasuredK10": str(left_eye_params["K1"])
            if left_eye_params
            else "",
            "ctl00$MainContent$MeasuredK20": str(left_eye_params["K2"])
            if left_eye_params
            else "",
            "ctl00$MainContent$OpticalACD0": format_decimal_for_request(
                left_eye_params["ACD"]
            )
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

        # 第三次：发送POST请求切换标签页
        third_response = session.post(url, data=third_post_data)
        third_response.raise_for_status()

        # 解析HTML内容并提取关键数据
        parsed_result = parse_iol_results(third_response.text)

        return parsed_result

    except requests.exceptions.RequestException as e:
        raise Exception(f"请求错误: {e}")
    except Exception as e:
        raise Exception(f"其他错误: {e}")


def get_hello_message():
    return "Hello World!"
