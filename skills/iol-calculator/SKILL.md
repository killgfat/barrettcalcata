---
name: iol-calculator
version: 1.0.0
slug: iol-calculator
displayName: IOL 人工晶体度数计算
summary: 调用 IOL 计算服务计算人工晶体度数：Barrett Universal II、SRK/T、Hoffer Q、Haigis 球镜，Barrett Toric / Haigis-T 柱镜与轴位，并按 ULIB 型号查优化常数。
license: Apache-2.0
homepage: https://github.com/killgfat/barrettcalcata
metadata:
  openclaw:
    requires:
      bins:
        - python3
    envVars:
      - name: IOL_API_BASE
        required: false
        description: 可选的自部署实例地址；未设置时使用默认公共实例
description: 调用 IOL 计算服务（HTTP API）来产出人工晶体度数的具体数值——Barrett Universal II、SRK/T、Hoffer Q、Haigis 的球镜计算，Barrett Toric 的柱镜与轴位，以及按晶体型号查优化常数。在下列情形使用：用户给出具体生物测量值（眼轴 AL、角膜曲率 K1/K2、前房深度 ACD、散光轴位、白到白 WTW）并问晶体该放多少度、柱镜选哪档、轴位定在哪；指定了晶体型号要查它的 A 常数 / Haigis a0a1a2 / Hoffer Q pACD；要把计算结果在几个公式之间对比或解释为什么差一档；提到自己部署了一份实例（自定义域名、IOL_API_BASE）想拿它算度数；拿着报告上的某个读数问它该怎么填进计算、会不会影响结果。反过来不需要本技能的场景：纯粹问公式原理、为什么 K 值要用 1.3375 折射率、Haigis 与 Haigis-L 的文献差异、PubMed 上有哪些研究，只是想打开 ULIB / IOLCon 网站看看，或者想让本技能从报告图片里 OCR 出数值——本服务不做图片识别，只接受用户已经读出的数值。
---

# IOL Calculator

一个 Cloudflare Workers 上运行的 IOL 计算服务，本技能封装它的 HTTP API。

## 目标实例

服务地址来自环境变量 `IOL_API_BASE`，**未设置时默认指向项目作者的部署**
`https://barrettcalcata.killgfat.com`。用户自己部署了实例时，让他们设置：

    export IOL_API_BASE=https://<their-worker-domain>

单次覆盖用 `--base`，不要为了换实例去改脚本。

## 用脚本，不要手拼 curl

调用 `scripts/iol.py`（相对本技能目录），它只用标准库，处理了 Cloudflare 对
默认 Python UA 的拦截、错误码和结果摘要。手写 curl 容易漏 User-Agent 被 403，
也容易把返回的 JSON 读错。

下面的命令都在技能目录下执行；换了工作目录就把路径补全成绝对路径：

    # 确认实例可达
    python3 scripts/iol.py health

    # 普通计算
    python3 scripts/iol.py calculate --file payload.json
    python3 scripts/iol.py calculate --json '{"model":"srkt","right_eye":{...}}'
    cat payload.json | python3 scripts/iol.py calculate

    # Barrett Toric（在线，可能被官网拒绝）
    python3 scripts/iol.py toric --json '{...}'

    # 确认实例可达
    python3 scripts/iol.py health

加 `--raw` 输出原始 JSON。

查晶体型号与常数不必调接口：`references/iol-models.md` 是内置的 304 款
ULIB 型号表，直接查表就能填 `iol_model`。这张表是 2016 年的静态快照，
要最新常数见下文「常数要新：优先 IOLCON」。要拿服务端的结果（含 Barrett
官网型号）也可以：

    curl -s "$IOL_API_BASE/api/iol-models?formula=srkt"
    curl -s "$IOL_API_BASE/api/iol-models?model=AMO%20ZCB00"

本技能不做图片 OCR：用户只给截图时，请他们先读出 AL / K1 / K2 / ACD 等
数值，再拿来计算。

## 计算请求的最小结构

`model` 必填，决定用哪套公式；至少一只眼，每眼必填 `AL`、`K1`、`K2`。

