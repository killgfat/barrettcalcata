---
name: iol-calculator
version: 1.2.0
slug: iol-calculator
displayName: IOL 人工晶体度数计算
summary: 调用 IOL 计算服务计算人工晶体度数：Barrett Universal II、SRK/T、Hoffer Q、Holladay 1、Haigis、Castrop 球镜，Barrett Toric / Haigis-T 柱镜与轴位，并按 ULIB 型号查优化常数。
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
description: 调用 IOL 计算服务（HTTP API）来产出人工晶体度数的具体数值——Barrett Universal II、SRK/T、Hoffer Q、Holladay 1、Haigis、Castrop 的球镜计算，Barrett Toric 的柱镜与轴位，以及按晶体型号查优化常数（Castrop 的 C/H/R 需用户从 IOLCon 提供）。在下列情形使用：用户给出具体生物测量值（眼轴 AL、角膜曲率 K1/K2、前房深度 ACD、散光轴位、白到白 WTW）并问晶体该放多少度、柱镜选哪档、轴位定在哪；指定了晶体型号要查它的 A 常数 / Haigis a0a1a2 / Hoffer Q pACD / Holladay 1 SF；要把计算结果在几个公式之间对比或解释为什么差一档；提到自己部署了一份实例（自定义域名、IOL_API_BASE）想拿它算度数；拿着报告上的某个读数问它该怎么填进计算、会不会影响结果。反过来不需要本技能的场景：纯粹问公式原理、为什么 K 值要用 1.3375 折射率、Haigis 与 Haigis-L 的文献差异、PubMed 上有哪些研究，只是想打开 ULIB / IOLCon 网站看看，或者想让本技能从报告图片里 OCR 出数值——本服务不做图片识别，只接受用户已经读出的数值。
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

加 `--raw` 输出原始 JSON。

查晶体型号与常数不必调接口：`references/iol-models.md` 是内置的 304 款
ULIB 型号表，直接查表就能填 `iol_model`。这张表是 2016 年的静态快照，
**不含 Castrop 的 C/H/R**（该公式 2021 年才发表），
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
| `holladay1` | Holladay 1 | 常数是 SF，可用 `holladay1_sf` 覆盖；不读 ACD/LT/WTW |
| `haigis` | Haigis | 用 ACD，不读 LT、WTW |
| `castrop` | Castrop | 用 ACD + LT；常数是 `castrop_constants`（C/H/R），不是 A 常数 |
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

这是最容易搞错的地方。**只要 `iol_model` 命中内置 ULIB，服务端就忽略
请求里同类的 `a_constant` / `hoffer_q_pacd` / `holladay1_sf` /
`haigis_constants`，改用该型号的内置常数——不会报错，只在响应的
`constants_source.ignored_request` 和每眼 `ignored_inputs` 里体现。**

「命中」指按 Barrett 型号映射或 ULIB 原始名查到条目，所以 Barrett 的短名
也能用：`AMO ZCB00` 会命中 ULIB 的 `AMO Tecnis 1 ZCB00`。响应的
`ulib_name` 会回显命中的 ULIB 条目，拿它核对最稳。

所以：

- 用户说「用某款晶体」→ 只给 `iol_model`，别同时塞 A 常数。
- 用户给了自己的 A 常数、没说型号 → 只给 `a_constant`。
- 两者都给 → 型号胜出。如果你不确定用户想要哪个，问一句，不要默认。

Barrett 系列（`barrett_ii_offline` / `barrett_ii`）不读 ULIB，只用 `a_constant`。

`holladay1` 也读 ULIB：快照 304 款全部带 Holladay 1 SF，声明型号即用该晶体的
优化 SF。列表接口返回的 `sf` 与单型号查询的 `holladay1_sf` 是同一个数，
可以直接读出来回填或核对。

`haigis-toric` 的常数有两条路：请求级 `haigis_constants`，或命中 ULIB 的
`iol_model`。都没有会返回 400。

