"""
API模块 - 处理IOL计算器的API接口
"""

import json
from calculate import calculate_iol
from worker_ai import WorkerAI


class APIHandler:
    DEFAULT_A_CONSTANT = 119.30
    DEFAULT_ACD = 3.00
    DEFAULT_REFRACTION = 0.0

    def __init__(self, env):
        self.env = env

    def _normalize_optional_float(self, value, default=None, decimal_places=None):
        """将可选数值字段标准化为浮点数。"""
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

    def _require_float(self, value, field_name, decimal_places=None):
        """校验必填字段必须是有效数值。"""
        normalized = self._normalize_optional_float(
            value, decimal_places=decimal_places
        )
        if normalized is None:
            raise ValueError(f"{field_name} 必须是有效数值")
        return normalized

    def _normalize_a_constant(self, value):
        """标准化A常数，未提供时使用默认值。"""
        if value is None:
            return self.DEFAULT_A_CONSTANT

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return self.DEFAULT_A_CONSTANT

        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            raise ValueError("a_constant 必须是有效数值")

    def _normalize_request_eye_params(self, eye_params, eye_name):
        """标准化用户提交的眼部参数。"""
        if not eye_params:
            return None

        if not isinstance(eye_params, dict):
            raise ValueError(f"{eye_name}参数必须是JSON对象")

        return {
            "AL": self._require_float(eye_params.get("AL"), f"{eye_name}AL"),
            "K1": self._require_float(eye_params.get("K1"), f"{eye_name}K1"),
            "K2": self._require_float(eye_params.get("K2"), f"{eye_name}K2"),
            "ACD": self._normalize_optional_float(
                eye_params.get("ACD"), self.DEFAULT_ACD, decimal_places=2
            ),
            "Refraction": self._normalize_optional_float(
                eye_params.get("Refraction"), self.DEFAULT_REFRACTION
            ),
            "LenThickness": (
                ""
                if eye_params.get("LenThickness") is None
                else str(eye_params.get("LenThickness")).strip()
            ),
            "WTW": (
                ""
                if eye_params.get("WTW") is None
                else str(eye_params.get("WTW")).strip()
            ),
        }

    def _normalize_extracted_eye_params(self, eye_params, eye_name):
        """标准化AI提取出的眼部参数。"""
        if not eye_params:
            return None

        if not isinstance(eye_params, dict):
            raise ValueError(f"{eye_name}提取结果格式不正确")

        normalized = {
            "AL": self._normalize_optional_float(eye_params.get("AL")),
            "K1": self._normalize_optional_float(eye_params.get("K1")),
            "K2": self._normalize_optional_float(eye_params.get("K2")),
        }

        if not any(value is not None for value in normalized.values()):
            return None

        missing_fields = [field for field, value in normalized.items() if value is None]
        if missing_fields:
            raise ValueError(
                f"{eye_name}提取结果缺少必需参数: {', '.join(missing_fields)}"
            )

        normalized["ACD"] = self._normalize_optional_float(
            eye_params.get("ACD"), self.DEFAULT_ACD, decimal_places=2
        )

        return normalized

    async def handle_api(self, request):
        """统一API入口，自动检测请求类型并执行相应功能"""

        # 只接受POST请求
        if request.method != "POST":
            return {
                "error": "Method Not Allowed",
                "message": "此端点只支持POST请求",
            }, 405

        try:
            # 解析请求体
            content_type = request.headers.get("content-type", "")

            if "application/json" not in content_type:
                return {
                    "error": "Unsupported Media Type",
                    "message": "请求体必须是JSON格式",
                }, 415

            # 获取请求体数据
            body = await request.json()

            # 自动检测请求类型
            # 如果包含image字段，则执行图片识别和计算流程
            # 如果包含right_eye或left_eye字段，则执行计算流程
            # 否则返回错误

            if "image" in body:
                # 自动处理流程：图片识别 -> 数据提取 -> IOL计算
                return await self._handle_auto_process(body)
            elif "right_eye" in body or "left_eye" in body:
                # 执行计算功能
                return await self._handle_calculate(body)
            else:
                # 无法确定请求类型
                return {
                    "error": "Bad Request",
                    "message": "无法确定请求类型。请提供image字段进行图片识别，或提供right_eye/left_eye字段进行IOL计算",
                }, 400

        except json.JSONDecodeError:
            return {"error": "Bad Request", "message": "无效的JSON格式"}, 400

        except ValueError as e:
            return {"error": "Bad Request", "message": str(e)}, 400

        except Exception as e:
            print(f"处理API请求时发生错误: {str(e)}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"处理过程中发生错误: {str(e)}",
            }, 500

    async def handle_extract(self, request):
        """处理图片提取请求"""

        # 只接受POST请求
        if request.method != "POST":
            return {
                "error": "Method Not Allowed",
                "message": "此端点只支持POST请求",
            }, 405

        try:
            # 解析请求体
            content_type = request.headers.get("content-type", "")

            if "application/json" not in content_type:
                return {
                    "error": "Unsupported Media Type",
                    "message": "请求体必须是JSON格式",
                }, 415

            # 获取请求体数据
            body = await request.json()

            # 执行图片提取功能
            return await self._handle_extract_from_image(body)

        except json.JSONDecodeError:
            return {"error": "Bad Request", "message": "无效的JSON格式"}, 400

        except ValueError as e:
            return {"error": "Bad Request", "message": str(e)}, 400

        except Exception as e:
            print(f"处理图片提取请求时发生错误: {str(e)}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"处理过程中发生错误: {str(e)}",
            }, 500

    async def handle_calculate(self, request):
        """处理IOL计算请求"""

        # 只接受POST请求
        if request.method != "POST":
            return {
                "error": "Method Not Allowed",
                "message": "此端点只支持POST请求",
            }, 405

        try:
            # 解析请求体
            content_type = request.headers.get("content-type", "")

            if "application/json" not in content_type:
                return {
                    "error": "Unsupported Media Type",
                    "message": "请求体必须是JSON格式",
                }, 415

            # 获取请求体数据
            body = await request.json()

            # 执行计算功能
            return await self._handle_calculate(body)

        except json.JSONDecodeError:
            return {"error": "Bad Request", "message": "无效的JSON格式"}, 400

        except ValueError as e:
            return {"error": "Bad Request", "message": str(e)}, 400

        except Exception as e:
            print(f"处理IOL计算请求时发生错误: {str(e)}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"处理过程中发生错误: {str(e)}",
            }, 500

    async def _handle_auto_process(self, body):
        """自动处理流程：图片识别 -> 数据提取 -> IOL计算"""
        try:
            # 验证必需的参数
            image_data = body.get("image")
            if not image_data:
                return {"error": "Bad Request", "message": "缺少图片数据"}, 400

            print(f"图片数据长度: {len(image_data)} 字符")

            # 状态存储（用于实时状态更新）
            status_messages = []

            def status_callback(message):
                """状态回调函数"""
                status_messages.append(
                    {"timestamp": str(__import__("time").time()), "message": message}
                )
                print(f"状态更新: {message}")

            # 调用WorkerAI的完整图片提取流程
            extraction_result = await WorkerAI.extract_iol_data_from_image_complete(
                image_data, self.env, status_callback=status_callback
            )

            # 添加状态信息到结果中
            extraction_result["status_history"] = status_messages

            if not extraction_result["success"]:
                # 提取失败，返回错误信息
                response_data = {
                    "success": False,
                    "error": extraction_result["error"],
                    "status_history": status_messages,
                    "attempts": extraction_result.get("attempts", []),
                    "total_extractions": extraction_result.get("total_extractions", 1),
                    "consensus_reached": extraction_result.get(
                        "consensus_reached", False
                    ),
                    "consensus_details": extraction_result.get("consensus_details", {}),
                }

                # 如果需要手动校验，使用200状态码但标记为失败
                if extraction_result.get("requires_manual_verification"):
                    response_data["requires_manual_verification"] = True
                    return response_data, 200
                else:
                    return response_data, 500

            # 提取成功，获取数据
            extracted_data = extraction_result["data"]

            # 准备IOL计算参数
            patient_name = extracted_data.get("patient_name")
            a_constant = self._normalize_optional_float(
                extracted_data.get("a_constant"),
                self.DEFAULT_A_CONSTANT,
                decimal_places=2,
            )

            # 处理右眼参数
            right_eye_params = self._normalize_extracted_eye_params(
                extracted_data.get("right_eye"), "右眼"
            )

            # 处理左眼参数
            left_eye_params = self._normalize_extracted_eye_params(
                extracted_data.get("left_eye"), "左眼"
            )

            # 验证至少提供了一只眼睛的参数
            if not right_eye_params and not left_eye_params:
                return {
                    "success": False,
                    "error": "未能从图片中提取到有效的眼睛参数",
                }, 400

            # 调用IOL计算函数
            calculation_result = await calculate_iol(
                right_eye_params=right_eye_params,
                left_eye_params=left_eye_params,
                a_constant=a_constant,
                patient_name=patient_name,
            )

            # 构造最终响应
            response_data = {
                "success": True,
                "data": {
                    "patient_name": patient_name,
                    "a_constant": a_constant,
                    "extracted_data": extracted_data,
                    "calculation_result": calculation_result,
                },
                "message": "图片识别和IOL计算完成",
                "status_history": status_messages,
                "attempts": extraction_result.get("attempts", []),
                "total_extractions": extraction_result.get("total_extractions", 1),
                "consensus_reached": extraction_result.get("consensus_reached", True),
                "consensus_details": extraction_result.get("consensus_details", {}),
            }

            return response_data, 200

        except Exception as e:
            print(f"自动处理流程发生错误: {str(e)}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"自动处理流程发生错误: {str(e)}",
            }, 500

    async def _handle_extract_from_image(self, body):
        """处理从图片提取IOL数据的请求"""
        try:
            # 验证必需的参数
            image_data = body.get("image")
            if not image_data:
                return {"error": "Bad Request", "message": "缺少图片数据"}, 400

            print(f"图片数据长度: {len(image_data)} 字符")

            # 状态存储（用于实时状态更新）
            status_messages = []

            def status_callback(message):
                """状态回调函数"""
                status_messages.append(
                    {"timestamp": str(__import__("time").time()), "message": message}
                )
                print(f"状态更新: {message}")

            # 调用WorkerAI的完整图片提取流程
            extraction_result = await WorkerAI.extract_iol_data_from_image_complete(
                image_data, self.env, status_callback=status_callback
            )

            # 添加状态信息到结果中
            extraction_result["status_history"] = status_messages

            if extraction_result["success"]:
                # 提取成功，返回数据
                return {
                    "success": True,
                    "data": extraction_result["data"],
                    "message": "图片数据提取成功",
                    "status_history": status_messages,
                    "attempts": extraction_result.get("attempts", []),
                    "total_extractions": extraction_result.get("total_extractions", 1),
                    "consensus_reached": extraction_result.get(
                        "consensus_reached", True
                    ),
                    "consensus_details": extraction_result.get("consensus_details", {}),
                }, 200
            else:
                # 提取失败，返回错误信息
                response_data = {
                    "success": False,
                    "error": extraction_result["error"],
                    "status_history": status_messages,
                    "attempts": extraction_result.get("attempts", []),
                    "total_extractions": extraction_result.get("total_extractions", 1),
                    "consensus_reached": extraction_result.get(
                        "consensus_reached", False
                    ),
                    "consensus_details": extraction_result.get("consensus_details", {}),
                }

                # 如果需要手动校验，使用200状态码但标记为失败
                if extraction_result.get("requires_manual_verification"):
                    response_data["requires_manual_verification"] = True
                    return response_data, 200
                else:
                    return response_data, 500

        except Exception as e:
            print(f"处理图片提取请求时发生错误: {str(e)}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"图片处理过程中发生错误: {str(e)}",
            }, 500

    async def _handle_calculate(self, body):
        """处理IOL计算请求"""
        try:
            # 验证必需的参数
            right_eye_params = self._normalize_request_eye_params(
                body.get("right_eye"), "右眼"
            )
            left_eye_params = self._normalize_request_eye_params(
                body.get("left_eye"), "左眼"
            )
            a_constant = self._normalize_a_constant(body.get("a_constant"))
            patient_name = body.get("patient_name")

            # 验证至少提供了一只眼睛的参数
            if not right_eye_params and not left_eye_params:
                return {
                    "error": "Bad Request",
                    "message": "至少需要提供右眼或左眼参数",
                }, 400

            # 调用计算函数
            result = await calculate_iol(
                right_eye_params=right_eye_params,
                left_eye_params=left_eye_params,
                a_constant=a_constant,
                patient_name=patient_name,
            )

            # 返回成功结果
            return {"success": True, "data": result, "message": "IOL计算完成"}, 200

        except ValueError as e:
            return {"error": "Bad Request", "message": str(e)}, 400

        except Exception as e:
            return {
                "error": "Internal Server Error",
                "message": f"计算过程中发生错误: {str(e)}",
            }, 500
