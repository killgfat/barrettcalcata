# 各公式的适用域与限制

面向使用者的摘要。完整推导、校准数据与文献出处见项目仓库的
`docs/formulas.md`。

## Barrett Universal II

`barrett_ii_offline` 是本地近似实现，`barrett_ii` 转发官网。

- 本地版用 `a_constant` 换算 Lens Factor，再用 AL、K、ACD、LT、WTW 预测 ELP；
- 缺失 ACD 时会给出警告；
- 本地版与官网结果不完全一致，属于近似模型；
- **不读 ULIB 常数**，ULIB 表里没有 Lens Factor 列。

## SRK/T

只用 AL 与平均 K，不读 ACD、LT、WTW。常数是优化后的 SRK/T A 常数。

## Hoffer Q

用 AL、K 与 A 常数推导 pACD，再在光学部分加 0.05 mm。

- 术前实测 ACD 不等于 pACD，标准 Hoffer Q 不使用实测 ACD；
- 短眼（AL < 22 mm）是这个公式的主要场景。

## Holladay 1（`holladay1`）

本地实现，论文：Holladay 1988（J Cataract Refract Surg 14:17-24）。

```text
ELP = 0.56 + (rag - sqrt(rag² - AG²/4)) + SF
rag = max(337.5/K, 7.0)
AG  = min(12.5×AL/23.45, 13.5)
ALm = AL + 0.2
P   = 1336/(ALm-ELP) - 1336/(1336/K' - ELP)
```

- 常数是 **SF（Surgeon Factor，mm）**，不是 A 常数，也不是 pACD；
- 可用 `holladay1_sf` 覆盖（范围 -10~12）；不给时按
  `SF = 0.5663·A - 65.60` 换算并降置信度；
- 声明命中 ULIB 的 `iol_model` 时用该晶体的优化 SF（快照 304 款全有），
  请求里的 `a_constant` / `holladay1_sf` 被屏蔽；
- `/api/iol-models` 的列表项带 `sf`，单型号查询带 `holladay1_sf`，
  `references/iol-models.md` 的静态表也有 SF 列，可直接查；
- IOLCon 导出 XML 的 `<Holladay1>` 就是优化后的 SF（mm），
  优先取 optimized，为空才回落 nominal；
- 不读实测 ACD、LT、WTW；
- rag/AG 的双重截断会让 ELP 在 AL≈25.32 mm 处达到极大值，
  这是原论文为避免根号内为负而做的限制，不是误差。

## Haigis

ELP 由三常数预测：`d = a0 + a1×ACD + a2×AL`。

- 使用实测 ACD；缺失时用默认值并标记 `ACD_defaulted`、降置信度；
- 三常数缺失时由 A 常数按厂商标准关系推导 a0，这只是近似起点，
  结果会给警告并标 `LOW_CONFIDENCE`。

## Castrop（`castrop`）

本地实现，论文：Langenbucher 2021（PLoS ONE 16(6):e0252102）。

- 需要术前 `ACD` 与晶状体厚度 `LenThickness`（缺省 3.20 / 4.60 mm 并降置信度）；
- 常数是 **C/H/R**，不是 A 常数：`castrop_constants` 传 `{C, H, R}`，
  值从 IOLCon 的 `Castrop(C / H / R)` 列抄入；
- ULIB 快照里没有这三列，所以选 `iol_model` 也不会覆盖常数；
  服务端对 `?formula=castrop` 返回空列表，Web UI 在 Castrop 下
  不显示型号选择器 —— 没有型号可查，列出来只会误导；
- `castrop_constants` 与 `castrop_elp` 都没给时，用论文优化初值
  C=0.40/H=0.00/R=0.00，结果标 `LOW_CONFIDENCE`，并明确告诉用户
  这不是晶体专属常数；
- 已有 IOLCon 算好的 ELP 时直接传 `castrop_elp`（mm），跳过 C/H 推导；
- `castrop_elp_model` 选 ELP 推导方式：
  `acd_lt`（默认，ACD + C·LT + H）、`regression`（含 AL 与角膜半径）、
  `regression_no_r`（含 AL、不含角膜半径，角膜屈光术后用）；
- 眼轴默认按 Cooke 回归换算（`castrop_al_correction`，默认 true）；
- A 常数与 WTW 不参与计算，会出现在 `ignored_inputs`。

## Haigis-T（`haigis-toric`）

本地近轴实现，**不是官方算法**，结果固定标低置信度。

需要：每眼 `K1`/`K1Axis`/`K2`/`K2Axis`（必须正交）、实测 `ACD`；
请求级 `haigis_constants` 或命中 ULIB 的 `iol_model`。

- `posterior_mode=none`（默认）不计后表面散光，WTR 可能过矫、ATR 可能欠矫；
- `measured` 用实测 PCA；`total` 用 TK/TCRP 总散光替换前表面与 PCA；
- `estimated` 用固定的 0.30 D @0° ATR 代理，**未经一手算法核实**；
- 轴位一律指光学强子午线，负柱镜处方轴为 axis+90；
- 不给 `cylinder_powers` 时只返回连续柱镜解，不猜厂商档位。

## A 常数在不同公式里的角色

同一个 `a_constant` 字段，四套公式用法不同，别一律当成“主参数”：

| 公式 | A 常数的作用 |
|---|---|
| SRK/T | 主参数，`ACD = 0.62467·A - 68.747 + H - 3.336` |
| Hoffer Q | 兜底，`pACD = 0.58357·A - 63.896`；给了 `hoffer_q_pacd` 就不再用 |
| Holladay 1 | 兜底，`SF = 0.5663·A - 65.60`；给了 `holladay1_sf` 就不再用 |
| Haigis | 兜底，由 A 近似 `a0 = 0.62467·A - 72.434`；给了 `haigis_constants` 就不再用 |
| Castrop | 完全不参与 |

判断依据看每眼的 `used_inputs.a_constant`：为 `null` 且
`ignored_inputs` 含 `a_constant` 时，说明这次计算没用到它。

Castrop 没有 A → C/H 的换算：C（无量纲 0.35~0.44）、H（mm）、R（D）量纲
各不相同，公开文献里没有把 A 映射到这三个量的式子。IOLCon 有“由 Haigis
常数推导 Castrop 常数”的标注，那是平台自有拟合，未公开，不要自行反推。

## 常数来源的边界

内置 ULIB 快照来自 IOLMaster 的优化常数（2016-10-31 停更，共 304 款）。
它只覆盖 SRK/T A、Hoffer Q pACD、Haigis a0/a1/a2、Holladay 1 SF、SRK II A，
没有 Barrett 的 Lens Factor，也没有 Castrop 的 C/H/R（2021 年才发表，
快照 2016 年就停更了）。

型号命中 ULIB 时其常数优先；请求里同类的常数会被屏蔽。ULIB 缺某一项时
才回落到请求值并给出警告。

**拿 A 常数反推 pACD 或 a0 只是近似**，与优化常数可能差 0.5 D 以上。
有条件时应使用晶体型号查表。

IOLCon（https://iolcon.org）是现行维护的官方常数来源，同一型号的值
常已更新。其条款禁止再分发，本服务不内置；正路是让用户自行获取，
以自定义参数传入，而不是声明 `iol_model`。

## 临床限制

- 本服务是计算辅助工具，结果不能替代医师判断；
- 在线公式依赖外部站点，不保证可用性；
- 不持久化患者数据；
- 不应把结果直接用于手术决策而未经核对。
