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
                                                "hoffer_q_pacd / haigis_constants 被屏蔽，"
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
                                                "haigis",
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
                                                "haigis",
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
