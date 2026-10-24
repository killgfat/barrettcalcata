# Barrett IOL Calculator

基于 Cloudflare Workers 的人工晶体（IOL）度数计算服务，支持 Barrett Universal II 公式计算，并集成 AI 视觉识别功能，可从 IOL Master 测量报告图片中自动提取参数。

## 在线 Demo

我们提供了一个在线演示版本，可直接体验所有功能：

🔗 **https://barrettcalcata.killgfat.com**

> **注意**：Demo 环境资源有限，仅用于功能体验和测试。请勿在生产环境中使用，生产部署请参考下方一键部署指南。

## 主要功能

- **IOL 度数计算**：基于 Barrett Universal II 公式，支持单眼或双眼计算，可配置 A 常数、目标屈光度、硅油眼矫正等参数
- **散光晶体计算**：独立的 Barrett Universal II Toric 模块，支持平坦/陡峭 K 值及轴位、切口 SIA、晶体厚度和 WTW，并返回晶体型号与建议植入轴位
- **AI 识图填充**：上传 IOL Master 晶体单图片，自动识别并填充患者姓名、A 常数及双眼 AL、K1、K2、ACD 等参数，采用三次并发识别 + 多数决机制提升准确性
- **Web UI**：内置可视化操作界面，支持手动输入与图片上传两种方式
- **OpenAPI 接口**：提供标准 OpenAPI 规范，可通过 `/docs`（Swagger UI）或 `/openapi.json` 查看完整接口文档

### Barrett Universal II Toric API

散光计算使用独立端点 `POST /api/calculate-toric`，至少提交 `right_eye` 或 `left_eye` 一组参数。为与普通 Barrett 模块统一，每只眼睛使用 `K1`、`K1Axis`、`K2`、`K2Axis`、`AL`、`lens_thickness` 和 `WTW`；其中 `K1`/`K1Axis` 为平坦子午线及轴位，`K2`/`K2Axis` 为陡峭子午线及轴位。旧版 `flat_k`、`flat_axis`、`steep_k`、`steep_axis` 仍兼容；`ACD`、目标屈光度、切口 SIA 与切口位置缺省为 `3.00`、`0`、`0` 和 `0`。成功响应中的 `axis_image.source_url` 指向 Barrett 官方轴位背景图，`fallback_url` 是官方资源不可用时使用的自包含轴位图。

```json
{
  "right_eye": {
    "K1": 41.50,
    "K1Axis": 84,
    "K2": 43.85,
    "K2Axis": 174,
    "AL": 24.43,
    "ACD": 3.25,
    "target_refraction": 0,
    "incision_sia": 0,
    "incision_location": 10,
    "lens_thickness": 4.21,
    "WTW": 11.80
  },
  "a_constant": 119.30,
  "k_index": 1.3375,
  "cylinder_mode": "-ve"
}
```

### 模块命名

- `src/barrett_calculate.py`：Barrett Universal II 普通晶体计算（官网在线路径）
- `src/barrett_offline.py`：Barrett Universal II 离线近似计算核心（零网络）
- `src/barrett_toric_calculate.py`：Barrett Universal II Toric 散光晶体计算与轴位图数据
- `src/barrett_iol_models.py`：Barrett 晶体型号与常数同步
- `src/barrett_config.py`：普通和散光计算共用的 K-index 配置
- `scripts/calibrate_offline.py`：一次性离线校准脚本（生成 docs/calibration_report.md）

## 离线模式

`POST /api/calculate` 现在支持 `mode` 开关：

- `mode = "offline"`（默认）：使用 `src/barrett_offline.py` 本地计算，零网络调用。
  输入仍是 `right_eye` / `left_eye` / `a_constant` / `k_index`，返回结构与在线模式兼容
  （`iol_options` 可直接被 Web UI 使用），并额外返回 `mode`、`model`、
  `confidence`、`warnings`、`elp` 等字段。
- `mode = "online"`：显式走原有的 Barrett 官网路径，行为与返回结构保持不变。

示例：

```json
{
  "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 3.2, "Refraction": 0},
  "a_constant": 119.3,
  "mode": "offline"
}
```

### 重要限制（请务必阅读）

1. 官方 Barrett Universal II 的 ELP 预测使用**未公开**的三阶多项式回归和厚透镜
   光线追迹；官网计算器不对应任何可公开复刻的单页公式。
2. 本仓库的离线实现 = **Gaussian 聚散度核心**（Barrett/Fyodorov 理论公式）
   + **由公开 CC-BY-4.0 网格反演的 ELP 近似式**。它**不是**官方公式的逐系数复刻，
   也不等价于官网结果。
3. 任务书中引用的 2021 年 Clin Exp Ophthalmol 论文在 PubMed / Crossref / Wiley
   目录中均无法检索到（检索记录见校准报告第 3 节），因此代码与文档不声称按该论文
   实现。真实可考的 Barrett 理论公式文献是 1993 年 JCRS 论文（PMID 8271166）。
4. 校准报告：[`docs/calibration_report.md`](docs/calibration_report.md)
   （逐点偏差、AL×K 分桶、超包络样本、留一基线验证）。
   原始对数数据：`docs/calibration_grid.csv`、`docs/calibration_outliers.csv`。
5. 适用域：`AL 22-26 mm`、`K 38-48 D`。超出时仍会计算，但结果的
   `confidence` 为 `LOW_CONFIDENCE` 并给出 `warnings`；短眼/长眼/极端 K
   建议显式使用 `mode="online"` 复核。
6. 纯 ALK（只给 AL+K）与官方五参数全量版的差异明显大于五参数离线模式；
   报告中的分桶表给出了具体包络。临床决策前必须人工复核。

### 重新生成校准报告

```bash
# 需要 numpy（仅校准脚本使用；运行时模块只用标准库）
python scripts/calibrate_offline.py
# 不联网时复用 ./data/barrett-uii-data
python scripts/calibrate_offline.py --no-download
```

数据通过 `ghfast.top` 镜像拉取到 `./data/`（该目录不提交）。脚本会真实读取
数据、真实计算偏差，并在 stdout 打印
`>>> OFFLINE BUII DONE maxΔ=... p95=... n=...` 哨兵。

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
