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

- `src/formula/formula.py`：唯一公式调度入口（能力检查、单双眼编排、结果组装）
- `src/formula/types.py`：`EyeInput` / `CalculationRequest` / `ToricCalculationRequest` / 能力声明
- `src/formula/common.py`：通用输入校验、适用域、取整与候选表
- `src/formula/barrett.py`：Barrett Universal II 本地近似核心（零网络）
- `src/formula/barrett_online.py`：Barrett Universal II 普通晶体官网在线路径
- `src/formula/barrett_toric.py`：Barrett Universal II Toric 散光晶体计算与轴位图数据
- `src/formula/iol_models.py`：Barrett 晶体型号与常数同步
- `src/formula/config.py`：普通和散光计算共用的 K-index 配置
- `src/formula/srkt.py`、`hoffer_q.py`、`haigis.py`：三个独立本地公式实现
- `scripts/calibrate_offline.py`：一次性离线校准脚本（生成 docs/calibration_report.md）

## 离线模式

Web UI 顶部的「公式」选择器可在 **Barrett Universal II / Hoffer Q / SRK/T /
Haigis** 之间切换；选中 Barrett 时还会出现「执行方式」开关（在线 / 本地，默认
本地），其余三个公式一律本地计算，不提供在线选项。散光（Toric）模式仍由独立的
Barrett 官网接口计算，不受公式选择影响。

`POST /api/calculate` 通过 `formula` 与 `mode` 两个参数表达同样的选择：

- `mode = "offline"`（默认）：本地计算，零网络调用；Barrett 走
  `src/formula/barrett.py` 的近似核心，其余公式走 `src/formula/`。
  输入仍是 `right_eye` / `left_eye` / `a_constant` / `k_index`，返回结构与在线模式兼容
  （`iol_options` 可直接被 Web UI 使用），并额外返回 `formula`、`formula_label`、
  `mode`、`model`、`confidence`、`warnings`、`elp`、`formula_capabilities` 等字段。
  每只眼还返回 `provided_inputs`、`used_inputs`、`ignored_inputs`，明确哪些输入
  实际参与计算、哪些被公式忽略。
- `mode = "online"`：显式走原有的 Barrett 官网路径，行为与返回结构保持不变；
  该选项只对 `formula = "barrett"` 有效，其他公式传 `online` 会被拒绝。
- `formula = "barrett" | "hoffer_q" | "srkt" | "haigis"`（默认 `barrett`）：
  选择本地公式实现，详见下文「本地公式实现与引用」。响应 `data` 中新增
  `formula`、`formula_label`、`mode`，每只眼的 `iol_options` 结构保持不变。

**ACD 缺省处理**：API 不再为所有公式统一填充 `ACD=3.00`。未提供时：
Barrett 只用实际提供的参数近似 ELP 并给出 warning；SRK/T 与 Hoffer Q 本来就
不使用实测 ACD；Haigis 使用 3.20 mm 并标记 `ACD_defaulted`、降为
`LOW_CONFIDENCE`；在线 Barrett 由官网适配器沿用 3.00 mm 并在 `used_inputs`
中标记。

示例：

```json
{
  "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0, "ACD": 3.2, "Refraction": 0},
  "a_constant": 119.3,
  "formula": "barrett",
  "mode": "offline"
}
```

### 重要限制（请务必阅读）

1. 官方 Barrett Universal II 的 ELP 预测使用**未公开**的三阶多项式回归和厚透镜
   光线追迹；官网计算器不对应任何可公开复刻的单页公式。
2. 本仓库的离线实现 = **Gaussian 聚散度核心**（Barrett/Fyodorov 理论公式）
   + **由公开 CC-BY-4.0 网格反演的 ELP 近似式**。它**不是**官方公式的逐系数复刻，
   也不等价于官网结果。
   `ekrbye/barrett-uii-data` 只提供官方在线计算器的输入与输出样本，**不直接提供
   官方 ELP 或其预测系数**。本项目的 ELP 是在当前聚散度/薄透镜模型下，由这些
   样本反演得到的**等效 ELP**，再经回归拟合形成固定近似式；不能将其解释为
   官方 Barrett Universal II 内部使用的 ELP。
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
   按题面的 mean≈0.03 D / SD 0.12-0.18 D 合格线，纯 ALK 版 SD≈0.34 D
   **不达标**，五参数版 SD≈0.17 D 落在量级内但依赖 ACD/LT/WTW。
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

## 本地公式实现与引用

