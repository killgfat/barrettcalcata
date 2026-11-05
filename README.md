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
- 晶体常数：内置 [ULIB](#ulib-常数数据与署名) 优化常数快照，按型号自动选用；
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

### Agent Skill

仓库内自带一个 [agent skill](skills/iol-calculator/SKILL.md)，让 Claude Code、
Codex、Cursor 等编码代理直接调用本 API 做晶体度数计算。

    npx skills add killgfat/barrettcalcata

技能指向的实例由环境变量 `IOL_API_BASE` 决定，未设置时使用
<https://barrettcalcata.killgfat.com>：

    export IOL_API_BASE=https://your-own-worker.example.com

技能自带 `scripts/iol.py`（仅标准库），也可以直接当命令行工具用：

    python3 skills/iol-calculator/scripts/iol.py calculate --file payload.json
    python3 skills/iol-calculator/scripts/iol.py models --model "AMO ZCB00"

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
| GET | /api/ulib-models | ULIB 晶体列表（供前端搜索选择） |
| GET | /docs | Swagger UI |
| GET | /openapi.json | OpenAPI 规范 |

`/api/iol-models?model=<型号>` 的查询顺序：

1. Barrett 官网型号经手工映射表查 [ULIB 常数快照](#ulib-常数数据与署名)；
2. ULIB 快照里的原始型号名；
3. 回退 Barrett 官网在线查询。

响应的 `source` 字段标明来源。ULIB 命中时返回 Haigis 三常数、
Hoffer Q pACD、Holladay 1 SF 与 SRK/T、SRK II 的 A 常数，可直接填入
计算请求，不必用 A 常数近似换算。

计算接口也有对应的常数选择规则：`model` 为 `srkt`、`hoffer_q`、
`haigis` 且 `iol_model` 能映射到 ULIB 条目时，自动采用 ULIB 的优化常数；
请求里显式提供的 `a_constant`、`hoffer_q_pacd`、`haigis_constants`
优先级更高。响应中的 `constants_source` 会说明实际使用了哪一套常数。详见
[公式实现说明第 7 节](docs/formulas.md#7-常数来源ulib-快照与-a-常数换算的边界)。

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

## ULIB 常数数据与署名

本项目内置了一份 **ULIB（User Group for Laser Interference Biometry）**
优化晶体常数快照，用于在非 Barrett 公式下按型号选用优化常数。

### 数据来源

| 项目 | 内容 |
|---|---|
| 组织 | ULIB — User Group for Laser Interference Biometry |
| 作者 | Wolfgang Haigis 博士（德国维尔茨堡大学） |
| 常数表 | <http://www.ocusoft.de/ulib/c1.htm> |
| 页面标题 | Optimized IOL Constants for the ZEISS IOLMaster |
| 最后修订 | 2016-10-31（原页面标注 "Last Revision: Oct 31, 2016 WH"） |
| 收录数量 | 304 款晶体 |
| 快照位置 | `src/formula/data_ulib.py` |
| 型号映射 | `src/formula/data_model_map.py` |

ULIB 是 IOLMaster 优化常数的原始公开来源，2016 年后停止更新；后继平台为
[IOLCon](https://iolcon.org)（Steinbeis / 萨尔大学 Langenbucher 团队）。
蔡司官方页面对此有明确说明。

### 收录了什么

快照只保留原表的**事实性数值字段**：

| 字段 | 含义 |
|---|---|
| 「name」 | 晶体型号名（保留 ULIB 原始写法，含地区后缀与正负度数标记） |
| 「nominal」 | 厂商名义 A 常数 |
| 「haigis」 | Haigis 优化三常数 a0 / a1 / a2 |
| 「pacd」 | Hoffer Q 优化 pACD（mm） |
| 「sf」 | Holladay 1 优化 Surgeon Factor |
| 「srkt」 | SRK/T 优化 A 常数 |
| 「srk2」 | SRK II 优化 A 常数 |
| 「n」 | 参与优化的临床样本量 |

### 明确没有收录什么

- 原页面的**文献编号列**（Ref，形如 「[49],[223],[224]」）——未收录；
- 原页面的**晶体别名对照表**（`identiol.htm`）——未收录；
- 页面的 HTML 结构、样式与图片——未收录。

即只取数值事实，不复制原站点的汇编编排。

### 代码中的调用点

ULIB 数据只经由下面这条链路被读取，没有其他入口：

| 位置 | 作用 |
|---|---|
| `src/formula/data_ulib.py` | 常数快照本体（固定文本，无外部依赖） |
| `src/formula/data_model_map.py` | Barrett 型号 → ULIB 条目的人工映射 |
| `src/formula/constants.py` | `lookup()` / `lookup_for_barrett_model()` 查询层 |
| `src/formula/formula.py` | `_resolve_offline_constants()` 决定是否替换常数 |
| `src/formula/iol_models.py` | `/api/iol-models` 的型号查询入口 |

**哪些公式会读 ULIB**：

| 公式 | 是否使用 ULIB 常数 |
|---|---|
| SRK/T | 是（采用优化后的 SRK/T A） |
| Hoffer Q | 是（采用优化后的 pACD） |
| Haigis / Haigis-T | 是（采用 a0 / a1 / a2 三常数） |
| Barrett 离线 / 在线 / Toric | **否**。ULIB 表内没有 Lens Factor 列，Barrett 始终使用自己的 Lens Factor 路径 |

**优先级**：请求里显式提供的 `a_constant`、`hoffer_q_pacd`、
`haigis_constants` 永远高于 ULIB 快照值，不会被静默替换。

### 运行时不联网

`src/formula/data_ulib.py` 是编译进 Worker 的固定文本块，运行时：

- 不访问 `ocusoft.de` 或任何第三方站点；
- 不读取外部文件，不依赖文件系统；
- 解析只用标准库字符串操作，无额外依赖。

更新快照需要重新生成该文件并经过代码评审，不会自动同步上游。

### Web UI 中的晶体选择

非 Barrett 公式（SRK/T、Hoffer Q、Haigis、Haigis-T）在 Web UI 里使用
**ULIB 晶体选择器**，与 Barrett 模式下的 Barrett 型号下拉相互独立：

```text
Barrett 模式     -> Barrett 官网型号下拉（18 项）
其他公式         -> 关键词搜索框 + ULIB 型号列表（304 项）
```

- 列表由 `GET /api/ulib-models` 一次性返回（约 37 KB），前端本地过滤，
  切换公式时不再产生额外请求；
- 支持空格分隔的多关键词（如 `tecnis zcb00` 唯一定位到一款）；
- 选中型号后自动填入 A 常数、Haigis a0/a1/a2 与 Hoffer Q pACD，
  这些值随请求显式提交，优先级高于后端的自动映射。

### 与 Barrett 型号的映射

Barrett 官网计算器只提供 18 个型号的快捷选择，命名体系与 ULIB 不同。
`src/formula/data_model_map.py` 对这批型号做了逐条人工对照：

- 6 条精确对应（如 `AMO ZCB00` → `AMO Tecnis 1 ZCB00`）；
- 5 条系列对应（如 `Alcon SN6AD` → `Alcon ReSTOR SN6AD1/3`）；
- 7 条明确不映射并注明原因（如 `Alcon MN60MA`，ULIB 只收录 MA60MA）。

未建立映射的型号回退到 A 常数按厂商标准关系换算，响应中会标注
`constants_source.source = "a_constant_conversion"` 并说明该值
**不是晶体优化常数**。

### 使用边界

- ULIB 常数源自使用 **ZEISS IOLMaster** 采集的临床数据，原页面明确说明
  这些常数只适用于该仪器类型；
- 样本量小于 50 的条目在原页面标注为 preliminary，查询结果会附带警告并
  降低置信度；
- 常数与晶体型号绑定，**不能用 A 常数线性换算替代**（详见
  [公式实现说明 7.5 节](docs/formulas.md#75-不要用-a-常数换算替代优化常数)）；
- 本项目不声称 ULIB 数据完整、准确或适用于任何特定临床场景。

### 权利与免责

ULIB 页面本身未附版权声明或使用条款。本项目仅收录其中不受著作权保护的
**事实性数值**（晶体型号与常数），并剔除原表的文献编号体系与别名对照表
等汇编层内容，不复制、不再分发原站点的页面或结构化数据库。

若 ULIB 的权利人认为本项目的收录方式不妥，请通过仓库 issue 联系，我们会
在核实后调整或移除相关内容。

使用者应自行确认所在地法规与临床规范，ULIB 数据仅供研究与估算参考。

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
- 内置 ULIB 常数快照停留在 2016-10-31 的版本，之后上市的晶体不在其中；
  快照中的数值未经二次临床验证。
- 未建立 Barrett 型号映射的晶体，常数由 A 常数按厂商标准关系换算得到，
  与晶体专属优化常数可能相差 0.5 D 以上。

## 文档

- [公式实现、常数与参考文献](docs/formulas.md)
- [Barrett Offline 校准方法、系数与误差](docs/calibration_report.md)

## 第三方数据来源

| 数据 | 来源 | 用途 | 许可证 / 声明 |
|---|---|---|---|
| ULIB 优化晶体常数快照 | [ocusoft.de/ulib](http://www.ocusoft.de/ulib/c1.htm)，2016-10-31 修订 | 非 Barrett 公式的晶体常数 | 见 [ULIB 常数数据与署名](#ulib-常数数据与署名) |
| Barrett 离线校准样本 | [ekrbye/barrett-uii-data](https://github.com/ekrbye/barrett-uii-data) | 仅开发期校准 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Barrett 在线/Toric 计算结果 | [calc.apacrs.org](https://calc.apacrs.org/barrett_universal2105/) | 在线模式转发 | 运行时调用，不存储 |

## 免责声明

计算结果仅供研究和估算参考，不构成医疗建议。实际临床应用请由专业眼科医生
核对测量数据、晶体常数和计算结果。