**`castrop` 是这条规则的唯一例外**：它的常数是 C/H/R，ULIB 快照里没有，
所以 `iol_model` 不会覆盖它们。C/H/R 从 IOLCon 的 `Castrop(C / H / R)` 列
抄进 `castrop_constants`；手上有 IOLCon 算好的 ELP 也可以直接传
`castrop_elp`（mm）；两者都没有时服务端用论文优化初值
C=0.40/H=0.00/R=0.00 兜底，并把结果标成 `LOW_CONFIDENCE` ——
这时要主动告诉用户常数没有晶体特异性。

## 常数要新：优先 IOLCON

内置 ULIB 表是 2016-10-31 停更的快照。IOLCon（https://iolcon.org）是
Langen-Bucher 团队持续维护的官方优化常数库，同一型号的常数往往已经
更新过，更可靠。本技能刻意不内置它：IOLCon 条款只允许用户为自身
计算目的使用数据，禁止复制、传播或转交第三方。

IOLCon 的导出接口匿名可用，不用注册（约 1 MB，等几十秒）：

    curl -s "https://iolcon.org/downloadLenses.php?action=download"

返回 XML，646 款晶体，含 SRK/T A（`<SRKt>`）、Hoffer Q pACD
（`<HofferQ>`）、Holladay 1 SF（`<Holladay1>`）、Haigis a0/a1/a2
和 Barrett 的 Lens Factor（`<Barrett><LF>`）。每款有
nominal（厂商名义值）和 optimized（实测优化值）两组常数。**优先取
optimized，为空才回落 nominal**：每个 optimized 块都存在，判据是
它的 `results` 属性大于 0 且对应字段非空；646 款里只有约 150 款
有优化数据，其余全空。IOLCon 比内置表有价值主要就在这批优化值上，
拿 nominal 前先确认没有 optimized 可用。接口没有按型号名过滤的参数
——现场下载整个文件、用 `grep` 定位目标型号、只取它的三四个数字，
用完即弃。

grep 型号名常命中多条：近似型号在文件里各占一条 `<Lens>`（如
`ZCB00` 与 `ZCB00V` 是相邻两条）。取数前先核对 `<Manufacturer>`
和 `<Name>` 与目标一致；不要用 `grep -A` 数行跨过 `</Lens>` 边界，
会把下一个型号的常数混进来。

用 `srkt` / `hoffer_q` / `holladay1` / `haigis` / `haigis-toric`
（Barrett 系列需要 `a_constant`）且报了晶体型号时，主动建议：

1. 从上面接口取该型号常数（或让用户自己在 iolcon.org 网页查）；
2. 用自定义参数传请求（`a_constant` / `hoffer_q_pacd` /
   `holladay1_sf` / `haigis_constants`），**不要同时声明 `iol_model`**——会被内置表
   静默屏蔽（见上一节）；
3. 回复里注明常数来自 IOLCon、哪个型号、什么时候取的。

用户拿不到 IOLCon 数据时再走内置表（声明 `iol_model`），但要如实
说明这是 2016 年快照，与现行优化值可能差半档以上。用户手上有厂商
手册等其他来源的常数，同样走自定义参数。

### Holladay 1 的 SF 怎么取

Holladay 1 的常数是 **SF（Surgeon Factor，mm）**，不是 A 常数，也不是
Hoffer Q 的 pACD——三者量纲都是 mm，但定义不同，不能互相代入。
SF 是虹膜平面到 IOL 主平面的距离，pACD 是角膜顶点到虹膜平面的距离。

取数路线和 Haigis 的 a0/a1/a2 完全一样，也是**优先 IOLCon optimized，
其次内置 ULIB**：

