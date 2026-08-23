"""
API文档模块 - 提供Swagger UI风格的API文档页面
"""

import json


def get_openapi_spec():
    """
    返回OpenAPI规范文档
    """
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Barretcalcata IOL Calculator API",
            "description": "基于Cloudflare Workers的IOL（人工晶体）度数计算API，提交JSON参数即可获取Barrett Universal II公式计算结果",
            "version": "1.0.0",
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
                    "description": "提交眼睛参数JSON，基于Barrett Universal II公式计算人工晶体度数。至少提供右眼或左眼其中一组参数。k_index使用真实角膜等效折射率表示，发送给Barrett站点时会转换为其表单值。",
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
                                                    "description": "前房深度（mm），默认3.0",
                                                    "example": 3.0,
                                                },
                                                "Refraction": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "目标屈光度（D），默认0",
                                                    "example": 0,
                                                },
                                                "LenThickness": {
                                                    "type": "string",
                                                    "description": "晶体厚度（可选）",
                                                },
                                                "WTW": {
                                                    "type": "string",
                                                    "description": "白到白距离（可选）",
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
                                                    "description": "前房深度（mm），默认3.0",
                                                    "example": 3.0,
                                                },
                                                "Refraction": {
                                                    "type": "number",
                                                    "format": "float",
                                                    "description": "目标屈光度（D），默认0",
                                                    "example": 0,
                                                },
                                                "LenThickness": {
                                                    "type": "string",
                                                    "description": "晶体厚度（可选）",
                                                },
                                                "WTW": {
                                                    "type": "string",
                                                    "description": "白到白距离（可选）",
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
                                            "description": "IOL晶体型号名称（可选），如 Alcon SN60WF",
                                        },
                                        "k_index": {
                                            "type": "number",
                                            "format": "float",
                                            "enum": [1.3375, 1.332],
                                            "default": 1.3375,
                                            "description": "角膜等效折射率。1.3375会转换为Barrett表单值337.5，1.332会转换为332。",
                                            "example": 1.3375,
                                        },
                                    },
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
                                    "example": {
                                        "success": True,
                                        "data": {
                                            "right_eye": {
                                                "iol_options": [
                                                    {
                                                        "iol_power": "20.0",
                                                        "optic": "TECNIS ZCB00",
                                                        "refraction": "-0.25",
                                                        "recommended": True,
                                                    }
                                                ]
                                            },
                                            "left_eye": {
                                                "iol_options": [
                                                    {
                                                        "iol_power": "20.5",
                                                        "optic": "TECNIS ZCB00",
                                                        "refraction": "-0.12",
                                                        "recommended": True,
                                                    }
                                                ]
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
                        "提交平坦/陡峭角膜曲率及轴位、眼轴、ACD、晶体厚度、"
                        "WTW 等参数，返回散光晶体型号、球镜度数和建议轴位。"
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
                        "flat_k",
                        "flat_axis",
                        "steep_k",
                        "steep_axis",
                        "AL",
                        "lens_thickness",
                        "WTW",
                    ],
                    "properties": {
                        "flat_k": {"type": "number", "minimum": 30, "maximum": 60},
                        "flat_axis": {"type": "number", "minimum": 0, "maximum": 180},
                        "steep_k": {"type": "number", "minimum": 30, "maximum": 60},
                        "steep_axis": {"type": "number", "minimum": 0, "maximum": 180},
                        "AL": {"type": "number", "minimum": 12, "maximum": 38},
                        "ACD": {"type": "number", "default": 3.0},
                        "target_refraction": {"type": "number", "default": 0},
                        "incision_sia": {"type": "number", "default": 0},
                        "incision_location": {"type": "number", "default": 0},
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
