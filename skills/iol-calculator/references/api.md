# IOL Calculator API 参考

所有端点都返回 JSON。成功：

    {"success": true, "data": {...}, "message": "..."}

失败：

    {"error": "...", "message": "..."}

状态码：`200` 成功、`400` 参数无效、`405` 方法错误、`415` 非 JSON、`500` 计算失败。

## POST /api/calculate

普通 IOL 计算。

### 顶层字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `model` | 是 | `barrett_ii_offline` / `barrett_ii` / `srkt` / `hoffer_q` / `holladay1` / `haigis` / `castrop` / `haigis-toric` |
| `right_eye` / `left_eye` | 至少一个 | 单眼参数对象 |
| `iol_model` | 否 | 晶体型号；命中内置 ULIB 时由型号决定常数 |
| `a_constant` | 否 | 默认 119.30，范围 112–125 |
| `k_index` | 否 | `1.3375`（默认）或 `1.332` |
| `step` | 否 | 候选表步长，默认 0.5，范围 0.1–2.0 |
| `haigis_constants` | 否 | `{a0,a1,a2}`，仅 `haigis` / `haigis-toric` |
| `hoffer_q_pacd` | 否 | 0–8 mm，仅 `hoffer_q` |
| `holladay1_sf` | 否 | -10–12 mm，仅 `holladay1`；留空由 A 常数换算 |
| `castrop_constants` | 否 | `{C,H,R}`，仅 `castrop`；三项必须齐全 |
| `castrop_elp` | 否 | 2–12 mm，仅 `castrop`；直接指定 ELP |
| `patient_name` | 否 | 不要放真实身份信息 |
| `mode` / `formula` | 否 | 已废弃，`model` 存在时忽略 |

### 单眼字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `AL` | 是 | 眼轴长度 mm，12–38 |
| `K1` / `K2` | 是 | 角膜曲率 D，30–60 |
| `ACD` | 视公式 | 前房深度 mm，0.5–8；`haigis-toric` 必填实测值，`castrop` 是 ELP 的核心输入 |
| `Refraction` | 否 | 目标屈光度 D，默认 0 |
| `LenThickness` | 否 | 晶体厚度 mm，0–15；`castrop` 用它推导 ELP 并做 Cooke 眼轴修正 |
| `WTW` | 否 | 白到白 mm，5–25 |
| `K1Axis` / `K2Axis` | `haigis-toric` 必填 | 0–180，必须正交 |
| `iol_cylinder` | 否 | 实际植入柱镜 D；非 0 时必须给 `iol_axis` |
| `iol_axis` | 否 | IOL 弱子午线方向，0–180 |
| `iol_spherical_equivalent` | 否 | 实际植入 SE，-10–45 |
| `posterior_mode` | 否 | `none` / `measured` / `estimated` / `total` |
| `posterior_cylinder` / `posterior_axis` | `measured` 必填 | 角膜平面 PCA |
| `total_cylinder` / `total_axis` / `total_source` | `total` 必填 | `total_source` 为 `TK` 或 `TCRP` |
| `incision_sia` | 否 | 切口引起的扁平化 D，默认 0 |
| `incision_location` | 否 | 切口位置度；SIA 非 0 时必填 |
| `cylinder_powers` | 否 | 可供柱镜档位数组 |

### 响应要点

    data.calculation_model        实际使用的模型
    data.constants_source.source  "ulib" / "a_constant_conversion" /
                                  "explicit_sf" / "castrop_constants" /
                                  "castrop_elp" / "paper_default"
    data.constants_source.applied          型号提供的字段
    data.constants_source.ignored_request  被型号屏蔽的请求字段
    data.right_eye.recommended_power
    data.right_eye.predicted_refraction
    data.right_eye.used_inputs      实际参与计算的值
    data.right_eye.ignored_inputs   本次忽略的输入
    data.right_eye.iol_options      候选度数表
    data.right_eye.confidence       OK / LOW_CONFIDENCE
    data.right_eye.warnings

`haigis-toric` 额外返回 `residual_astigmatism`、
`recommended_iol_cylinder_exact`、`recommended_axis`、`toric_options`。

## POST /api/calculate-toric

Barrett Toric 在线计算，转发到 Barrett 官网。

顶层：`right_eye` / `left_eye`（至少一个）、`a_constant`、`iol_model`、
`k_index`、`cylinder_mode`（`+ve` / `-ve`）、`patient_name`。

每眼必填 `K1`、`K1Axis`、`K2`、`K2Axis`、`AL`、`lens_thickness`、`WTW`；
可选 `ACD`（默认 3.0）、`target_refraction`、`incision_sia`、`incision_location`。

也接受 `toric_right_eye` / `toric_left_eye` 作为别名。

官网可能拒绝自动请求，返回 500 并提示稍后重试。不要反复重试。

## POST /api/extract

从 IOL Master 报告图片提取参数。请求 `{"image": "<base64>"}`，只用
`content-type: application/json`。

