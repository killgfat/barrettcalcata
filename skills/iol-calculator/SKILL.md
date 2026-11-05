---
name: iol-calculator
description: 通过 HTTP API 计算人工晶体（IOL）度数、做 Barrett Toric 散光计算、查询晶体优化常数、或从 IOL Master 报告图片提取生物测量参数。当用户提到 IOL、人工晶体、晶体度数、Barrett Universal II、SRK/T、Hoffer Q、Haigis、Haigis-T、角膜散光、Toric 轴位、A 常数、ULIB 常数、IOL Master 报告识别、白到白 WTW、眼轴 AL、前房深度 ACD 等任何与白内障术前计算相关的内容时使用本技能。即使用户只是贴了一张 IOL Master 报告截图问「这个该放多少度」，也应使用。
---

# IOL Calculator

一个 Cloudflare Workers 上运行的 IOL 计算服务，本技能封装它的 HTTP API。

## 目标实例

服务地址来自环境变量 `IOL_API_BASE`，**未设置时默认指向项目作者的部署**
`https://barrettcalcata.killgfat.com`。用户自己部署了实例时，让他们设置：

    export IOL_API_BASE=https://<their-worker-domain>

单次覆盖用 `--base`，不要为了换实例去改脚本。

脚本路径相对本技能目录。先确认实例可达再开始算：

    python3 <skill-dir>/scripts/iol.py health

## 用脚本，不要手拼 curl

`scripts/iol.py` 只用标准库，处理了 Cloudflare 对默认 Python UA 的拦截、错误码
和结果摘要。手写 curl 容易漏 User-Agent 被 403，也容易把返回的 JSON 读错。

    # 普通计算
    python3 scripts/iol.py calculate --file payload.json
    python3 scripts/iol.py calculate --json '{"model":"srkt","right_eye":{...}}'
    cat payload.json | python3 scripts/iol.py calculate

    # Barrett Toric（在线，可能被官网拒绝）
    python3 scripts/iol.py toric --json '{...}'

    # 查某款晶体的常数
    python3 scripts/iol.py models --model "AMO ZCB00"

    # 按关键词筛 ULIB 型号（多个关键词是 AND）
    python3 scripts/iol.py ulib-models --search "alcon sn60"

    # 从报告图片提取参数
    python3 scripts/iol.py extract --image report.jpg

加 `--raw` 输出原始 JSON。

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