| model | 含义 | 备注 |
|---|---|---|
| `barrett_ii_offline` | Barrett 本地近似 | 用 `a_constant` 换算 Lens Factor |
| `barrett_ii` | Barrett 官网在线 | 依赖外部站点，可能失败 |
| `srkt` | SRK/T | 不读 ACD、LT、WTW |
| `hoffer_q` | Hoffer Q | 可用 `hoffer_q_pacd` 覆盖 |
| `haigis` | Haigis | 用 ACD，不读 LT、WTW |
| `haigis-toric` | Haigis-T 本地散光 | 每眼还要 `K1Axis`、`K2Axis`、实测 `ACD` |

```json
{
  "model": "srkt",
  "iol_model": "AMO ZCB00",
  "k_index": 1.3375,
  "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.5, "ACD": 3.2, "Refraction": 0}
}
```

## 常数优先级：型号赢

这是最容易搞错的地方。**声明了能命中内置 ULIB 的 `iol_model`，请求里的
`a_constant` / `hoffer_q_pacd` / `haigis_constants` 会被静默屏蔽**，
改用该型号的优化常数。响应里 `constants_source.ignored_request` 和每眼的
`ignored_inputs` 会列出被丢掉的值。

所以：

- 用户说「用某款晶体」→ 只给 `iol_model`，别同时塞 A 常数。
- 用户给了自己的 A 常数、没说型号 → 只给 `a_constant`。
- 两者都给 → 型号胜出。如果你不确定用户想要哪个，问一句，不要默认。

Barrett 系列（`barrett_ii_offline` / `barrett_ii`）不读 ULIB，只用 `a_constant`。

`haigis-toric` 的常数有两条路：请求级 `haigis_constants`，或命中 ULIB 的
`iol_model`。都没有会返回 400。

## 常数要新：优先 IOLCON

内置 ULIB 表是 2016-10-31 停更的快照。IOLCon（https://iolcon.org）是
Langen-Bucher 团队持续维护的官方优化常数库，同一型号的常数往往已经
更新过，更可靠。本技能刻意不内置它：IOLCon 条款禁止把数据复制、传播
或转交第三方，但用户自己查来用于计算是允许的。

用 `srkt` / `hoffer_q` / `haigis` / `haigis-toric`（Barrett 系列需要
`a_constant`）且报了晶体型号时，主动建议用户：

1. 自己到 iolcon.org 免费注册登录，搜索该型号；
2. 读出常数：SRK/T A、Hoffer Q pACD、Haigis a0/a1/a2、Barrett 的
   Lens Factor；
3. 用自定义参数传请求（`a_constant` / `hoffer_q_pacd` /
   `haigis_constants`），**不要同时声明 `iol_model`**——会被内置表
   静默屏蔽（见上一节）；
4. 回复里注明常数来自 IOLCon、哪个型号、什么时候取的。

用户拿不到 IOLCon 数据时再走内置表（声明 `iol_model`），但要如实
说明这是 2016 年快照，与现行优化值可能差半档以上。用户手上有厂商
手册等其他来源的常数，同样走自定义参数。

合规红线：不要把 IOLCon 的表格批量复制进代码、文档或对话；一次
计算只需要一个型号的三四个数字。

## 读懂返回

摘要里值得转述给用户的字段：

| 字段 | 含义 |
|---|---|
| `recommended_power` | 推荐度数（D） |
| `predicted_refraction` | 该度数下的预测屈光度 |
| `confidence` | `OK` / `LOW_CONFIDENCE` |
| `constants_source` | `ulib` 或 `a_constant_conversion` |
| `ignored_inputs` | 本次没用上的输入 |
| `warnings` | 必须读，经常包含范围外的提示 |

`LOW_CONFIDENCE` 和 `warnings` 要如实告诉用户，不要淡化。

## 注意事项

- **Toric 在线计算依赖 Barrett 官网**，可能返回「官网拒绝自动请求」。
  遇到这个不要反复重试，直接说明并建议用 `haigis-toric`（本地）。
- **不要编造数值**。API 报 400 就把 message 原样给用户，缺什么补什么。
- **患者隐私**：只发计算必需字段，别把姓名、病历号塞进 `patient_name`。
- **不能作为临床决策唯一依据**。涉及真实患者时，说明本服务是计算辅助，
  结果需由医师核对。

## 更多资料

- `references/api.md` — 端点、字段、响应结构的完整清单
- `references/formulas.md` — 各公式的适用域与限制
- `references/iol-models.md` — 304 款 ULIB 型号及其常数（静态表）
