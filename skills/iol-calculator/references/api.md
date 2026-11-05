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
| `model` | 是 | `barrett_ii_offline` / `barrett_ii` / `srkt` / `hoffer_q` / `haigis` / `haigis-toric` |
| `right_eye` / `left_eye` | 至少一个 | 单眼参数对象 |
| `iol_model` | 否 | 晶体型号；命中内置 ULIB 时由型号决定常数 |
| `a_constant` | 否 | 默认 119.30，范围 112–125 |
| `k_index` | 否 | `1.3375`（默认）或 `1.332` |
| `step` | 否 | 候选表步长，默认 0.5，范围 0.1–2.0 |
| `haigis_constants` | 否 | `{a0,a1,a2}`，仅 `haigis` / `haigis-toric` |
| `hoffer_q_pacd` | 否 | 0–8 mm，仅 `hoffer_q` |
| `patient_name` | 否 | 不要放真实身份信息 |
| `mode` / `formula` | 否 | 已废弃，`model` 存在时忽略 |

### 单眼字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `AL` | 是 | 眼轴长度 mm，12–38 |
| `K1` / `K2` | 是 | 角膜曲率 D，30–60 |
| `ACD` | 视公式 | 前房深度 mm，0.5–8；`haigis-toric` 必填实测值 |
| `Refraction` | 否 | 目标屈光度 D，默认 0 |
| `LenThickness` | 否 | 晶体厚度 mm，0–15 |
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
    data.constants_source.source  "ulib" 或 "a_constant_conversion"
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

不带参数列出 Barrett 官网型号。带 `?model=<型号>` 查单款常数：

    {"name": "...", "a_constant": ..., "lens_factor": ...,
     "haigis_constants": [a0,a1,a2], "hoffer_q_pacd": ...,
     "srkt_a": ..., "nominal_a": ..., "samples": ...,
     "source": "ulib" | "barrett", "warnings": [...]}

查询顺序：Barrett 型号映射 → ULIB 原始型号名 → Barrett 官网。

## GET /api/ulib-models

返回内置 ULIB 快照全部 304 款。每项含 `name`、`a_constant`、`haigis`、
`pacd`、`samples`、`preliminary`。

## GET /openapi.json

完整 OpenAPI 3.0 规范。`GET /docs` 是对应的 Swagger UI。