返回 `data` 含 `a_constant`、`haigis_constants`、`hoffer_q_pacd`、
`right_eye`、`left_eye`。`success: false` 且 `requires_manual_verification:
true` 表示多数决未达成，应当让用户核对而不是直接拿去计算。

## GET /api/iol-models

一个端点两件事，靠查询参数区分。

**`?formula=<公式>` 返回候选型号列表**（不传 `model` 时）：

| formula | 来源 | 条目 |
|---|---|---|
| `barrett`（默认） | Barrett 官网清单 | 18 |
| `srkt` / `hoffer_q` / `holladay1` / `haigis` / `haigis-toric` | ULIB 快照 | 304 |
| `castrop` | 无 | 0 |

`castrop` 返回空 `models`、`source: "none"` 与
`constants_available: false`，并附一条 warning。因为 ULIB 快照停更于
2016-10-31，Castrop 2021 年才发表，表里没有 C/H/R 三列，也就没有可选的
晶体条目。常数必须由调用方用 `castrop_constants` 或 `castrop_elp` 传入，
所以 Web UI 在 Castrop 下不显示型号选择器。

ULIB 快照停在 2016-10-31；现行优化常数以 IOLCon（iolcon.org）为准，
用户可自行获取后以自定义参数传入（见 SKILL.md「常数要新：优先 IOLCON」）。

也接受 `barrett_ii`、`barrett_ii_offline`。响应：

    {"success": true,
     "data": {
       "formula": "barrett",
       "source": "barrett" | "barrett_local_map" | "ulib" | "none",
       "constants_available": true | false,
       "source_revision": "2016-10-31",
       "warnings": [],
       "models": [{"name": ..., "a_constant": ..., "haigis": [a0,a1,a2],
                   "pacd": ..., "sf": ..., "samples": ..., "preliminary": ...,
                   "lens_factor": null, "ulib_name": ..., "match": ...,
                   "note": ...}]}}

`sf` 是 Holladay 1 的 Surgeon Factor（mm），与单型号查询里的
`holladay1_sf` 是同一个数；ULIB 304 款全部有值，不会为 null。

Barrett 官网不可达时 `source` 变成 `barrett_local_map`，`warnings` 说明
降级原因，列表仍可用。未映射到 ULIB 的型号 `a_constant` 为 `null`，
`note` 给出原因——不要给它编一个常数。

**`?model=<型号>` 查单个型号的常数**：

    {"name": "...", "a_constant": ..., "lens_factor": ...,
     "haigis_constants": [a0,a1,a2], "hoffer_q_pacd": ...,
     "holladay1_sf": ..., "srkt_a": ..., "srk2_a": ..., "nominal_a": ...,
     "samples": ..., "preliminary": ..., "source": "ulib" | "barrett",
     "warnings": [...]}

查询顺序：Barrett 型号映射 → ULIB 原始型号名 → Barrett 官网。

所以 `model=` 和 `iol_model` 都接受 Barrett 的短名：`AMO ZCB00` 会命中
ULIB 的 `AMO Tecnis 1 ZCB00`，响应里 `name` 回显请求值、`ulib_name`
给出命中的 ULIB 条目。要确认实际用的是哪条，看 `ulib_name` 和
`source`；两个都对不上才回落 Barrett 官网。

旧的 `/api/ulib-models` 已移除，改用
`/api/iol-models?formula=<任意非 Barrett 公式>`。

**`formula=castrop` 返回空列表**（`source: "none"`、
`constants_available: false`）。这不是错误：ULIB 里没有该公式的
晶体常数，列出型号只会让人以为能选型号自动填常数。需要常数请走
`castrop_constants` 或 `castrop_elp`。

## Castrop 的请求参数

`model=castrop` 时额外支持（其它公式传这些字段会返回 400）：

| 字段 | 说明 |
|---|---|
| `castrop_constants` | `{"C":..,"H":..,"R":..}`，从 IOLCon 的 `Castrop(C / H / R)` 列抄入 |
| `castrop_elp` | 直接指定 ELP（mm），给出后跳过 C/H 推导 |
| `castrop_elp_model` | `acd_lt`（默认）/`regression`/`regression_no_r` |
| `castrop_cct` | 中央角膜厚度（mm），默认 0.55 |
| `castrop_posterior_ratio` | 角膜后/前表面半径比，默认 0.82368 |
| `castrop_al_correction` | 是否做 Cooke 眼轴修正，默认 true |

    {"model": "castrop",
     "right_eye": {"AL": 23.5, "K1": 43.5, "K2": 44.0,
                   "ACD": 3.2, "LenThickness": 4.6, "Refraction": 0},
     "castrop_constants": {"C": 0.424, "H": -0.312, "R": 0.077}}

响应里每眼带 `castrop_details`（C/H/R、ELP 与来源、Pcornea、ALcor、
实际使用的角膜参数），顶层 `constants_source` 的 `source` 取
`castrop_constants` / `castrop_elp` / `paper_default`，`ulib_supported`
恒为 false。

## GET /openapi.json

完整 OpenAPI 3.0 规范。`GET /docs` 是对应的 Swagger UI。
