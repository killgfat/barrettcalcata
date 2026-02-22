import base64
import json
import re
import asyncio
import httpx
from typing import Optional, Dict, Any


class WorkerAI:
    def __init__(
        self,
        api_base_url: str = "https://api.openai.com/v1",
        api_key: str = None,
        model: str = "gpt-4-vision-preview",
        config_params: dict = None,
    ):
        """
        初始化 WorkerAI，使用 OpenAI 兼容的 API

        参数:
          - api_base_url: OpenAI 兼容 API 的 Base URL（包含 /v1 但不包含 /chat/completions）
          - api_key: API 密钥
          - model: 使用的模型名称
          - config_params: 配置参数字典，包含数值范围限制等
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else None,
        }
        # 移除None值的header
        self.headers = {k: v for k, v in self.headers.items() if v is not None}

        # 设置默认配置参数
        self.config_params = config_params or {}

        # 初始化默认数值范围（与webui.py保持一致）
        self.default_limits = {
            "al_min": 12.0,  # 眼轴长度最小值 (mm)
            "al_max": 38.0,  # 眼轴长度最大值 (mm)
            "al_normal_min": 20.0,  # 正常范围最小值
            "al_normal_max": 30.0,  # 正常范围最大值
            "k_min": 30.0,  # 角膜曲率最小值 (D)
            "k_max": 60.0,  # 角膜曲率最大值 (D)
            "k_normal_min": 35.0,  # 正常范围最小值
            "k_normal_max": 50.0,  # 正常范围最大值
            "acd_min": 0.0,  # 前房深度最小值 (mm)
            "acd_max": 6.0,  # 前房深度最大值 (mm)
            "acd_normal_min": 2.0,  # 正常范围最小值
            "acd_normal_max": 4.5,  # 正常范围最大值
            "a_const_min": 110.0,  # A常数最小值
            "a_const_max": 125.0,  # A常数最大值
            "a_const_common_min": 115.0,  # 常见范围最小值
            "a_const_common_max": 122.0,  # 常见范围最大值
        }

        # 如果提供了配置参数，覆盖默认值
        if self.config_params:
            for key, value in self.config_params.items():
                if key in self.default_limits:
                    self.default_limits[key] = float(value)

    async def extract_iol_data_from_image(
        self, image_base64: str, ai_client=None, status_callback=None
    ):
        """
        使用 OpenAI 兼容的API从 IOL master 晶体单图片中提取数据。
        连续进行3次识别，然后对三次输出的json中的数值逐项比对，
        采用有两个以上相同的结果，生成最后的json。
        如果存在3次结果均不相同，在webui中弹出"识别数据存在错误，请手动校验"。

        参数:
          - image_base64: base64 编码（不带 data:image 前缀）的图片数据
          - ai_client: 保留参数以保持兼容性，但不再使用
          - status_callback: 状态回调函数，用于更新前端状态

        返回:
          - dict: { success: bool, data: … / error: …, raw_response: …, consensus_reached: bool?, attempts: int }
        """
        extraction_count = 3
        extraction_results = []

        def update_status(message):
            """更新状态信息"""
            print(f"=== {message} ===")
            if status_callback:
                status_callback(message)

        try:
            update_status("WorkerAI开始处理图片")
            print(f"输入图片base64长度: {len(image_base64)}")

            update_status("开始并发执行3次识别")

            # 创建三个并发任务
            tasks = []
            for extract_num in range(1, extraction_count + 1):
                task = self._extract_data_from_image_once(
                    image_base64, extract_num, extraction_count
                )
                tasks.append(task)

            # 并发执行所有任务
            gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理每个任务的结果
            for extract_num, extract_result in enumerate(gathered_results, 1):
                if isinstance(extract_result, Exception):
                    update_status(f"第{extract_num}次识别失败: {str(extract_result)}")
                    extraction_results.append(
                        {
                            "attempt": extract_num,
                            "success": False,
                            "error": str(extract_result),
                        }
                    )
                elif not extract_result["success"]:
                    update_status(
                        f"第{extract_num}次识别失败: {extract_result.get('error', '未知错误')}"
                    )
                    extraction_results.append(
                        {
                            "attempt": extract_num,
                            "success": False,
                            "error": extract_result.get("error", "未知错误"),
                        }
                    )
                else:
                    update_status(f"第{extract_num}次识别成功")
                    extraction_results.append(
                        {
                            "attempt": extract_num,
                            "success": True,
                            "data": extract_result["data"],
                            "raw_response": extract_result["raw_response"],
                        }
                    )

            # 检查是否有成功的识别结果
            successful_extractions = [r for r in extraction_results if r["success"]]
            if len(successful_extractions) < 2:
                update_status("成功识别次数不足2次，无法进行多数决比对")
                return {
                    "success": False,
                    "error": f"成功识别次数不足2次（仅{len(successful_extractions)}次成功），无法进行多数决比对",
                    "attempts": extraction_results,
                }

            update_status("开始进行多数决比对")
            consensus_result = self._perform_consensus_analysis(successful_extractions)

            if consensus_result["consensus_reached"]:
                update_status("多数决比对成功，生成最终结果")
                return {
                    "success": True,
                    "data": consensus_result["consensus_data"],
                    "consensus_reached": True,
                    "consensus_details": consensus_result["details"],
                    "attempts": extraction_results,
                    "total_extractions": extraction_count,
                }
            else:
                update_status("多数决比对失败，三次结果均不相同")
                return {
                    "success": False,
                    "error": "识别数据存在错误，请手动校验",
                    "consensus_reached": False,
                    "consensus_details": consensus_result["details"],
                    "attempts": extraction_results,
                    "total_extractions": extraction_count,
                    "requires_manual_verification": True,
                }

        except Exception as e:
            update_status(f"处理过程中发生异常: {str(e)}")
            print(f"WorkerAI处理图片时发生异常: {str(e)}")
            import traceback

            print(f"异常堆栈: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"图片分析失败: {e}",
                "attempts": extraction_results,
            }

    async def _extract_data_from_image_once(
        self, image_base64: str, extract_num: int = 1, total_count: int = 3
    ):
        """
        执行一次图片数据提取

        参数:
          - image_base64: base64编码的图片数据
          - extract_num: 当前是第几次提取（1-based）
          - total_count: 总共要进行多少次提取
        """
        try:
            # 构造 prompt（文本部分）单独作为字符串
            prompt = (
                f"=== 第{extract_num}/{total_count}次提取 ===\\n"
                "1. 【系统指令】你是一位专业的眼科医疗数据提取专家，专门从 IOL master 晶体单测量报告图片中提取数据。\\n"
                "2. 【任务描述】请仔细分析这张 IOL master 晶体单图片，准确提取以下数据：\\n"
                "   - 患者姓名\\n"
                "   - A常数（A constant）\\n"
                "   - 右眼（OD）的AL（眼轴长度）、K1、K2（角膜曲率）、ACD（前房深度）\\n"
                "   - 左眼（OS）的AL、K1、K2、ACD\\n"
                "3. 【自我验证步骤】在生成最终结果前，请回答以下自我质询问题：\\n"
                "   a) 我是否确认了左右眼标签的位置？有没有可能将左右眼数据颠倒？\\n"
                "   b) 我是否检查了每个数值对应的标签（AL对应眼轴，K1对应角膜曲率等）？\\n"
                "   c) 提取的数值是否在合理范围内？（参考下面的数值范围）\\n"
                "   d) 是否存在明显的OCR识别错误或数字误读？\\n"
                "   e) 表单中是否有多个相似数值，我是否正确匹配了对应字段？\\n"
                "\\n"
                "4. 【置信度评估】对每个字段给出信心评分（1-5分，5为最高）：\\n"
                "   - 患者姓名：文字清晰度如何？是否容易识别？\\n"
                "   - 数值数据：数字清晰度如何？是否有模糊或遮挡？\\n"
                "   - 标签匹配：数值和标签的对应关系是否明确？\\n"
                "\\n"
                "=== 常见错位识别问题及避免方法 ===\\n"
                "常见错误1: 左右眼数据颠倒 - 仔细核对 'OD'(右眼) 和 'OS'(左眼) 标签\\n"
                "常见错误2: AL、K1、K2、ACD 数值错配 - 确保数值与正确的测量项目对应\\n"
                "常见错误3: 单位混淆 - AL 是 mm，K1/K2 是 D，注意不要混淆\\n"
                "常见错误4: 小数点位置错误 - 注意小数点位置，如 23.45 不是 2345\\n"
                "常见错误5: ACD数值读取错误- 仪器不一定测得出ACD的数值，不要识别成Cyl的数值\\n"
                "\\n"
                "=== 输出格式要求 ===\\n"
                "请严格按照以下 JSON 格式返回，如果某个字段找不到就设为 null：\\n"
                "{\\n"
                '  "patient_name": "患者姓名或null",\\n'
                '  "a_constant": 数值或null,\\n'
                '  "right_eye": {\\n'
                '    "AL": 数值或null,\\n'
                '    "K1": 数值或null,\\n'
                '    "K2": 数值或null,\\n'
                '    "ACD": 数值或null\\n'
                "  },\\n"
                '  "left_eye": {\\n'
                '    "AL": 数值或null,\\n'
                '    "K1": 数值或null,\\n'
                '    "K2": 数值或null,\\n'
                '    "ACD": 数值或null\\n'
                "  },\\n"
                '  "self_verification": {\\n'
                '    "confidence_scores": {\\n'
                '      "patient_name": 1-5,\\n'
                '      "a_constant": 1-5,\\n'
                '      "right_eye": {\\n'
                '        "AL": 1-5,\\n'
                '        "K1": 1-5,\\n'
                '        "K2": 1-5,\\n'
                '        "ACD": 1-5\\n'
                "      },\\n"
                '      "left_eye": {\\n'
                '        "AL": 1-5,\\n'
                '        "K1": 1-5,\\n'
                '        "K2": 1-5,\\n'
                '        "ACD": 1-5\\n'
                "      }\\n"
                "    },\\n"
                '    "potential_issues": ["描述任何潜在问题或不确定的地方"],\\n'
                '    "verification_notes": "自我验证的总结说明"\\n'
                "  }\\n"
                "}\\n\\n"
                "=== 数值范围限制（请严格遵循） ===\\n"
                "- 眼轴长度 AL: 15.00-35.00mm（正常范围20.00-30.00mm）\\n"
                "- 角膜曲率 K1, K2: 30.00-65.00D（正常范围35.00-50.00D）\\n"
                "- 前房深度 ACD: 1.00-6.00mm（正常范围2.00-4.50mm）\\n"
                "- A常数: 110.00-125.00（常见范围115.00-122.00）\\n\\n"
                "=== 重要要求 ===\\n"
                "- 只返回 JSON，不要其他文字\\n"
                "- 所有数值（AL、K1、K2、ACD、a_constant）必须保留2位小数，如23.45、43.21等\\n"
                "- 数值请提取原始数字，不要单位\\n"
                "- 如果左右眼数据都存在，请分别提取\\n"
                "- 如果只有单眼数据，另一眼设为 null\\n"
                "- 请确保数值精度：即使原始数据是整数，也要写成2位小数格式（如23写成23.00）\\n"
                "- 如果提取的数值超出上述合理范围，请仔细检查图片，确保识别准确\\n"
                "- 对于明显异常的数值，请以图片实际显示为准，不要强行修正\\n"
                "- 在 self_verification 中诚实评估置信度，低置信度（≤2）的字段需要特别说明\\n"
                "\\n"
                "=== 最终检查 ===\\n"
                "在返回结果前，最后确认：\\n"
                "1. JSON 格式是否正确且完整？\\n"
                "2. 所有数值是否都有正确的小数点格式？\\n"
                "3. 是否避免了常见的左右眼混淆错误？\\n"
                "4. 是否在合理范围内标记了异常值？\\n"
            )

            # 构造 image_url payload：把 base64 字符串作为纯字符串传给 API
            image_data_uri = f"data:image/jpeg;base64,{image_base64}"
            print(f"构造的图片URI长度: {len(image_data_uri)}")

            print("开始调用AI模型...")

            # 构造OpenAI兼容的请求payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_data_uri}},
                        ],
                    }
                ],
                "max_tokens": 1024,
                "temperature": 0.5,
            }

            # 发送异步请求到OpenAI兼容API
            print("开始调用AI模型...")

            # 使用 httpx 发送异步请求
            timeout = httpx.Timeout(60.0, connect=60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                # 检查响应状态
                response.raise_for_status()

                print("AI模型调用完成")

                # 解析 AI 响应
                response_data = response.json()

            # 提取响应文本
            if "choices" in response_data and len(response_data["choices"]) > 0:
                response_text = response_data["choices"][0]["message"][
                    "content"
                ].strip()
            else:
                raise ValueError("API响应格式不正确：缺少choices字段")

            # 有时候 LLM 会返回 ```json ... ``` 格式，把可能的 Markdown code block 去掉
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            try:
                extracted = json.loads(response_text)
            except json.JSONDecodeError:
                # JSON 解析失败，使用 fallback 文本提取
                return await self._fallback_text_extraction(image_base64, response_text)

            cleaned = self._validate_and_clean_data(extracted)

            # 输出LLM返回的原始结果
            print("=== LLM识别完成，返回结果 ===")
            print(f"原始响应: {response_text}")
            print(
                f"解析后的JSON: {json.dumps(extracted, ensure_ascii=False, indent=2)}"
            )
            print(f"清洗后的数据: {json.dumps(cleaned, ensure_ascii=False, indent=2)}")
            print("=== 识别结果输出完成 ===")

            return {"success": True, "data": cleaned, "raw_response": response_text}

        except httpx.HTTPError as e:
            error_msg = f"API请求失败: {e}"
            print(f"WorkerAI处理图片时发生网络异常: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
            }
        except Exception as e:
            print(f"WorkerAI处理图片时发生异常: {str(e)}")
            import traceback

            print(f"异常堆栈: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"图片分析失败: {e}",
            }

    def _perform_consensus_analysis(self, extraction_results):
        """
        对多次识别结果进行多数决分析

        参数:
          - extraction_results: 成功的识别结果列表

        返回:
          - dict: { consensus_reached: bool, consensus_data: dict, details: dict }
        """
        try:
            # 提取所有数值数据进行比对
            data_points = []
            for result in extraction_results:
                data_points.append(result["data"])

            print(f"=== 开始多数决分析，共{len(data_points)}个结果 ===")
            for i, data in enumerate(data_points):
                print(f"结果{i + 1}: {json.dumps(data, ensure_ascii=False, indent=2)}")

            def format_to_two_decimal(value):
                """将数值格式化为2位小数"""
                if value is None:
                    return None
                try:
                    return round(float(value), 2)
                except (ValueError, TypeError):
                    return None

            # 执行多数决分析
            consensus_data = {
                "patient_name": self._get_consensus_value(
                    [d.get("patient_name") for d in data_points], is_string=True
                ),
                "a_constant": format_to_two_decimal(
                    self._get_consensus_value(
                        [d.get("a_constant") for d in data_points]
                    )
                ),
                "right_eye": {
                    "AL": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("right_eye", {}).get("AL") for d in data_points]
                        )
                    ),
                    "K1": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("right_eye", {}).get("K1") for d in data_points]
                        )
                    ),
                    "K2": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("right_eye", {}).get("K2") for d in data_points]
                        )
                    ),
                    "ACD": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("right_eye", {}).get("ACD") for d in data_points]
                        )
                    ),
                },
                "left_eye": {
                    "AL": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("left_eye", {}).get("AL") for d in data_points]
                        )
                    ),
                    "K1": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("left_eye", {}).get("K1") for d in data_points]
                        )
                    ),
                    "K2": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("left_eye", {}).get("K2") for d in data_points]
                        )
                    ),
                    "ACD": format_to_two_decimal(
                        self._get_consensus_value(
                            [d.get("left_eye", {}).get("ACD") for d in data_points]
                        )
                    ),
                },
            }

            # 统计达成共识的字段数量
            total_fields = 0
            consensus_fields = 0
            details = {}

            # 检查各个字段的共识情况
            fields_to_check = [
                ("patient_name", [d.get("patient_name") for d in data_points], True),
                ("a_constant", [d.get("a_constant") for d in data_points], False),
                (
                    "right_eye.AL",
                    [d.get("right_eye", {}).get("AL") for d in data_points],
                    False,
                ),
                (
                    "right_eye.K1",
                    [d.get("right_eye", {}).get("K1") for d in data_points],
                    False,
                ),
                (
                    "right_eye.K2",
                    [d.get("right_eye", {}).get("K2") for d in data_points],
                    False,
                ),
                (
                    "right_eye.ACD",
                    [d.get("right_eye", {}).get("ACD") for d in data_points],
                    False,
                ),
                (
                    "left_eye.AL",
                    [d.get("left_eye", {}).get("AL") for d in data_points],
                    False,
                ),
                (
                    "left_eye.K1",
                    [d.get("left_eye", {}).get("K1") for d in data_points],
                    False,
                ),
                (
                    "left_eye.K2",
                    [d.get("left_eye", {}).get("K2") for d in data_points],
                    False,
                ),
                (
                    "left_eye.ACD",
                    [d.get("left_eye", {}).get("ACD") for d in data_points],
                    False,
                ),
            ]

            for field_name, values, is_string in fields_to_check:
                total_fields += 1
                consensus_value = self._get_consensus_value(values, is_string)
                consensus_info = self._analyze_consensus(values, consensus_value)
                details[field_name] = consensus_info

                if consensus_info["has_consensus"]:
                    consensus_fields += 1

            # 判断是否达成足够的共识（至少2/3的字段达成共识）
            consensus_threshold = total_fields * 2 / 3
            consensus_reached = consensus_fields >= consensus_threshold

            print(f"=== 多数决分析完成 ===")
            print(f"总字段数: {total_fields}, 达成共识字段数: {consensus_fields}")
            print(f"共识阈值: {consensus_threshold:.1f}, 达成共识: {consensus_reached}")
            print(
                f"最终结果: {json.dumps(consensus_data, ensure_ascii=False, indent=2)}"
            )

            return {
                "consensus_reached": consensus_reached,
                "consensus_data": consensus_data,
                "details": details,
                "total_fields": total_fields,
                "consensus_fields": consensus_fields,
                "consensus_threshold": consensus_threshold,
            }

        except Exception as e:
            print(f"多数决分析时发生异常: {str(e)}")
            import traceback

            print(f"异常堆栈: {traceback.format_exc()}")
            return {
                "consensus_reached": False,
                "consensus_data": None,
                "details": {"error": str(e)},
            }

    def _get_consensus_value(self, values, is_string=False, tolerance=0.1):
        """
        获取多数决值

        参数:
          - values: 值列表
          - is_string: 是否为字符串类型
          - tolerance: 数值类型的容差范围

        返回:
          - 达成共识的值，如果没有共识则返回None
        """
        # 过滤掉None值
        valid_values = [v for v in values if v is not None]
        if len(valid_values) < 2:
            return valid_values[0] if len(valid_values) == 1 else None

        if is_string:
            # 字符串类型：完全匹配
            from collections import Counter

            counter = Counter(valid_values)
            most_common = counter.most_common(1)
            if most_common and most_common[0][1] >= 2:
                return most_common[0][0]
            return None
        else:
            # 数值类型：在容差范围内匹配
            for i, value1 in enumerate(valid_values):
                matching_count = 1
                for j, value2 in enumerate(valid_values):
                    if i != j and abs(value1 - value2) <= tolerance:
                        matching_count += 1
                if matching_count >= 2:
                    # 返回匹配值的平均值
                    matching_values = [
                        v for v in valid_values if abs(v - value1) <= tolerance
                    ]
                    return sum(matching_values) / len(matching_values)
            return None

    def _analyze_consensus(self, values, consensus_value):
        """
        分析共识情况

        参数:
          - values: 原始值列表
          - consensus_value: 共识值

        返回:
          - dict: 包含共识分析信息的字典
        """
        valid_values = [v for v in values if v is not None]

        if consensus_value is None:
            return {
                "has_consensus": False,
                "original_values": values,
                "valid_values": valid_values,
                "reason": "未达成共识",
            }

        # 统计匹配情况
        matching_count = 0
        for v in valid_values:
            if isinstance(v, str):
                if v == consensus_value:
                    matching_count += 1
            else:
                if abs(v - consensus_value) <= 0.1:
                    matching_count += 1

        return {
            "has_consensus": matching_count >= 2,
            "consensus_value": consensus_value,
            "matching_count": matching_count,
            "total_valid": len(valid_values),
            "original_values": values,
            "valid_values": valid_values,
        }

    async def _validate_extraction_result(
        self, image_base64: str, extracted_data: dict
    ):
        """
        使用LLM验证提取的数据是否正确
        """
        try:
            validation_prompt = (
                "请仔细对比这张 IOL master 晶体单测量报告图片和下面提取的数据，"
                "判断提取的数据是否准确无误。\n\n"
                f"提取的数据：\n{json.dumps(extracted_data, ensure_ascii=False, indent=2)}\n\n"
                "请检查以下方面：\n"
                "1. 患者姓名是否正确\n"
                "2. A常数是否正确\n"
                "3. 左右眼的AL、K1、K2、ACD数值是否准确\n"
                "4. 数值范围是否合理（AL通常在20-30mm，K值通常在35-50D）\n\n"
                "请只回答：\n"
                "- 如果数据完全正确，回答：正确\n"
                "- 如果有任何错误，回答：错误，并简要说明错误原因"
            )

            image_data_uri = f"data:image/jpeg;base64,{image_base64}"

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": validation_prompt},
                            {"type": "image_url", "image_url": {"url": image_data_uri}},
                        ],
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.1,
            }

            # 使用 httpx 发送异步请求
            timeout = httpx.Timeout(60.0, connect=60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                response_data = response.json()

                if "choices" in response_data and len(response_data["choices"]) > 0:
                    validation_response = response_data["choices"][0]["message"][
                        "content"
                    ].strip()
                else:
                    raise ValueError("验证API响应格式不正确：缺少choices字段")

            print(f"=== 二次校验结果 ===")
            print(f"校验响应: {validation_response}")

            is_correct = validation_response.startswith("正确")

            return {
                "is_correct": is_correct,
                "validation_response": validation_response,
            }

        except Exception as e:
            print(f"二次校验时发生异常: {str(e)}")
            # 如果校验失败，默认认为第一次结果正确，避免无限重试
            return {
                "is_correct": True,
                "validation_response": f"校验失败，默认使用第一次结果: {str(e)}",
            }

    async def _fallback_text_extraction(self, image_base64: str, initial_response: str):
        """
        用文本模型对 AI 的初始 response 进行再提取（fallback）。
        """
        try:
            prompt2 = (
                "以下是从 IOL master 晶体单图片中提取的文本内容：\n\n"
                f"{initial_response}\n\n"
                "请使用自我验证的方法，仔细提取患者姓名、A 常数、左右眼的 AL、K1、K2、ACD 数据，"
                "返回 JSON 格式。如果找不到某个字段就设为 null。\n\n"
                "=== 自我验证要求 ===\n"
                "在提取数据前，请思考：\n"
                "1. 是否确认了左右眼的区分？有没有可能将左右眼数据颠倒？\n"
                "2. 每个数值是否与正确的测量项目对应（AL对应眼轴，K1/K2对应角膜曲率）？\n"
                "3. 提取的数值是否在合理范围内？\n"
                "4. 是否有明显的OCR识别错误或数字误读？\n"
                "\n"
                "=== 输出格式 ===\n"
                "请严格按照以下 JSON 格式返回：\n"
                "{\n"
                '  "patient_name": "患者姓名或null",\n'
                '  "a_constant": 数值或null,\n'
                '  "right_eye": {\n'
                '    "AL": 数值或null,\n'
                '    "K1": 数值或null,\n'
                '    "K2": 数值或null,\n'
                '    "ACD": 数值或null\n'
                "  },\n"
                '  "left_eye": {\n'
                '    "AL": 数值或null,\n'
                '    "K1": 数值或null,\n'
                '    "K2": 数值或null,\n'
                '    "ACD": 数值或null\n'
                "  },\n"
                '  "self_verification": {\n'
                '    "confidence_scores": {\n'
                '      "patient_name": 1-5,\n'
                '      "a_constant": 1-5,\n'
                '      "right_eye": {\n'
                '        "AL": 1-5,\n'
                '        "K1": 1-5,\n'
                '        "K2": 1-5,\n'
                '        "ACD": 1-5\n'
                "      },\n"
                '      "left_eye": {\n'
                '        "AL": 1-5,\n'
                '        "K1": 1-5,\n'
                '        "K2": 1-5,\n'
                '        "ACD": 1-5\n'
                "      }\n"
                "    },\n"
                '    "potential_issues": ["描述任何潜在问题或不确定的地方"],\n'
                '    "verification_notes": "自我验证的总结说明"\n'
                "  }\n"
                "}\n\n"
                "=== 数值范围限制（请严格遵循） ===\n"
                "- 眼轴长度 AL: 12.00-38.00mm（正常范围20.00-30.00mm）\n"
                "- 角膜曲率 K1, K2: 30.00-60.00D（正常范围35.00-50.00D）\n"
                "- 前房深度 ACD: 0.00-6.00mm（正常范围2.00-4.50mm）\n"
                "- A常数: 110.00-125.00（常见范围115.00-122.00）\n\n"
                "=== 重要要求 ===\n"
                "- 只返回 JSON，不要其他文字\n"
                "- 所有数值（AL、K1、K2、ACD、a_constant）必须保留2位小数\n"
                "- 即使原始数据是整数，也要写成2位小数格式（如23写成23.00）\n"
                "- 请确保数值精度和格式正确\n"
                "- 如果提取的数值超出上述合理范围，请仔细检查文本内容，确保识别准确\n"
                "- 对于明显异常的数值，请以文本实际显示为准，不要强行修正\n"
                "- 在 self_verification 中诚实评估置信度，低置信度（≤2）的字段需要特别说明"
            )

            # 构造fallback请求payload
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt2}],
                "max_tokens": 1000,
                "temperature": 0.1,
            }

            # 使用 httpx 发送异步请求
            timeout = httpx.Timeout(60.0, connect=60.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                response_data = response.json()

                if "choices" in response_data and len(response_data["choices"]) > 0:
                    resp_text2 = response_data["choices"][0]["message"][
                        "content"
                    ].strip()
                else:
                    raise ValueError("Fallback API响应格式不正确：缺少choices字段")

                if resp_text2.startswith("```json"):
                    resp_text2 = resp_text2[7:]
                if resp_text2.endswith("```"):
                    resp_text2 = resp_text2[:-3]
                resp_text2 = resp_text2.strip()

            try:
                extracted2 = json.loads(resp_text2)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "无法解析 fallback 提取的 JSON",
                    "raw_response": resp_text2,
                }

            cleaned2 = self._validate_and_clean_data(extracted2)

            # 输出fallback模式下LLM返回的原始结果
            print("=== LLM Fallback识别完成，返回结果 ===")
            print(f"初始响应: {initial_response}")
            print(f"Fallback响应: {resp_text2}")
            print(
                f"解析后的JSON: {json.dumps(extracted2, ensure_ascii=False, indent=2)}"
            )
            print(f"清洗后的数据: {json.dumps(cleaned2, ensure_ascii=False, indent=2)}")
            print("=== Fallback识别结果输出完成 ===")

            return {
                "success": True,
                "data": cleaned2,
                "raw_response": resp_text2,
                "fallback_used": True,
            }

        except httpx.HTTPError as e:
            error_msg = f"Fallback API请求失败: {e}"
            print(f"Fallback处理时发生网络异常: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "raw_response": initial_response,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"备用提取失败: {e}",
                "raw_response": initial_response,
            }

    def _validate_and_clean_data(self, data: dict):
        """
        验证 & 清理提取出的数据，把字符串中的数字提取出来。
        规范化数值格式，确保AL、K1、K2、ACD都是2位小数。
        处理新格式：包含 self_verification 字段
        """

        def format_to_two_decimal(value):
            """将数值格式化为2位小数"""
            if value is None:
                return None
            try:
                return round(float(value), 2)
            except (ValueError, TypeError):
                return None

        # 提取核心数据字段，兼容新旧格式
        cleaned = {
            "patient_name": data.get("patient_name"),
            "a_constant": format_to_two_decimal(
                self._clean_number(data.get("a_constant"))
            ),
            "right_eye": {
                "AL": format_to_two_decimal(
                    self._clean_number(data.get("right_eye", {}).get("AL"))
                ),
                "K1": format_to_two_decimal(
                    self._clean_number(data.get("right_eye", {}).get("K1"))
                ),
                "K2": format_to_two_decimal(
                    self._clean_number(data.get("right_eye", {}).get("K2"))
                ),
                "ACD": format_to_two_decimal(
                    self._clean_number(data.get("right_eye", {}).get("ACD"))
                ),
            },
            "left_eye": {
                "AL": format_to_two_decimal(
                    self._clean_number(data.get("left_eye", {}).get("AL"))
                ),
                "K1": format_to_two_decimal(
                    self._clean_number(data.get("left_eye", {}).get("K1"))
                ),
                "K2": format_to_two_decimal(
                    self._clean_number(data.get("left_eye", {}).get("K2"))
                ),
                "ACD": format_to_two_decimal(
                    self._clean_number(data.get("left_eye", {}).get("ACD"))
                ),
            },
        }

        # 如果包含 self_verification 字段，保留它
        if "self_verification" in data:
            cleaned["self_verification"] = data["self_verification"]

        return cleaned

    def _clean_number(self, value):
        """
        把 value 清洗成浮点数或 None。如果是字符串，提取第一个数字（包括小数点和负号）。
        """
        if value is None:
            return None
        # 如果是字符串
        if isinstance(value, str):
            nums = re.findall(r"-?\d+\.?\d*", value)
            if nums:
                try:
                    return float(nums[0])
                except:
                    return None
            else:
                return None
        # 如果是数字 (int / float)
        try:
            return float(value)
        except:
            return None

    def set_api_config(
        self, api_base_url: str = None, api_key: str = None, model: str = None
    ):
        """
        更新 API 配置

        参数:
          - api_base_url: 新的 API Base URL
          - api_key: 新的 API 密钥
          - model: 新的模型名称
        """
        if api_base_url:
            self.api_base_url = api_base_url.rstrip("/")
        if api_key:
            self.api_key = api_key
            self.headers["Authorization"] = f"Bearer {api_key}"
        if model:
            self.model = model

    @staticmethod
    async def extract_iol_data_from_image_complete(
        image_base64: str, env=None, status_callback=None
    ) -> dict:
        """
        完整的图片数据提取流程，包括环境配置和结果处理

        参数:
          - image_base64: base64编码的图片数据
          - env: 环境对象，用于获取API配置和参数限制
          - status_callback: 状态回调函数，用于更新前端状态

        返回:
          - dict: 完整的响应结果，包含success、data、error等字段
        """
        try:

            def update_status(message):
                """更新状态信息"""
                print(f"=== {message} ===")
                if status_callback:
                    status_callback(message)

            update_status("开始完整的图片数据提取流程")

            # 从环境变量获取 API 配置
            api_base_url = (
                getattr(env, "OPENAI_API_URL", "https://api.openai.com/v1")
                if env
                else "https://api.openai.com/v1"
            )
            api_key = getattr(env, "OPENAI_API_KEY", None) if env else None
            model = (
                getattr(env, "OPENAI_MODEL", "gpt-4-vision-preview")
                if env
                else "gpt-4-vision-preview"
            )

            if not api_key:
                update_status("错误：未配置 OpenAI API 密钥")
                return {
                    "success": False,
                    "error": "未配置 OpenAI API 密钥，请在环境变量中设置 OPENAI_API_KEY",
                }

            # 从环境变量获取参数限制配置
            config_params = {}
            if env:
                # 眼轴长度限制
                if hasattr(env, "AL_MIN"):
                    config_params["al_min"] = getattr(env, "AL_MIN")
                if hasattr(env, "AL_MAX"):
                    config_params["al_max"] = getattr(env, "AL_MAX")
                if hasattr(env, "AL_NORMAL_MIN"):
                    config_params["al_normal_min"] = getattr(env, "AL_NORMAL_MIN")
                if hasattr(env, "AL_NORMAL_MAX"):
                    config_params["al_normal_max"] = getattr(env, "AL_NORMAL_MAX")

                # 角膜曲率限制
                if hasattr(env, "K_MIN"):
                    config_params["k_min"] = getattr(env, "K_MIN")
                if hasattr(env, "K_MAX"):
                    config_params["k_max"] = getattr(env, "K_MAX")
                if hasattr(env, "K_NORMAL_MIN"):
                    config_params["k_normal_min"] = getattr(env, "K_NORMAL_MIN")
                if hasattr(env, "K_NORMAL_MAX"):
                    config_params["k_normal_max"] = getattr(env, "K_NORMAL_MAX")

                # 前房深度限制
                if hasattr(env, "ACD_MIN"):
                    config_params["acd_min"] = getattr(env, "ACD_MIN")
                if hasattr(env, "ACD_MAX"):
                    config_params["acd_max"] = getattr(env, "ACD_MAX")
                if hasattr(env, "ACD_NORMAL_MIN"):
                    config_params["acd_normal_min"] = getattr(env, "ACD_NORMAL_MIN")
                if hasattr(env, "ACD_NORMAL_MAX"):
                    config_params["acd_normal_max"] = getattr(env, "ACD_NORMAL_MAX")

                # A常数限制
                if hasattr(env, "A_CONST_MIN"):
                    config_params["a_const_min"] = getattr(env, "A_CONST_MIN")
                if hasattr(env, "A_CONST_MAX"):
                    config_params["a_const_max"] = getattr(env, "A_CONST_MAX")
                if hasattr(env, "A_CONST_COMMON_MIN"):
                    config_params["a_const_common_min"] = getattr(
                        env, "A_CONST_COMMON_MIN"
                    )
                if hasattr(env, "A_CONST_COMMON_MAX"):
                    config_params["a_const_common_max"] = getattr(
                        env, "A_CONST_COMMON_MAX"
                    )

            update_status("API和参数配置完成")

            # 创建WorkerAI实例，传递配置参数
            worker_ai = WorkerAI(
                api_base_url=api_base_url,
                api_key=api_key,
                model=model,
                config_params=config_params,
            )

            # 调用图片提取功能
            result = await worker_ai.extract_iol_data_from_image(
                image_base64, status_callback=status_callback
            )

            update_status("图片提取流程完成")
            return result

        except Exception as e:
            update_status(f"完整图片提取流程发生异常: {str(e)}")
            print(f"完整图片提取流程发生异常: {str(e)}")
            import traceback

            print(f"异常堆栈: {traceback.format_exc()}")
            return {"success": False, "error": f"图片分析失败: {str(e)}"}
