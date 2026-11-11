"""
API文档模块 - 提供Swagger UI风格的API文档页面
"""

import json


def get_openapi_spec():
    """
    返回OpenAPI规范文档
    """
    specification = {
        "openapi": "3.0.0",
        "info": {
            "title": "Barretcalcata IOL Calculator API",
            "description": "基于Cloudflare Workers的IOL（人工晶体）度数计算API，提交JSON参数即可获取Barrett Universal II公式计算结果",
            "version": "2.0.0",
            "contact": {
                "name": "API Support",
                "url": "https://barrettcalcata.killgfat.com",
            },
        },
        "paths": {
            "/api/extract": {
                "post": {
                    "summary": "从报告图片提取 IOL 数据",
                    "description": (
                        "使用视觉模型从 IOL Master 报告图片中提取眼部参数。"
                        "提取完成后，请由调用方确认数据并调用 /api/calculate。"
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "image": {
                                            "type": "string",
                                            "format": "byte",
                                            "description": "报告图片的 Base64 数据",
                                        }
                                    },
                                    "required": ["image"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "图片数据提取完成"},
                        "400": {"description": "请求参数无效"},
                        "405": {"description": "仅支持 POST 请求"},
                        "415": {"description": "请求体必须是 JSON 格式"},
                        "500": {"description": "图片识别失败"},
                    },
                }
            },
            "/api/calculate": {
                "post": {
                    "summary": "执行IOL计算",
                    "description": (
                        "提交眼睛参数，计算人工晶体度数。model 必填，决定用哪套公式；"
                        "至少提供一只眼的参数。iol_model 命中内置 ULIB 时由型号决定"
                        "常数。各公式的算法、常数来源与适用域见 docs/formulas.md。"
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "right_eye": {
                                            "type": "object",
                                            "description": "右眼参数",
                                            "properties": {
                                                "AL": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "眼轴长度（mm）",
                                                    "example": 23.5,
                                                },
                                                "K1": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "角膜曲率K1（D）",
                                                    "example": 43.5,
                                                },
                                                "K2": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "角膜曲率K2（D）",
                                                    "example": 44.0,
                                                },
                                                "ACD": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "术前前房深度（mm）；haigis-toric 必填实测值，其他模型按各自规则处理",
                                                    "example": 3.0,
                                                },
                                                "Refraction": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "目标屈光度（D），默认0",
                                                    "example": 0,
                                                },
                                                "LenThickness": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "minimum": 0,
                                                    "maximum": 15,
                                                    "description": "晶体厚度（mm，可选）",
                                                    "example": 4.6,
                                                },
                                                "WTW": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "minimum": 5,
                                                    "maximum": 25,
                                                    "description": "白到白距离（mm，可选）",
                                                    "example": 11.9,
                                                },
                                            },
                                            "required": ["AL", "K1", "K2"],
                                        },
                                        "left_eye": {
                                            "type": "object",
                                            "description": "左眼参数",
                                            "properties": {
                                                "AL": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "眼轴长度（mm）",
                                                    "example": 23.3,
                                                },
                                                "K1": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "角膜曲率K1（D）",
                                                    "example": 43.8,
                                                },
                                                "K2": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "角膜曲率K2（D）",
                                                    "example": 44.2,
                                                },
                                                "ACD": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "术前前房深度（mm）；haigis-toric 必填实测值，其他模型按各自规则处理",
                                                    "example": 3.0,
                                                },
                                                "Refraction": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "目标屈光度（D），默认0",
                                                    "example": 0,
                                                },
                                                "LenThickness": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "minimum": 0,
                                                    "maximum": 15,
                                                    "description": "晶体厚度（mm，可选）",
                                                    "example": 4.6,
                                                },
                                                "WTW": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "minimum": 5,
                                                    "maximum": 25,
                                                    "description": "白到白距离（mm，可选）",
                                                    "example": 11.9,
                                                },
                                            },
                                            "required": ["AL", "K1", "K2"],
                                        },
                                        "a_constant": {
                                            "type": "number",
                                            "format": "float",
                                            "description": "A常数，默认119.3",
                                            "example": 119.3,
                                        },
                                        "patient_name": {
                                            "type": "string",
                                            "description": "患者姓名（可选）",
                                        },
                                        "iol_model": {
                                            "type": "string",
                                            "description": (
                                                "IOL 晶体型号（可选）。命中内置 ULIB 时"
                                                "按型号取常数，请求里的 a_constant / "
                                                "hoffer_q_pacd / holladay1_sf / "
                                                "haigis_constants 被屏蔽，"
                                                "详见 constants_source.ignored_request。"
                                                "未声明或未命中时按请求给的常数计算；"
                                                "Barrett 系列不查 ULIB。"
                                            ),
                                            "example": "AMO ZCB00",
                                        },
                                        "k_index": {
                                            "type": "number",
                                            "format": "float",
                                            "enum": [1.3375, 1.332],
                                            "default": 1.3375,
                                            "description": "角膜等效折射率。1.3375会转换为Barrett表单值337.5，1.332会转换为332。",
                                            "example": 1.3375,
                                        },
                                        "model": {
                                            "type": "string",
                                            "enum": [
                                                "barrett_ii_offline",
                                                "barrett_ii",
                                                "srkt",
                                                "hoffer_q",
                                                "holladay1",
                                                "haigis",
                                                "castrop",
                                                "haigis-toric",
                                            ],
                                            "description": (
                                                "计算模型（必填）。barrett_ii_offline = Barrett 本地离线；"
                                                "barrett_ii = Barrett 官网在线；其余为对应本地公式。"
                                            ),
                                            "example": "barrett_ii_offline",
                                        },
                                        "mode": {
                                            "type": "string",
                                            "enum": ["offline", "online"],
                                            "default": "offline",
                                            "deprecated": True,
                                            "description": "兼容字段；新客户端请使用 model。model 存在时忽略本字段。",
                                            "example": "offline",
                                        },
                                        "formula": {
                                            "type": "string",
                                            "enum": [
                                                "barrett",
                                                "srkt",
                                                "hoffer_q",
                                                "holladay1",
                                                "haigis",
                                                "castrop",
                                                "haigis-toric",
                                            ],
                                            "default": "barrett",
                                            "deprecated": True,
                                            "description": "兼容字段；新客户端请使用 model。model 存在时忽略本字段。",
                                            "example": "barrett",
                                        },
                                        "step": {
                                            "type": "number",
                                            "format": "float",
                                            "default": 0.5,
                                            "minimum": 0.1,
                                            "maximum": 2.0,
                                            "description": "本地 IOL 候选表步长（D）。",
                                            "example": 0.5,
                                        },
                                        "hoffer_q_pacd": {
                                            "type": "number",
                                            "description": "仅 model=hoffer_q 可用的 pACD（mm）；留空由 A 常数推导。",
                                            "minimum": 0.0,
                                            "maximum": 8.0,
                                        },
                                        "holladay1_sf": {
                                            "type": "number",
                                            "format": "float",
                                            "description": (
                                                "仅 model=holladay1 可用的 Surgeon Factor"
                                                "（SF，mm）。留空则由 A 常数按厂商标准关系"
                                                " SF=0.5663*A-65.60 换算；声明命中 ULIB 的"
                                                " iol_model 时由型号提供 SF，本字段被屏蔽。"
                                                "给出 SF 时 a_constant 不再参与计算。"
                                                "范围按 ULIB 实测跨度取 -10~12。"
                                            ),
                                            "minimum": -10.0,
                                            "maximum": 12.0,
                                            "example": 1.84,
                                        },
                                        "haigis_constants": {
                                            "type": "object",
                                            "description": (
                                                "仅 model=haigis/haigis-toric 可用。提供优化后的 a0/a1/a2 时，"
                                                "不再由 A 常数推导 a0；a_constant 会被忽略。"
                                                "声明了命中 ULIB 的 iol_model 时本字段被型号常数"
                                                "屏蔽；没声明 iol_model 时 haigis-toric 必须提供。"
                                            ),
                                            "properties": {
                                                "a0": {"type": "number"},
                                                "a1": {"type": "number"},
                                                "a2": {"type": "number"},
                                            },
                                            "required": ["a0", "a1", "a2"],
                                        },
                                        "castrop_constants": {
                                            "type": "object",
                                            "description": (
                                                "仅 model=castrop 可用。C/H/R 取自 IOLCon 的 "
                                                "Castrop(C / H / R) 列。ULIB 快照（2016-10-31 停更）"
                                                "不含这三列，所以选了 iol_model 也不会覆盖本字段。"
                                                "留空时用论文优化初值 C=0.40/H=0.00/R=0.00，"
                                                "结果标记为低置信度。"
                                            ),
                                            "properties": {
                                                "C": {
                                                    "type": "number",
                                                    "minimum": 0.2,
                                                    "maximum": 0.6,
                                                    "description": "晶状体厚度比例系数，典型 0.35~0.44",
                                                },
                                                "H": {
                                                    "type": "number",
                                                    "minimum": -1.0,
                                                    "maximum": 1.0,
                                                    "description": "IOL 主平面相对晶状体赤道面的轴向偏移（mm）",
                                                },
                                                "R": {
                                                    "type": "number",
                                                    "minimum": -1.0,
                                                    "maximum": 1.0,
                                                    "description": (
                                                        "折算到屈光度的系统偏移（D），"
                                                        "求解时以 target-R 进入光学链"
                                                    ),
                                                },
                                            },
                                            "required": ["C", "H", "R"],
                                            "example": {"C": 0.424, "H": -0.312, "R": 0.077},
                                        },
                                        "castrop_elp": {
                                            "type": "number",
                                            "minimum": 2.0,
                                            "maximum": 12.0,
                                            "description": (
                                                "仅 model=castrop 可用。直接给出 ELP（mm，自角膜前顶点"
                                                "量到 IOL 主平面），给出后不再由 C/H 与 ACD/LT 推导；"
                                                "R 仍按 castrop_constants 作用于目标屈光度。"
                                            ),
                                        },
                                        "castrop_elp_model": {
                                            "type": "string",
                                            "enum": [
                                                "acd_lt",
                                                "regression",
                                                "regression_no_r",
                                            ],
                                            "default": "acd_lt",
                                            "description": (
                                                "仅 model=castrop 且未给 castrop_elp 时生效，"
                                                "对应 IOLCon 的 ELP calculation 三个选项："
                                                "acd_lt = ACD + C·LT + H（论文 2021 原式）；"
                                                "regression = 0.045·AL + 0.761·ACD - 0.042·r + C·LT + H；"
                                                "regression_no_r = 0.036·AL + 0.753·ACD + C·LT + H。"
                                            ),
                                        },
                                        "castrop_cct": {
                                            "type": "number",
                                            "minimum": 0.3,
                                            "maximum": 0.9,
                                            "default": 0.5,
                                            "description": "仅 model=castrop 可用。中央角膜厚度（mm），按论文默认 0.50。",
                                        },
                                        "castrop_posterior_ratio": {
                                            "type": "number",
                                            "minimum": 0.6,
                                            "maximum": 0.95,
                                            "description": (
                                                "仅 model=castrop 可用。角膜后/前表面半径比，"
                                                "默认 6.4/7.77≈0.8237（论文给定值）。"
                                            ),
                                        },
                                        "castrop_al_correction": {
                                            "type": "boolean",
                                            "default": True,
                                            "description": (
                                                "仅 model=castrop 可用。是否用 Cooke 回归把光学眼轴"
                                                "换算为等效分段眼轴（默认开启，与论文一致）。"
                                            ),
                                        },
                                    },
                                    "required": ["model"],
                                },
                                "example": {
                                    "right_eye": {
                                        "AL": 23.5,
                                        "K1": 43.5,
                                        "K2": 44.0,
                                        "ACD": 3.0,
                                        "Refraction": 0,
                                    },
                                    "left_eye": {
                                        "AL": 23.3,
                                        "K1": 43.8,
                                        "K2": 44.2,
                                        "ACD": 3.0,
                                        "Refraction": 0,
                                    },
                                    "a_constant": 119.3,
                                    "k_index": 1.3375,
                                    "model": "barrett_ii_offline",
                                    "patient_name": "张三",
                                },
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "计算成功",
                            "content": {
                                "application/json": {
                                    # 只展示结构与关键字段；每眼完整候选表
                                    # 与 used_inputs 已在字段说明中覆盖。
                                    "example": {
                                        "success": True,
                                        "data": {
                                            "calculation_model": "barrett_ii_offline",
                                            "calculation_model_label": "Barrett Universal II（离线）",
                                            "formula": "barrett",
                                            "mode": "offline",
                                            "model": "BUII-ALK-offline-surrogate/1.0",
                                            "constants_source": {
                                                "source": "ulib",
                                                "ulib_name": "AMO Tecnis 1 ZCB00",
                                                "applied": ["a_constant"],
                                                "ignored_request": ["a_constant"],
                                            },
                                            "right_eye": {
                                                "used_inputs": {
                                                    "AL": 23.5,
                                                    "K": 43.75,
                                                    "a_constant": 119.3,
                                                    "ACD": 3.2,
                                                },
                                                "ignored_inputs": [],
                                                "recommended_power": "20.0",
                                                "predicted_refraction": -0.25,
                                                "iol_options": [
                                                    {
                                                        "iol_power": "20.0",
                                                        "optic": None,
                                                        "refraction": "-0.25",
                                                        "recommended": True,
                                                    }
                                                ],
                                            },
                                        },
                                        "message": "IOL计算完成",
                                    }
                                }
                            },
                        },
                        "400": {"description": "缺少必需参数或参数无效"},
                        "405": {"description": "请求方法不允许（仅支持POST）"},
                        "415": {"description": "请求体必须是JSON格式"},
                        "500": {"description": "计算失败"},
                    },
                }
            },
            "/api/calculate-toric": {
                "post": {
                    "summary": "执行 Barrett Universal II 散光晶体计算",
                    "description": (
                        "提交 K1/K1Axis、K2/K2Axis 角膜曲率及轴位、眼轴、ACD、"
                        "晶体厚度、WTW 等参数，返回散光晶体型号、球镜度数和建议轴位。"
                        "响应 calculation_model 固定为 barrett_ii_toric（在线）。"
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "right_eye": {
                                            "$ref": "#/components/schemas/ToricEye"
                                        },
                                        "left_eye": {
                                            "$ref": "#/components/schemas/ToricEye"
                                        },
                                        # 兼容别名：from_mapping 会优先读这两个字段。
                                        # OpenAPI 3.0 的 Reference Object 不能带兄弟字段，
                                        # 这里用 allOf 包裹后再补充说明。
                                        "toric_right_eye": {
                                            "allOf": [
                                                {
                                                    "$ref": "#/components/schemas/ToricEye"
                                                }
                                            ],
                                            "deprecated": True,
                                            "description": "right_eye 的兼容别名，两者同时给出时以本字段为准",
                                        },
                                        "toric_left_eye": {
                                            "allOf": [
                                                {
                                                    "$ref": "#/components/schemas/ToricEye"
                                                }
                                            ],
                                            "deprecated": True,
                                            "description": "left_eye 的兼容别名，两者同时给出时以本字段为准",
                                        },
                                        "a_constant": {
                                            "type": "number",
                                            "default": 119.3,
                                            "minimum": 112,
                                            "maximum": 125,
                                        },
                                        "iol_model": {"type": "string"},
                                        "patient_name": {"type": "string"},
                                        "k_index": {
                                            "type": "number",
                                            "enum": [1.3375, 1.332],
                                            "default": 1.3375,
                                        },
                                        "cylinder_mode": {
                                            "type": "string",
                                            "enum": ["+ve", "-ve"],
                                            "default": "-ve",
                                        },
                                    },
                                    "anyOf": [
                                        {"required": ["right_eye"]},
                                        {"required": ["left_eye"]},
                                        {"required": ["toric_right_eye"]},
                                        {"required": ["toric_left_eye"]},
                                    ],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "散光计算成功并返回轴位图元数据"},
                        "400": {"description": "缺少必需参数或参数无效"},
                        "405": {"description": "请求方法不允许（仅支持POST）"},
                        "415": {"description": "请求体必须是JSON格式"},
                        "500": {"description": "散光计算失败"},
                    },
                }
            },
            "/api/iol-models": {
                "get": {
                    "summary": "查询可选晶体型号与常数",
                    "description": (
                        "带 formula 时返回该公式的候选型号列表：Barrett 系列用"
                        "官网型号清单（官网不可达时降级到内置映射表并用 "
                        "source=barrett_local_map 与 warnings 标明），"
                        "其余公式直接读内置 ULIB 快照。"
                        "formula=castrop 是例外：ULIB 快照（2016-10-31 停更）"
                        "不含该 2021 年公式的 C/H/R，因此返回空 models、"
                        "source=none 与 constants_available=false，常数请用 "
                        "castrop_constants 或 castrop_elp 传入。"
                        "带 model 时返回单个型号的常数。两者同时给出时以 model "
                        "优先。都不给时按 Barrett 返回列表，保持向后兼容。"
                    ),
                    "parameters": [
                        {
                            "name": "formula",
                            "in": "query",
                            "required": False,
                            "description": (
                                "barrett / srkt / hoffer_q / holladay1 / "
                                "haigis / castrop / haigis-toric；也接受 "
                                "barrett_ii 与 "
                                "barrett_ii_offline 这类计算模型名"
                            ),
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "model",
                            "in": "query",
                            "required": False,
                            "description": "晶体型号名，返回该型号的常数",
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {
                        "200": {"description": "查询成功"},
                        "405": {"description": "请求方法不允许（仅支持GET）"},
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "错误类型"},
                        "message": {"type": "string", "description": "错误消息"},
                    },
                },
                "SuccessResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "description": "操作是否成功"},
                        "data": {"type": "object", "description": "计算结果"},
                        "message": {"type": "string", "description": "操作消息"},
                    },
                },
                "ToricEye": {
                    "type": "object",
                    "required": [
                        "K1",
                        "K1Axis",
                        "K2",
                        "K2Axis",
                        "AL",
                        "lens_thickness",
                        "WTW",
                    ],
                    "properties": {
                        "K1": {"type": "number", "minimum": 30, "maximum": 60},
                        "K1Axis": {"type": "number", "minimum": 0, "maximum": 180},
                        "K2": {"type": "number", "minimum": 30, "maximum": 60},
                        "K2Axis": {"type": "number", "minimum": 0, "maximum": 180},
                        "AL": {"type": "number", "minimum": 12, "maximum": 38},
                        "ACD": {"type": "number", "default": 3.0},
                        "target_refraction": {"type": "number", "default": 0},
                        "incision_sia": {"type": "number", "default": 0},
                        "incision_location": {"type": "number", "default": 135},
                        "lens_thickness": {
                            "type": "number",
                            "minimum": 2,
                            "maximum": 8,
                        },
                        "WTW": {"type": "number", "minimum": 8, "maximum": 14},
                    },
                },
            }
        },
    }
    # 本地散光复用普通计算入口；在线 Barrett Toric 的 schema 独立保留。
    schema = specification["paths"]["/api/calculate"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    toric_properties = {
        "K1Axis": {
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "description": "Haigis-T：K1 的光学弱子午线，与 K2Axis 正交",
        },
        "K2Axis": {
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "description": "Haigis-T：K2 的光学强子午线",
        },
        "iol_cylinder": {
            "type": "number",
            "minimum": 0,
            "default": 0,
            "description": "实际植入的 IOL 平面柱镜量值（D）",
        },
        "iol_axis": {
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "description": "IOL 弱子午线对齐轴；非零 iol_cylinder 时必填",
        },
        "iol_spherical_equivalent": {
            "type": "number",
            "minimum": -10,
            "maximum": 45,
            "description": "实际 IOL 球镜等效度数 SE；缺省使用 Haigis 推荐 SE",
        },
        "posterior_mode": {
            "type": "string",
            "enum": ["none", "measured", "estimated", "total"],
            "default": "none",
            "description": (
                "none=忽略 PCA 并警告；measured=实测光学 PCA；"
                "estimated=显式启用 0.30 D@0 ATR 代理，"
                "UNVERIFIED-PENDING-PRIMARY，尚非已核实的 Haigis-T 系数；"
                "total=用 TK/TCRP 总散光替换前表面及 PCA，禁止重复叠加"
            ),
        },
        "posterior_cylinder": {
            "type": "number",
            "minimum": 0,
            "description": "measured 必填；角膜平面 PCA 光学量值（D）",
        },
        "posterior_axis": {
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "description": "measured 必填；PCA 光学强子午线，不是后表面曲率陡轴",
        },
        "total_cylinder": {
            "type": "number",
            "minimum": 0,
            "description": "total 必填；经测量定义校准的角膜平面总散光（D）",
        },
        "total_axis": {
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "description": "total 必填；总散光光学强子午线",
        },
        "total_source": {
            "type": "string",
            "enum": ["TK", "TCRP"],
            "description": "total 必填；不自动换算 TK/TCRP 的平均屈光力",
        },
        "incision_sia": {
            "type": "number",
            "minimum": 0,
            "default": 0,
            "description": "角膜平面 SICA；沿切口子午线的扁平化量（D）",
        },
        "incision_location": {
            "type": "number",
            "minimum": 0,
            "maximum": 360,
            "description": "切口位置（度）；非零 incision_sia 时必填",
        },
        "cylinder_powers": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "number", "minimum": 0},
            "description": "可供的 IOL 平面柱镜档位；省略时仅返回连续解",
        },
    }
    for eye in ("right_eye", "left_eye"):
        schema["properties"][eye]["properties"].update(toric_properties)
    # OpenAPI 3.0 没有 if/then，用互斥的 oneOf 表达「条件必填」：
    # 前一个分支命中该取值并强制附带字段，后一个分支覆盖其余取值。
    toric_conditional_rules = [
        {
            "oneOf": [
                {
                    "required": [
                        "posterior_mode",
                        "posterior_cylinder",
                        "posterior_axis",
                    ],
                    "properties": {"posterior_mode": {"enum": ["measured"]}},
                },
                {"properties": {"posterior_mode": {"not": {"enum": ["measured"]}}}},
            ]
        },
        {
            "oneOf": [
                {
                    "required": [
                        "posterior_mode",
                        "total_cylinder",
                        "total_axis",
                        "total_source",
                    ],
                    "properties": {"posterior_mode": {"enum": ["total"]}},
                },
                {"properties": {"posterior_mode": {"not": {"enum": ["total"]}}}},
            ]
        },
        # OpenAPI 3.0 的 exclusiveMinimum 是布尔值，这里改用「非 0」等价表达。
        {
            "oneOf": [
                {
                    "required": ["iol_cylinder", "iol_axis"],
                    "properties": {"iol_cylinder": {"not": {"enum": [0]}}},
                },
                {"properties": {"iol_cylinder": {"enum": [0]}}},
            ]
        },
    ]
    specification["components"]["schemas"]["HaigisToricEye"] = {
        "type": "object",
        "description": (
            "model=haigis-toric 的每眼参数。ACD 必须实测，三常数放在请求级 "
            "haigis_constants 或由 iol_model 查表。axis 指光学强子午线，"
            "负柱镜处方轴为 axis+90。LT/WTW 不参与计算，"
            "完整约定见 docs/formulas.md。"
        ),
        "required": ["AL", "K1", "K2", "K1Axis", "K2Axis", "ACD"],
        "properties": {
            **schema["properties"]["right_eye"]["properties"],
            "ACD": {
                "type": "number",
                "minimum": 0.5,
                "maximum": 8,
                "description": "术前实测 ACD（mm），无默认值",
            },
        },
        "allOf": toric_conditional_rules,
    }
    schema["allOf"] = [
        {
            "oneOf": [
                {"properties": {"model": {"not": {"enum": ["haigis-toric"]}}}},
                {
                    "properties": {
                        "model": {"enum": ["haigis-toric"]},
                        "right_eye": {"$ref": "#/components/schemas/HaigisToricEye"},
                        "left_eye": {"$ref": "#/components/schemas/HaigisToricEye"},
                    },
                    # 三常数可以直接给，也可以由命中 ULIB 的型号查表得到。
                    "anyOf": [
                        {"required": ["haigis_constants"]},
                        {"required": ["iol_model"]},
                    ],
                },
            ],
        }
    ]
    return specification


