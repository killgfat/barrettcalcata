# IOL Calculator

基于 Cloudflare Workers 的人工晶体（IOL）计算服务。支持 Barrett Universal II、
SRK/T、Hoffer Q、Haigis，以及 Barrett Toric 在线计算；也可通过 AI 识别
IOL Master 报告图片并填充生物测量参数。

## 在线演示

https://barrettcalcata.killgfat.com

演示环境仅用于功能体验，不保证可用性，也不应作为临床决策依据。

## 功能

- 普通 IOL：单眼/双眼计算、目标屈光度、0.5 D 候选度数表；
- 多种公式：Barrett 本地或在线，SRK/T、Hoffer Q、Haigis 本地计算；
- Toric：Barrett 官网散光晶体计算与建议植入轴位；
- AI 识图：提取姓名、A 常数及 AL、K1、K2、ACD 等报告字段；
- Web UI 与 OpenAPI：浏览器直接使用，或通过 JSON API 集成。

公式原理、参数差异和限制见 **[公式实现说明](docs/formulas.md)**。

## 快速开始

### 本地开发

    uv sync
    npm run dev

打开终端显示的本地地址即可使用 Web UI。

### 测试

    uv run pytest tests/
    uv run ruff check src tests
    uv run ruff format --check src tests

## 快速部署

### 一键部署（推荐）

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/killgfat/barrettcalcata)

> 部署后在 Cloudflare 控制台的高级选项中配置 `OPENAI_API_KEY` 机密变量。

### 手动部署

    # 安装依赖
    uv sync

    # 设置 API 密钥（可选，仅 AI 识图功能需要）
    npx wrangler secret put OPENAI_API_KEY

    # 部署
    npm run deploy

默认使用 Git 跟踪的 `wrangler.jsonc`。私有 Cloudflare 配置和密钥不应提交到仓库。

## 使用方式

### Web UI

首页选择非散光或散光模式。非散光模式可选择计算公式；Barrett 支持在线和本地，
其余公式仅本地计算。Web UI 默认显式选择 Barrett 在线模式。

结果会显示实际公式、执行方式、常数、ELP、使用/忽略的输入、置信度和警告。

### 普通 IOL API

请求 POST /api/calculate。新客户端使用 model 指定计算模型：

| model | 含义 | ACD、LT、WTW |
|---|---|---|
| barrett_ii_offline | Barrett 本地近似 | 可选；缺失时给出警告 |
| barrett_ii | Barrett 官网在线 | 按官网适配器转发 |
| srkt | SRK/T 本地 | 不使用 |
| hoffer_q | Hoffer Q 本地 | 不使用 |
| haigis | Haigis 本地 | 使用 ACD；不使用 LT、WTW |

每眼必填 AL、K1、K2；可选 ACD、Refraction、LenThickness、WTW。
目标屈光度字段为 Refraction，默认 0。Haigis 可通过 haigis_constants
直接传入设备或晶体库的 a0/a1/a2。

示例：

    {
      "model": "barrett_ii_offline",
      "a_constant": 119.30,
      "k_index": 1.3375,
      "right_eye": {
        "AL": 23.50,
        "K1": 43.50,
        "K2": 44.00,
        "ACD": 3.20,
        "Refraction": 0,
        "LenThickness": 4.60,
        "WTW": 11.90
      }
    }

同时提供 formula/mode 与 model 时，以 model 为准。
完整请求、响应和 Toric 示例见 /docs 或 /openapi.json。

## 主要端点

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | / | Web UI |
| POST | /api/calculate | 普通 IOL 计算 |
| POST | /api/calculate-toric | Barrett Toric 在线计算 |
| POST | /api/extract | AI 识别 IOL Master 报告 |
| GET | /api/iol-models | 晶体型号与常数查询 |
| GET | /docs | Swagger UI |
| GET | /openapi.json | OpenAPI 规范 |

## AI 配置

只有 AI 识图需要以下环境变量，IOL 计算本身不依赖 OpenAI：

| 变量 | 说明 |
|---|---|
| OPENAI_API_KEY | 通过 Wrangler Secret 配置 |
| OPENAI_API_URL | OpenAI 兼容接口地址 |
| OPENAI_MODEL | 具备视觉能力的模型；跟踪配置使用 gpt-5 |

未配置 AI 时，手动输入和公式计算仍可使用。

在线 Barrett/Toric 和 AI 识图会调用外部服务。请勿提交不必要的患者身份信息；
使用 AI 时还应评估所配置模型服务的数据政策。本服务不设计患者数据持久化。

## Barrett 校准数据与署名

Barrett Offline 的开发期校准和验证使用
**[ekrbye/barrett-uii-data](https://github.com/ekrbye/barrett-uii-data)**，
作者为 Yishen Wang、Li Li，许可证为
**[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**。

需要明确：

- 数据是官方在线计算器的输入/输出样本，不直接包含官方 ELP 或其系数；
- 本项目对样本进行了等效 ELP 反演、回归拟合和误差分析；
- 数据只用于 Barrett Offline，不用于拟合 SRK/T、Hoffer Q 或 Haigis；
- **Worker 运行时不会调用该仓库，也不读取或部署这些数据文件。**

详见 [公式实现说明](docs/formulas.md) 和
[Barrett 离线校准报告](docs/calibration_report.md)。

生成校准报告：

    # 仅开发期校准需要 numpy
    python scripts/calibrate_offline.py

    # 已有本地数据、不联网重新下载时
    python scripts/calibrate_offline.py --no-download

## 重要限制

- Barrett Offline 是本地近似实现，不是官方 Barrett Universal II 的逐系数复刻，
  也不保证与官网结果一致。
- 各公开公式独立实现，公式之间结果不同并不代表可以相互校准。
- 计算结果会受生物测量、晶体常数、目标屈光度和特殊眼情况影响；
  本地结果必须人工复核。
- 本项目不提供患者数据存储，也不替代专业眼科判断。

## 文档

- [公式实现、常数与参考文献](docs/formulas.md)
- [Barrett Offline 校准方法、系数与误差](docs/calibration_report.md)

## 免责声明

计算结果仅供研究和估算参考，不构成医疗建议。实际临床应用请由专业眼科医生
核对测量数据、晶体常数和计算结果。
