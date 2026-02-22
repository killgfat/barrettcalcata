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
            "description": "基于Cloudflare Workers的IOL（人工晶体）计算器API，支持AI图像识别提取医疗数据",
            "version": "1.0.0",
            "contact": {
                "name": "API Support",
                "url": "https://barrettcalcata.killgfat.com",
            },
        },
        "tags": [
            {"name": "基础功能", "description": "基础API功能"},
            {"name": "图片处理", "description": "AI图像识别和数据处理"},
            {"name": "IOL计算", "description": "人工晶体度数计算"},
        ],
        "paths": {
            "/hello": {
                "get": {
                    "tags": ["基础功能"],
                    "summary": "获取问候消息",
                    "description": "返回简单的问候消息，用于测试API是否正常工作",
                    "responses": {
                        "200": {
                            "description": "成功响应",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "message": "Hello World!",
                                        "service": "IOL Calculator API",
                                        "version": "1.0.0",
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api": {
                "post": {
                    "tags": ["基础功能"],
                    "summary": "统一API入口",
                    "description": "自动检测请求类型并执行相应功能：包含image字段则执行图片识别和计算流程，包含right_eye或left_eye字段则执行IOL计算",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "image": {
                                            "type": "string",
                                            "format": "base64",
                                            "description": "Base64编码的图片数据（用于图片识别和计算流程）",
                                        },
                                        "right_eye": {
                                            "type": "object",
                                            "description": "右眼参数（用于IOL计算）",
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
                                                    "description": "屈光度（D），默认0",
                                                    "example": 0,
                                                },
                                                "LenThickness": {
                                                    "type": "string",
                                                    "description": "晶体厚度",
                                                },
                                                "WTW": {
                                                    "type": "string",
                                                    "description": "白到白距离",
                                                },
                                            },
                                            "required": ["AL", "K1", "K2"],
                                        },
                                        "left_eye": {
                                            "type": "object",
                                            "description": "左眼参数（用于IOL计算）",
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
                                                    "description": "屈光度（D），默认0",
                                                    "example": 0,
                                                },
                                                "LenThickness": {
                                                    "type": "string",
                                                    "description": "晶体厚度",
                                                },
                                                "WTW": {
                                                    "type": "string",
                                                    "description": "白到白距离",
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
                                            "description": "患者姓名",
                                        },
                                    },
                                },
                                "examples": {
                                    "图片识别和计算": {
                                        "summary": "图片识别和计算流程",
                                        "value": {"image": "base64编码的图片数据..."},
                                    },
                                    "IOL计算": {
                                        "summary": "仅执行IOL计算",
                                        "value": {
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
                                            "patient_name": "张三",
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "成功响应",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {
                                                "type": "boolean",
                                                "description": "操作是否成功",
                                            },
                                            "data": {
                                                "type": "object",
                                                "description": "返回的数据",
                                            },
                                            "message": {
                                                "type": "string",
                                                "description": "操作消息",
                                            },
                                            "error": {
                                                "type": "string",
                                                "description": "错误类型（仅当success为false时）",
                                            },
                                            "status_history": {
                                                "type": "array",
                                                "description": "处理状态历史",
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "400": {"description": "请求参数错误"},
                        "405": {"description": "请求方法不允许"},
                        "415": {"description": "不支持的媒体类型"},
                        "500": {"description": "服务器内部错误"},
                    },
                }
            },
            "/api/extract": {
                "post": {
                    "tags": ["图片处理"],
                    "summary": "从图片提取IOL数据",
                    "description": "使用AI图像识别技术从医疗图片中提取IOL计算所需的数据",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "image": {
                                            "type": "string",
                                            "format": "base64",
                                            "description": "Base64编码的图片数据",
                                        }
                                    },
                                    "required": ["image"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "成功提取数据",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "success": True,
                                        "data": {
                                            "patient_name": "张三",
                                            "a_constant": 119.3,
                                            "right_eye": {
                                                "AL": 23.5,
                                                "K1": 43.5,
                                                "K2": 44.0,
                                                "ACD": 3.0,
                                            },
                                            "left_eye": {
                                                "AL": 23.3,
                                                "K1": 43.8,
                                                "K2": 44.2,
                                                "ACD": 3.0,
                                            },
                                        },
                                        "message": "图片数据提取成功",
                                        "status_history": [
                                            {
                                                "timestamp": "2025-02-19T10:30:00Z",
                                                "message": "开始处理图片",
                                            }
                                        ],
                                    }
                                }
                            },
                        },
                        "400": {"description": "缺少图片数据"},
                        "500": {"description": "图片处理失败"},
                    },
                }
            },
            "/api/calculate": {
                "post": {
                    "tags": ["IOL计算"],
                    "summary": "执行IOL计算",
                    "description": "根据提供的眼睛参数计算人工晶体度数",
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
                                                    "description": "屈光度（D），默认0",
                                                    "example": 0,
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
                                                    "description": "屈光度（D），默认0",
                                                    "example": 0,
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
                                            "description": "患者姓名",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "成功计算",
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
                        "400": {"description": "缺少必需参数"},
                        "500": {"description": "计算失败"},
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
                        "available_endpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "可用的API端点",
                        },
                    },
                },
                "SuccessResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "description": "操作是否成功"},
                        "data": {"type": "object", "description": "返回的数据"},
                        "message": {"type": "string", "description": "操作消息"},
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
                    <div class="api-description">基于Cloudflare Workers的IOL（人工晶体）计算器API，支持AI图像识别提取医疗数据</div>
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
