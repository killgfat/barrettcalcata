"""API模块 - 处理IOL计算器的API接口。"""

import json

from formula import (
    CalculationRequest,
    FormulaError,
    ToricCalculationRequest,
    calculate,
    calculate_toric,
    fetch_iol_model_list,
    fetch_model_a_constant,
)
from worker_ai import WorkerAI


class APIHandler:
    def __init__(self, env):
        self.env = env

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
            print(f"处理图片提取请求时发生错误: {e!s}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"处理过程中发生错误: {e!s}",
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
            print(f"处理图片提取请求时发生错误: {e!s}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"图片处理过程中发生错误: {e!s}",
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
                "message": f"获取晶体型号数据失败: {e!s}",
            }, 500

    async def handle_barrett_calculate(self, request):
        """处理IOL计算请求。"""
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
            return await self._handle_barrett_calculate(body)
        except json.JSONDecodeError:
            return {"error": "Bad Request", "message": "无效的JSON格式"}, 400
        except (FormulaError, ValueError) as exc:
            return {"error": "Bad Request", "message": str(exc)}, 400
        except Exception as exc:
            print(f"处理IOL计算请求时发生错误: {exc!s}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"处理过程中发生错误: {exc!s}",
            }, 500

    async def _handle_barrett_calculate(self, body):
        """把 JSON 转成 CalculationRequest，并调用唯一公式入口。"""
        try:
            request = CalculationRequest.from_mapping(body)
            result = await calculate(request)
            message = (
                "IOL计算完成（离线模式）"
                if result.get("mode") == "offline"
                else "IOL计算完成"
            )
            return {"success": True, "data": result, "message": message}, 200
        except (FormulaError, ValueError) as exc:
            return {"error": "Bad Request", "message": str(exc)}, 400
        except Exception as exc:
            print(f"处理IOL计算请求时发生错误: {exc!s}")
            import traceback

            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "error": "Internal Server Error",
                "message": f"处理过程中发生错误: {exc!s}",
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
        except (FormulaError, ValueError, TypeError) as exc:
            return {"error": "Bad Request", "message": str(exc)}, 400
        except Exception as exc:
            print(f"处理Barrett散光计算请求时发生错误: {exc!s}")
            return {
                "error": "Internal Server Error",
                "message": f"散光计算过程中发生错误: {exc!s}",
            }, 500

    async def _handle_barrett_toric_calculate(self, body):
        """把 JSON 转成 ToricCalculationRequest，并调用公式入口。"""
        try:
            request = ToricCalculationRequest.from_mapping(body)
            result = await calculate_toric(request)
            return {
                "success": True,
                "data": result,
                "message": "Barrett Universal II散光计算完成",
            }, 200
        except (FormulaError, ValueError, TypeError) as exc:
            return {"error": "Bad Request", "message": str(exc)}, 400
        except Exception as exc:
            return {
                "error": "Internal Server Error",
                "message": f"散光计算过程中发生错误: {exc!s}",
            }, 500

