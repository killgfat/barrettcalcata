from workers import WorkerEntrypoint, Response
from urllib.parse import urlparse
from calculate import get_hello_message
from webui import get_webui_page

from api import APIHandler
from docs import get_swagger_ui_html, get_openapi_json


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
        elif path == "/api/extract":
            return await self.handle_extract(request)
        elif path == "/api/calculate":
            return await self.handle_calculate(request)
        elif path == "/api/iol-models":
            return await self.handle_iol_models(request)
        elif path == "/docs":
            return await self.handle_docs()
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
                        "POST /api/extract - 从图片提取IOL数据",
                        "POST /api/calculate - 执行IOL计算",
                        "GET /docs - API文档页面（Swagger UI）",
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

    async def handle_iol_models(self, request):
        """处理IOL晶体型号查询请求"""
        from urllib.parse import parse_qs

        query = parse_qs(urlparse(request.url).query)
        model_name = query.get("model", [None])[0]

        api_handler = APIHandler(self.env)
        result, status_code = await api_handler.handle_iol_models(
            request, model_name=model_name
        )
        return Response.json(result, status=status_code)

    async def handle_docs(self):
        """处理API文档页面请求（Swagger UI）"""
        return Response(
            get_swagger_ui_html(), headers={"Content-Type": "text/html; charset=utf-8"}
        )

    async def handle_openapi_json(self):
        """处理OpenAPI规范JSON请求"""
        openapi_spec = get_openapi_json()
        return Response.json(openapi_spec)
