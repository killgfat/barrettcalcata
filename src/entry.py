import json
from workers import WorkerEntrypoint, Response
from urllib.parse import urlparse
from calculate import calculate_iol, get_hello_message
from webui import get_webui_page
from worker_ai import WorkerAI

from api import APIHandler
from docs import get_swagger_ui_html, get_redoc_html, get_openapi_json


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # 获取请求路径
        path = urlparse(request.url).path

        # 处理不同的路由
        if path in ["/", "/index.html"]:
            return Response(
                get_webui_page(), headers={"Content-Type": "text/html; charset=utf-8"}
            )
        elif path == "/hello":
            return await self.handle_hello()
        elif path == "/api":
            return await self.handle_api(request)
        elif path == "/api/extract":
            return await self.handle_extract(request)
        elif path == "/api/calculate":
            return await self.handle_calculate(request)
        elif path == "/docs":
            return await self.handle_docs()
        elif path == "/redoc":
            return await self.handle_docs_redoc()
        elif path == "/openapi.json":
            return await self.handle_openapi_json()

        else:
            return Response.json(
                {
                    "error": "Not Found",
                    "message": f"路径 {path} 不存在",
                    "available_endpoints": [
                        "GET / - Web UI界面",
                        "GET /hello - 返回问候消息",
                        "POST /api - 统一API入口，自动检测请求类型",
                        "POST /api/extract - 从图片提取IOL数据",
                        "POST /api/calculate - 执行IOL计算",
                        "GET /docs - API文档页面（Swagger UI）",
                        "GET /redoc - API文档页面（ReDoc）",
                        "GET /openapi.json - OpenAPI规范JSON",
                    ],
                },
                status=404,
            )

    async def handle_hello(self):
        """处理问候请求"""
        return Response.json(
            {
                "message": get_hello_message(),
                "service": "IOL Calculator API",
                "version": "1.0.0",
            }
        )

    async def handle_api(self, request):
        """统一API入口，自动检测请求类型并执行相应功能"""
        api_handler = APIHandler(self.env)
        result, status_code = await api_handler.handle_api(request)
        return Response.json(result, status=status_code)

    async def handle_extract(self, request):
        """处理图片提取请求"""
        api_handler = APIHandler(self.env)
        result, status_code = await api_handler.handle_extract(request)
        return Response.json(result, status=status_code)

    async def handle_calculate(self, request):
        """处理IOL计算请求"""
        api_handler = APIHandler(self.env)
        result, status_code = await api_handler.handle_calculate(request)
        return Response.json(result, status=status_code)

    async def handle_docs(self):
        """处理API文档页面请求（Swagger UI）"""
        return Response(
            get_swagger_ui_html(), headers={"Content-Type": "text/html; charset=utf-8"}
        )

    async def handle_docs_redoc(self):
        """处理API文档页面请求（ReDoc）"""
        return Response(
            get_redoc_html(), headers={"Content-Type": "text/html; charset=utf-8"}
        )

    async def handle_openapi_json(self):
        """处理OpenAPI规范JSON请求"""
        openapi_spec = get_openapi_json()
        return Response.json(openapi_spec)