1. **IOLCon 的 optimized SF**（最可靠）→ 传 `holladay1_sf`。
   导出 XML 里的字段就叫 `<Holladay1>`，值直接是 SF 毫米数，不需要
   再做换算。646 款里 nominal 有 526 款、optimized 有 152 款，
   另有 92 款带独立的 `type="ULIB"` 块；口径同上，**optimized 优先，
   为空才回落 nominal**。例：`AMO Tecnis 1 ZCB00` 的 nominal 是 1.96、
   optimized 是 2.0582，差 0.1 mm 就够换半档，别拿 nominal 顶替；
2. **内置 ULIB 快照**（拿不到 IOLCon 时）→ 声明 `iol_model`，304 款全部
   带 SF。静态表 `references/iol-models.md` 的 SF 列可以直接查来填
   `holladay1_sf`，也可以只声明型号让服务端取；但这是 2016 年快照，
   与 IOLCon 现行 optimized 值可能差 0.1 mm 以上；
3. **都没有** → 服务端按厂商标准关系 `SF = 0.5663×A - 65.60` 换算，
   结果标 `LOW_CONFIDENCE` 并给警告。这时要主动说明：这不是晶体专属
   常数，与 IOL Master 打印的 Holladay 1 结果可能差半档。

注意第 1、2 条互斥：既然走 IOLCon 自定义参数，就**不要再声明
`iol_model`**，否则内置表会静默覆盖你传的 SF（见上文「常数优先级」）。

SF 的合法输入范围是 **-10~12 mm**，比 pACD 的 0~8 宽得多，因为 ULIB 里
有两条超高度数晶体落在极值：`Alcon MA60MA (+diopters)` 是 +10.29，
`(-diopters)` 是 -7.08。看到这类型号不要以为是数据错误。

另外提醒一句：这两个极值 SF 会让 ELP 推到 14 mm 以上，公式在光学部分
发散，服务端返回「无法生成 IOL 度数表」。Hoffer Q 用同一批常数也会这样，
属于这批型号的常数超出薄透镜模型适用范围，不是 Holladay 1 特有的问题。
遇到时如实说明，不要换个公式凑一个数字出来。

### Castrop 的常数怎么取

Castrop 是 2021 年的公式，**内置 ULIB 快照里根本没有它的 C/H/R**，所以
它既不在 `references/iol-models.md` 里，也不会被 `iol_model` 带出来
（服务端对 `?formula=castrop` 返回空列表）。三条路，按优先级：

1. 用户手上有 IOLCon 该型号的 `C / H / R` 三个数 → 传
   `castrop_constants`，**三项必须齐全**，缺一项 API 返回 400；
2. 用户有 IOLCon 或 AS-OCT 算好的 ELP → 传 `castrop_elp`（mm），
   跳过 C/H 推导；
3. 都没有 → 服务端用论文优化初值 C=0.40/H=0.00/R=0.00，结果标
   `LOW_CONFIDENCE`。**必须主动说明这组常数没有晶体特异性**，
   不要把 21.5 D 这样的数字单独丢给用户。

IOLCon 导出 XML 里的 Castrop 字段是 `CastropC` / `CastropH` /
  `CastropR`（网页上写作 `Castrop(C / H / R)`），取值口径同上：
优先 optimized，为空才回落 nominal。IOLCon 页面对部分型号会提示
"Castrop constants derived from Haigis constants"，这类值精度差一些，
要在回复里点出来。

合规红线：下载接口匿名可用不等于授权再分发——条款 8.1 只允许用户
为自身计算目的使用数据。不要把导出文件、批量表格或常数快照写进代码、
文档、缓存或对话；每次现取现用，一次只取一个型号的三四个数字。

## 读懂返回

摘要里值得转述给用户的字段：

| 字段 | 含义 |
|---|---|
| `recommended_power` | 推荐度数（D） |
| `predicted_refraction` | 该度数下的预测屈光度 |
| `confidence` | `OK` / `LOW_CONFIDENCE` |
| `constants_source` | `ulib` / `a_constant_conversion` / Holladay 1 的 `explicit_sf` / Castrop 的 `castrop_constants` / `castrop_elp` / `paper_default` |
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
