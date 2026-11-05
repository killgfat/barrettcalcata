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

## Haigis

ELP 由三常数预测：`d = a0 + a1×ACD + a2×AL`。

- 使用实测 ACD；缺失时用默认值并标记 `ACD_defaulted`、降置信度；
- 三常数缺失时由 A 常数按厂商标准关系推导 a0，这只是近似起点，
  结果会给警告并标 `LOW_CONFIDENCE`。

## Haigis-T（`haigis-toric`）

本地近轴实现，**不是官方算法**，结果固定标低置信度。

需要：每眼 `K1`/`K1Axis`/`K2`/`K2Axis`（必须正交）、实测 `ACD`；
请求级 `haigis_constants` 或命中 ULIB 的 `iol_model`。

- `posterior_mode=none`（默认）不计后表面散光，WTR 可能过矫、ATR 可能欠矫；
- `measured` 用实测 PCA；`total` 用 TK/TCRP 总散光替换前表面与 PCA；
- `estimated` 用固定的 0.30 D @0° ATR 代理，**未经一手算法核实**；
- 轴位一律指光学强子午线，负柱镜处方轴为 axis+90；
- 不给 `cylinder_powers` 时只返回连续柱镜解，不猜厂商档位。

## 常数来源的边界

内置 ULIB 快照来自 IOLMaster 的优化常数（2016-10-31 停更，共 304 款）。
它只覆盖 SRK/T A、Hoffer Q pACD、Haigis a0/a1/a2、Holladay 1 SF、SRK II A，
没有 Barrett 的 Lens Factor。

型号命中 ULIB 时其常数优先；请求里同类的常数会被屏蔽。ULIB 缺某一项时
才回落到请求值并给出警告。

**拿 A 常数反推 pACD 或 a0 只是近似**，与优化常数可能差 0.5 D 以上。
有条件时应使用晶体型号查表。

## 临床限制

- 本服务是计算辅助工具，结果不能替代医师判断；
- 在线公式依赖外部站点，不保证可用性；
- 不持久化患者数据；
- 不应把结果直接用于手术决策而未经核对。
