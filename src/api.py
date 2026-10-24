"""
API模块 - 处理IOL计算器的API接口
"""

import json
import math

from barrett_config import DEFAULT_K_INDEX as DEFAULT_BARRETT_K_INDEX
from barrett_config import normalize_k_index
from barrett_calculate import calculate_barrett_iol
from barrett_iol_models import fetch_iol_model_list, fetch_model_a_constant
from barrett_offline import (
    MODEL_ID,
    MODEL_NOTE,
    solve_iol_power as solve_offline_iol_power,
)
from barrett_toric_calculate import calculate_barrett_toric_iol
from worker_ai import WorkerAI


class APIHandler:
    DEFAULT_A_CONSTANT = 119.30
    DEFAULT_ACD = 3.00
    DEFAULT_REFRACTION = 0.0
    DEFAULT_K_INDEX = DEFAULT_BARRETT_K_INDEX
    # 正常眼默认走离线；online 必须显式指定。
    DEFAULT_CALCULATION_MODE = "offline"
    SUPPORTED_MODES = ("offline", "online")

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

    def _normalize_k_index(self, value):
        """标准化角膜K-index。"""
        return normalize_k_index(value)

    def _normalize_mode(self, value):
        """标准化计算模式：offline（默认）或 online。"""
        if value is None:
            return self.DEFAULT_CALCULATION_MODE
        if not isinstance(value, str):
            raise ValueError("mode 必须是 offline 或 online")
        mode = value.strip().lower()
        if not mode:
            return self.DEFAULT_CALCULATION_MODE
        if mode not in self.SUPPORTED_MODES:
            raise ValueError("mode 只支持 offline 或 online")
        return mode

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

    async def handle_barrett_iol_models(self, request, model_name=None):
        """处理IOL晶体型号查询请求"""
        if request.method != "GET":
            return {
                "error": "Method Not Allowed",
                "message": "此端点只支持GET请求",
            }, 405

        try:
            if model_name:
                result = fetch_model_a_constant(model_name)
                return {
                    "success": True,
                    "data": {
                        "name": model_name,
                        "a_constant": result["a_constant"],
                        "lens_factor": result["lens_factor"],
                    },
                    "message": "查询成功",
                }, 200

            models = fetch_iol_model_list()
            return {
                "success": True,
                "data": {"models": models},
                "message": "获取晶体型号列表成功",
            }, 200

        except Exception as e:
            return {
                "error": "Internal Server Error",
                "message": f"获取晶体型号数据失败: {str(e)}",
            }, 500

    async def handle_barrett_calculate(self, request):
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
            return await self._handle_barrett_calculate(body)

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

    async def handle_barrett_toric_calculate(self, request):
        """处理 Barrett Universal II 散光晶体计算请求。"""
        if request.method != "POST":
            return {
                "error": "Method Not Allowed",
                "message": "此端点只支持POST请求",
            }, 405

        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type:
                return {
                    "error": "Unsupported Media Type",
                    "message": "请求体必须是JSON格式",
                }, 415

            body = await request.json()
            return await self._handle_barrett_toric_calculate(body)
        except json.JSONDecodeError:
            return {"error": "Bad Request", "message": "无效的JSON格式"}, 400
        except (ValueError, TypeError) as exc:
            return {"error": "Bad Request", "message": str(exc)}, 400
        except Exception as exc:
            print(f"处理Barrett散光计算请求时发生错误: {str(exc)}")
            return {
                "error": "Internal Server Error",
                "message": f"散光计算过程中发生错误: {str(exc)}",
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
                # 提取成功，返回数据（部分字段可能未达成共识）
                response_data = {
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
                    "failed_fields": extraction_result.get("failed_fields", []),
                }
                if extraction_result.get("requires_manual_verification"):
                    response_data["requires_manual_verification"] = True
                return response_data, 200
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

    def _calculate_offline_eye(self, params, a_constant, k_index):
        """用离线模块计算单眼，返回与在线结果兼容的 iol_options。"""
        k_mean = (params["K1"] + params["K2"]) / 2.0
        target = params.get("Refraction")
        if target is None:
            target = self.DEFAULT_REFRACTION
        lt = self._normalize_optional_float(params.get("LenThickness"))
        wtw = self._normalize_optional_float(params.get("WTW"))
        solved = solve_offline_iol_power(
            params["AL"],
            k_mean,
            target=target,
            a_constant=a_constant,
            k_index=k_index,
            acd=params.get("ACD"),
            lt=lt,
            wtw=wtw,
        )
        predicted = solved["predicted_refraction"]
        return {
            "biometry": (
                f"AL {params['AL']:.2f} mm; "
                f"K1 {params['K1']:.2f} D; K2 {params['K2']:.2f} D; "
                f"Kmean {k_mean:.2f} D"
            ),
            "prediction": "offline",
            "constants": (
                f"A={a_constant:.2f}; LF={solved['lens_factor']:.2f}; "
                f"K index={k_index}"
            ),
            "iol_options": solved["iol_options"],
            "recommended_power": solved["iol_power_text"],
            "predicted_refraction": (
                round(predicted, 2) if math.isfinite(predicted) else None
            ),
            "elp": round(solved["elp"], 2),
            "confidence": solved["confidence"],
            "low_confidence": solved["low_confidence"],
            "warnings": solved["warnings"],
        }

    def _calculate_offline_result(
        self, right_eye_params, left_eye_params, a_constant, k_index
    ):
        """组装离线模式的双眼结果。"""
        result = {
            "mode": "offline",
            "model": MODEL_ID,
            "model_note": MODEL_NOTE,
            "calibration_report": "docs/calibration_report.md",
            "right_eye": None,
            "left_eye": None,
        }
        if right_eye_params:
            result["right_eye"] = self._calculate_offline_eye(
                right_eye_params, a_constant, k_index
            )
        if left_eye_params:
            result["left_eye"] = self._calculate_offline_eye(
                left_eye_params, a_constant, k_index
            )
        return result

    async def _handle_barrett_calculate(self, body):
        """处理IOL计算请求（默认 offline，可显式指定 online）。"""
        try:
            # 验证必需的参数
            right_eye_params = self._normalize_request_eye_params(
                body.get("right_eye"), "右眼"
            )
            left_eye_params = self._normalize_request_eye_params(
                body.get("left_eye"), "左眼"
            )
            a_constant = self._normalize_a_constant(body.get("a_constant"))
            k_index = self._normalize_k_index(body.get("k_index"))
            patient_name = body.get("patient_name")
            iol_model = body.get("iol_model")
            mode = self._normalize_mode(body.get("mode"))

            # 验证至少提供了一只眼睛的参数
            if not right_eye_params and not left_eye_params:
                return {
                    "error": "Bad Request",
                    "message": "至少需要提供右眼或左眼参数",
                }, 400

            # online 模式保持原有官网调用行为不变。
            if mode == "online":
                result = await calculate_barrett_iol(
                    right_eye_params=right_eye_params,
                    left_eye_params=left_eye_params,
                    a_constant=a_constant,
                    patient_name=patient_name,
                    iol_model=iol_model,
                    k_index=k_index,
                )
                return {
                    "success": True,
                    "data": result,
                    "message": "IOL计算完成",
                }, 200

            # offline 模式：本机聚散度核心 + ELP 近似式，零网络调用。
            result = self._calculate_offline_result(
                right_eye_params, left_eye_params, a_constant, k_index
            )
            return {
                "success": True,
                "data": result,
                "message": "IOL计算完成（离线近似模式）",
            }, 200

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

    async def _handle_barrett_toric_calculate(self, body):
        """标准化并执行独立的 Barrett Universal II Toric 计算。"""
        if not isinstance(body, dict):
            return {
                "error": "Bad Request",
                "message": "请求体必须是JSON对象",
            }, 400

        try:
            # /api/calculate-toric 使用与普通接口相同的 right_eye/left_eye
            # 字段；toric_right_eye/toric_left_eye 作为显式别名保留。
            right_eye = body.get("toric_right_eye") or body.get("right_eye")
            left_eye = body.get("toric_left_eye") or body.get("left_eye")
            a_constant = self._normalize_a_constant(body.get("a_constant"))
            patient_name = body.get("patient_name")
            iol_model = body.get("iol_model")
            k_index = self._normalize_k_index(body.get("k_index"))
            cylinder_mode = body.get("cylinder_mode", "-ve")

            if not right_eye and not left_eye:
                return {
                    "error": "Bad Request",
                    "message": "至少需要提供右眼或左眼散光参数",
                }, 400

            result = await calculate_barrett_toric_iol(
                right_eye_params=right_eye,
                left_eye_params=left_eye,
                a_constant=a_constant,
                patient_name=patient_name,
                iol_model=iol_model,
                k_index=k_index,
                cylinder_mode=cylinder_mode,
            )
            return {
                "success": True,
                "data": result,
                "message": "Barrett Universal II散光计算完成",
            }, 200
        except (ValueError, TypeError) as exc:
            return {"error": "Bad Request", "message": str(exc)}, 400
        except Exception as exc:
            return {
                "error": "Internal Server Error",
                "message": f"散光计算过程中发生错误: {str(exc)}",
            }, 500
