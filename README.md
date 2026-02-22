# Barrett IOL Calculator

基于 Cloudflare Workers 的人工晶体（IOL）度数计算服务，支持 Barrett Universal II 公式计算，并集成 AI 视觉识别功能，可从 IOL Master 测量报告图片中自动提取参数。

## 在线 Demo

我们提供了一个在线演示版本，可直接体验所有功能：

🔗 **https://barretcalcata.killgfat.com**

> **注意**：Demo 环境资源有限，仅用于功能体验和测试。请勿在生产环境中使用，生产部署请参考下方一键部署指南。

## 主要功能

- **IOL 度数计算**：基于 Barrett Universal II 公式，支持单眼或双眼计算，可配置 A 常数、目标屈光度、硅油眼矫正等参数
- **AI 识图填充**：上传 IOL Master 晶体单图片，自动识别并填充患者姓名、A 常数及双眼 AL、K1、K2、ACD 等参数，采用三次并发识别 + 多数决机制提升准确性
- **Web UI**：内置可视化操作界面，支持手动输入与图片上传两种方式
- **OpenAPI 接口**：提供标准 OpenAPI 规范，可通过 `/docs`（Swagger UI）或 `/openapi.json` 查看完整接口文档

## 环境变量

以下变量均为可选，仅在使用 AI 识图功能时需要配置。

| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | API 密钥，通过 `wrangler secret put OPENAI_API_KEY` 设置 |
| `OPENAI_API_URL` | OpenAI 兼容 API 的 Base URL（默认 `https://api.openai.com/v1`） |
| `OPENAI_MODEL` | 使用的模型名称（默认 `gpt-4-vision-preview`） |

> **注意**：AI 识图功能使用 OpenAI 兼容 API，需接入具备**视觉能力的 VLM**（Vision Language Model），普通 LLM 不支持图片输入。不配置以上变量时，IOL 计算功能仍可正常使用。

## 快速部署

### 一键部署（推荐）

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/killgfat/barrettcalcata)

> 请自行在部署界面的高级选项中配置 `OPENAI_API_KEY` 的机密变量

### 手动部署

```bash
# 安装依赖
uv sync

# 设置 API 密钥（可选，仅 AI 识图功能需要）
npx wrangler secret put OPENAI_API_KEY

# 在 wrangler.jsonc 中配置 OPENAI_API_URL 和 OPENAI_MODEL（可选）

# 部署
uv run pywrangler deploy
```

## 本地开发

```bash
uv sync
uv run pywrangler dev
```

## 免责声明

计算结果仅供参考，实际临床应用请咨询专业眼科医生。