Web UI 的「公式」选择器与 `POST /api/calculate` 的 `formula` 参数共用同一套
本地实现（`src/formula/`）。四个公式的执行方式如下：

| formula | 展示名 | 执行方式 | 实现位置 |
|---------|--------|----------|----------|
| `barrett` | Barrett Universal II | 本地（默认）/ 官网在线 | `src/formula/barrett.py`（本地） / `src/formula/barrett_online.py`（在线） |
| `hoffer_q` | Hoffer Q | 仅本地 | `src/formula/hoffer_q.py` |
| `srkt` | SRK/T | 仅本地 | `src/formula/srkt.py` |
| `haigis` | Haigis | 仅本地 | `src/formula/haigis.py` |

### 1. Barrett Universal II

官方 Barrett Universal II 的 ELP 预测（三阶多项式 + 厚透镜光线追迹）从未公开，
官网计算器无法逐系数复刻。本实现的本地路径 = **Gaussian 聚散度核心**
（Barrett/Fyodorov 理论公式）+ **由公开 CC-BY-4.0 网格反演的 ELP 近似式**，
属于本地近似，不是官方公式复刻，也不等价于官网结果。可考的 Barrett 文献：

- Barrett GD. Intraocular lens calculation formulas for new intraocular lens
  implants. J Cataract Refract Surg. 1987;13(4):389-396.
- Barrett GD. An improved universal theoretical formula for intraocular lens
  power prediction. J Cataract Refract Surg. 1993;19(6):713-720. PMID 8271166.
- Barrett GD. Barrett Formulas: Strategies to Improve IOL Power Prediction.
  In: Intraocular Lens Calculations. Springer; 2024:577-592.
  doi:10.1007/978-3-031-50666-6_37.

需要特别说明：任务书中提到的 2021 年 Clin Exp Ophthalmol 49(7):660-670 在
PubMed / Crossref / Wiley 目录中均**无法检索**，因此代码与文档不声称按该文实现；
校准数据、逐点偏差与检索记录见
[`docs/calibration_report.md`](docs/calibration_report.md)。

### 2. SRK/T

- Retzlaff JA, Sanders DR, Kraff MC. Development of the SRK/T intraocular lens
  implant power calculation formula. J Cataract Refract Surg.
  1990;16(3):333-340.

本地实现按公开 SRK/T 计算：用 A-constant 推导术后前房深度（`0.62467*A -
68.747`，另加角膜穹隆高度与视网膜厚度修正），**WTW 不参与**计算。目标屈光度
按 Retzlaff 1990 附录公式 (10) 进入分子/分母，预测屈光度用同一附录的公式 (11)
解析反解；ELP 只由术前 AL/K/A 常数决定，不随 target 改变。

### 3. Hoffer Q

- Hoffer KJ. The Hoffer Q formula: a comparison of theoretic and regression
  formulas. J Cataract Refract Surg. 1993;19(6):700-712.
  Errata: 1994;20(6):677；2007;33(2):193.

基准前房深度由 A 常数换算：`pACD = 0.58357*A - 63.896`，再按眼轴与角膜屈光度
做前房深度修正；目标屈光度同样折算到角膜平面。

### 4. Haigis

- Haigis W, Lege B, Miller N, Schneider B. Comparison of immersion ultrasound
  biometry and partial coherence interferometry for intraocular lens
  calculation according to Haigis. Graefes Arch Clin Exp Ophthalmol.
  2000;238(9):765-773.

三常数形式 `d = a0 + a1*ACD + a2*AL`，其中 `a1 = 0.4`、`a2 = 0.1` 为经典取值，
`a0` 由 A 常数换算（`a0 = 0.62467*A - 72.434`）**只是近似起点**，不是个体化
优化结果。要获得可比的准确性，应提供术前实测 ACD，并用自有数据做最小二乘拟合
优化三常数。若已在自有数据上优化，可在请求中传
`haigis_constants: {a0, a1, a2}`；此时不再由 A 常数推导 a0，`a_constant`
会出现在 `ignored_inputs` 中，实际使用的 a0/a1/a2 记录在 `used_inputs`。

### 5. 统一免责声明

- 本地公式仅用于**估算与横向对照**，不替代官方计算器、厂家常数或临床判断。
- 适用域为 `AL 22-26 mm`、`K 38-48 D`；超出时仍返回结果，但 `confidence`
  为 `LOW_CONFIDENCE` 并附带 `warnings`，必须人工复核。
- 硬边界 `AL 12-38 mm`、`K 30-60 D` 之外直接报错；散光（Toric）计算固定走
  Barrett 官网接口，与本地公式无关。

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