def get_swagger_ui_html():
    """
    返回Swagger UI HTML页面
    """
    openapi_spec = json.dumps(get_openapi_spec(), ensure_ascii=False, indent=2)

    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Barrettcalcata API 文档</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css">
    <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5.9.0/favicon-32x32.png" sizes="32x32" />
    <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5.9.0/favicon-16x16.png" sizes="16x16" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *,
        *:before,
        *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin: 0;
            background: #fafafa;
        }}
        .swagger-ui .topbar {{
            background-color: #1e3a8a;
            padding: 10px 0;
        }}
        .swagger-ui .topbar .download-url-wrapper {{
            display: none;
        }}
        .api-title {{
            color: white;
            font-size: 1.5em;
            font-weight: bold;
            padding: 10px 20px;
        }}
        .api-description {{
            color: white;
            padding: 0 20px 10px;
            font-size: 0.9em;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                spec: {openapi_spec},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                docExpansion: 'list',
                filter: true,
                tagsSorter: 'alpha',
                operationsSorter: 'alpha',
                defaultModelsExpandDepth: 1,
                defaultModelExpandDepth: 1,
                displayRequestDuration: true,
                showExtensions: true,
                showCommonExtensions: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
                validatorUrl: null
            }});
            
            // 自定义顶部栏
            const topbar = document.querySelector('.topbar');
            if (topbar) {{
                topbar.innerHTML = `
                    <div class="api-title">Barrettcalcata IOL Calculator API</div>
                    <div class="api-description">基于Cloudflare Workers的IOL（人工晶体）度数计算API，提交JSON参数即可获取计算结果</div>
                ` + topbar.innerHTML;
            }}
            
            window.ui = ui;
        }};
    </script>
</body>
</html>
"""


def get_openapi_json():
    """
    返回OpenAPI规范的JSON格式
    """
    return get_openapi_spec()
