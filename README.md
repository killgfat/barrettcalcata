# IOL Calculator

基于 Cloudflare Workers 的人工晶体（IOL）度数计算服务。支持 Barrett Universal II、
SRK/T、Hoffer Q、Holladay 1、Haigis、Castrop 的球镜计算，Barrett Toric 的散光计算，以及从
IOL Master 报告图片识别生物测量参数。

在线演示：<https://barrettcalcata.killgfat.com>（仅功能体验，不保证可用性，
不可作为临床决策依据）

## 快速开始

    uv sync
    npm run dev                 # 本地开发
    uv run pytest tests/        # 测试
    ruff check src tests

### 部署

[![Deploy to Cloudflare Workers](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/killgfat/barrettcalcata)

或手动部署：

    npx wrangler secret put OPENAI_API_KEY   # 可选，仅 AI 识图需要
    npm run deploy

默认使用 Git 跟踪的 `wrangler.jsonc`；私有配置与密钥不要提交。

## Agent Skill

仓库自带 [agent skill](skills/iol-calculator/SKILL.md)，供 Claude Code、Codex、
Cursor 等编码代理直接调用本 API。

    npx skills add killgfat/barrettcalcata

目标实例由 `IOL_API_BASE` 决定，未设置时指向在线演示：

    export IOL_API_BASE=https://your-own-worker.example.com

技能内含 `scripts/iol.py`（仅标准库的 CLI）与 304 款 ULIB 型号的静态常数表。

## 使用

浏览器打开首页即可使用：选择非散光或散光模式与计算公式，填写眼部参数后计算。
结果会给出推荐度数、候选表、实际使用的常数、置信度与警告。

晶体型号搜索框的候选随公式变化：Barrett 用官网型号（18 项），其余公式用内置
ULIB 快照（304 项）。**留空表示不指定型号**，直接用下方的 A 常数；选中型号后
由型号决定常数，请求里同类的 A 常数 / Haigis 三常数 / Hoffer Q pACD /
Holladay 1 SF 不再生效。
Holladay 1 的常数是 SF：选中型号时用该晶体的优化 SF，SF 输入框会锁定并
显示「由所选晶体决定」；不选型号时手填 SF，留空则按 `SF = 0.5663×A - 65.60`
换算，结果会标低置信度并给出警告。

Castrop 是例外：它的常数是 C/H/R，ULIB 快照（2016 停更）里没有这三列，
所以界面不显示型号选择器（服务端对 `?formula=castrop` 返回空列表）。
C/H/R 请从 [IOLCon](https://iolcon.org) 的 `Castrop(C / H / R)` 列抄入；
三项都留空时退回论文优化初值 C=0.40/H=0.00/R=0.00 并标为低置信度。如果手上
已有 IOLCon 算好的 ELP，也可以直接填 ELP，跳过 C/H 推导。

需要程序化调用时见站点的 `/docs`。

## AI 配置

仅 AI 识图需要，IOL 计算本身不依赖 OpenAI：

| 变量 | 说明 |
|---|---|
| OPENAI_API_KEY | 通过 Wrangler Secret 配置 |
| OPENAI_API_URL | OpenAI 兼容接口地址 |
| OPENAI_MODEL | 具备视觉能力的模型；跟踪配置使用 gpt-5 |

在线 Barrett/Toric 与 AI 识图会调用外部服务。请勿提交不必要的患者身份信息。
本服务不持久化患者数据。

## 数据来源与署名

### ULIB 优化晶体常数

内置快照来自 **ULIB（User Group for Laser Interference Biometry）**，
作者 Wolfgang Haigis 博士（德国维尔茨堡大学），原始页面
<http://www.ocusoft.de/ulib/c1.htm>，最后修订 2016-10-31，收录 304 款晶体。
2016 年后停止更新，后继平台为 [IOLCon](https://iolcon.org)。

- 快照位于 `src/formula/data_ulib.py`，Barrett 型号映射位于
  `src/formula/data_model_map.py`；
- 只收录原表的**事实性数值**（型号名、名义 A、Haigis a0/a1/a2、Hoffer Q pACD、
  Holladay 1 SF、SRK/T A、SRK II A、样本量），剔除文献编号列与别名对照表；
- Holladay 1 SF 直接用于 `model=holladay1` 的计算，见
  [公式实现说明 4a 节](docs/formulas.md#4a-holladay-1)；
- 运行时零网络、零文件读取，更新需重新生成并经评审；
- 数据源自 ZEISS IOLMaster 采集的临床数据，样本量小于 50 的条目为 preliminary；
- 常数与型号绑定，**不能用 A 常数线性换算替代**，详见
  [公式实现说明 7.5 节](docs/formulas.md#75-不要用-a-常数换算替代优化常数)。

原页面未附版权声明。本项目仅收录不受著作权保护的事实性数值，不复制其汇编
编排。若权利人认为收录方式不妥，请通过 issue 联系，核实后调整或移除。

Castrop 的 C/H/R 与 ELP **不内置**：ULIB 快照停更于 2016 年，而 Castrop 是
2021 年发表的公式，表里没有这三列。需要时由调用方从 IOLCon 抄入
`castrop_constants`，或直接给 `castrop_elp`；两者都没有时用论文常数优化的
初值 C=0.40/H=0.00/R=0.00 兜底并标为低置信度。本服务不抓取 IOLCon 数据。

### Barrett 离线校准数据

Barrett Offline 的开发期校准使用
[ekrbye/barrett-uii-data](https://github.com/ekrbye/barrett-uii-data)
（作者 Yishen Wang、Li Li，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)）。

该数据是官方计算器的输入/输出样本，不含官方 ELP 或系数；本项目对其做了等效
ELP 反演、回归拟合与误差分析，仅用于 Barrett Offline。**Worker 运行时不会
调用该仓库，也不部署这些数据文件。** 详见
[校准报告](docs/calibration_report.md)。

生成校准报告（需 numpy）：

    python scripts/calibrate_offline.py               # 联网下载样本
    python scripts/calibrate_offline.py --no-download # 使用本地已有数据

### 第三方数据一览

| 数据 | 来源 | 用途 | 许可 / 声明 |
|---|---|---|---|
| ULIB 常数快照 | [ocusoft.de/ulib](http://www.ocusoft.de/ulib/c1.htm)，2016-10-31 | 非 Barrett 公式常数 | 见上 |
| Castrop 常数与 ELP | 调用方自行输入（来源通常为 [IOLCon](https://iolcon.org)） | Castrop 公式 | 不内置、不抓取；缺省用论文初值 |
| Barrett 校准样本 | [ekrbye/barrett-uii-data](https://github.com/ekrbye/barrett-uii-data) | 仅开发期校准 | CC BY 4.0 |
| 在线 Barrett/Toric 结果 | [calc.apacrs.org](https://calc.apacrs.org/barrett_universal2105/) | 在线模式转发 | 运行时调用，不存储 |

## 重要限制

- Barrett Offline 是本地近似实现，不是官方公式的逐系数复刻，不保证与官网一致；
- 各公式独立实现，结果不同不代表可以相互校准；
- 结果受生物测量、晶体常数、目标屈光度与特殊眼情况影响，**必须人工复核**；
- ULIB 快照停留在 2016-10-31，之后上市的晶体不在其中，数值未经二次临床验证；
- 未建立映射的晶体，常数由 A 常数按厂商标准关系换算，与优化常数可能相差
  0.5 D 以上；
- 本服务不替代专业眼科判断。

## 文档

- [公式实现、常数与参考文献](docs/formulas.md)
- [Barrett Offline 校准方法与误差](docs/calibration_report.md)

## 免责声明

计算结果仅供研究与估算参考，不构成医疗建议。临床应用中请由专业眼科医生核对
测量数据、晶体常数与计算结果。
