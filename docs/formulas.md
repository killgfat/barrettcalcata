# 公式实现说明

本文说明 src/formula/ 中各计算模块的算法来源、参数用途和限制。
API 字段与在线示例以 /openapi.json 为准。

## 1. 统一接口与独立性

src/formula/formula.py 负责计算模型解析、能力检查、单双眼编排和结果组装。
各公式独立完成角膜参数转换、ELP 预测、目标屈光度处理和术后屈光反解。

| 计算模型 | 实现 | 使用的主要输入 | 执行方式 |
|---|---|---|---|
| barrett_ii_offline | Barrett 本地近似 | AL、K；可选 ACD、LT、WTW | 本地，零网络 |
| barrett_ii | Barrett 官网适配器 | 按官网表单转发 | Barrett 官网 |
| srkt | SRK/T | AL、K、A 常数 | 本地，零网络 |
| hoffer_q | Hoffer Q | AL、K、A 常数/pACD | 本地，零网络 |
| haigis | Haigis | AL、K、ACD、a0/a1/a2 | 本地，零网络 |
| haigis-toric | Haigis-T 公开框架近轴实现 | AL、前表面 K/轴位、实测 ACD、三常数；可选 PCA/总散光、SICA、IOL 柱镜/轴位 | 本地，零网络 |

各公式使用各自的光学核心：

- SRK/T 与 Hoffer Q 不使用术前实测 ACD、LT、WTW；
- Haigis 使用实测 ACD，不使用 LT、WTW；
- Haigis 光学部分使用自己的 nC=1.3315；
- ELP 由术前生物测量决定，与目标屈光度无关；
- 各公式独立实现，不通过 Barrett 的结果拟合或修正其他公开公式。

## 2. Barrett Universal II

### 2.1 在线模式

barrett_ii 调用 Barrett 官方在线计算器，通过官网表单、会话和结果解析获取结果。
它不是本地公式，官网可用性及返回结构变化会影响该路径。

在线 Toric 使用独立的 barrett_ii_toric 和 POST /api/calculate-toric，需要额外的
轴位、切口 SIA 等参数。本地 haigis-toric 则使用 POST /api/calculate 的模型调度。

### 2.2 离线模式不是官方公式复刻

官方 Barrett Universal II 的完整 ELP 预测和厚透镜光线追迹未公开。
本地实现由两部分组成：

1. Gaussian 聚散度核心：

   ```text
   P = 1336/(AL-ELP) - 1336/(1336/K'-ELP)
   ```

   K' 包含按 12 mm 顶点距离折算的目标屈光度。

2. 固定 ELP 近似式：AL/K 二次项、ACD/LT/WTW 修正项，以及 A 常数经
   Lens Factor 产生的平移。

这些 ELP 系数是当前薄透镜模型下的**等效 ELP 回归参数**，不是官方 ELP，
也不是官方内部系数。未提供 ACD/LT/WTW 时跳过相应修正，不能把这些字段的
参考中心值解释为患者的真实测量值。

A 常数与 Lens Factor 的线性换算来自公开厂商常数对，同样不是官方公布的
完整转换公式。

### 2.3 校准数据来源与使用边界

开发期使用 [ekrbye/barrett-uii-data](https://github.com/ekrbye/barrett-uii-data)
提供的官方在线计算器输入/输出样本：

- 数据作者：Yishen Wang、Li Li；
- 许可证：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；
- 数据主要包括单参数扫描 scans.csv 和双参数曲面 grids.npz；
- 数据不直接包含官方 ELP 或其预测系数；
- 本项目对样本进行薄透镜等效 ELP 反演、回归拟合和误差分析，属于对原数据的加工；
- 数据只用于 Barrett Offline 的开发期校准与验证，不用于 SRK/T、Hoffer Q、Haigis；
- **Worker 运行时不访问该仓库，不读取数据文件，也不需要 numpy。**

校准脚本为 scripts/calibrate_offline.py，详细方法、系数和偏差见
[校准报告](calibration_report.md)。数据不随项目发布，也不进入部署包。

### 2.4 已有数值验证的含义

在当前公开扫描留出集上：

| 离线模式 | mean Δ | SD | median \|Δ\| | p95 \|Δ\| | max \|Δ\| |
|---|---:|---:|---:|---:|---:|
| AL/K + ACD/LT/WTW | +0.002 D | 0.164 D | 0.091 D | 0.328 D | 0.918 D |
| 纯 AL/K | +0.001 D | 0.339 D | 0.159 D | 0.685 D | 1.805 D |

其中 Δ=本地连续 IOL 度数−公开官方输出。这些数字：

- 不是术后临床屈光误差；
- 不证明与官方 Barrett 全量实现等价；
- 不能直接代表只提供 AL/K/ACD 的四参数场景；
- 主要基于 A=118.7、target=0，其他常数和非零目标仍需独立验证。

短眼、长眼、极端 K 和特殊前房结构应使用在线模式或其他可靠方式复核。

## 3. SRK/T

实现位置：src/formula/srkt.py。

采用公开的 SRK/T 算法，包括：

- A 常数转换为 ACD constant；
- LCOR、角膜宽度和角膜高度修正；
- 视网膜厚度及 optical AL 修正；
- ELP 阶段的角膜参数与光学阶段的 nC=1.333 分别处理。

目标屈光度按 Retzlaff 附录公式进入分子和分母，预测屈光度由对应公式反解。
不把目标屈光度简单加到 K 后同时改变 ELP；ELP 只由术前 AL、K 和 A 常数决定。

术前实测 ACD、LT、WTW 不参与标准 SRK/T 计算，会在统一结果中列为忽略输入。

## 4. Hoffer Q

实现位置：src/formula/hoffer_q.py。

采用公开 Hoffer Q 及 errata 的算法：

```text
pACD = 0.58357 × A - 63.896
```

随后根据 AL 和 K 做 Q 修正，并在光学计算中使用 ACD+0.05 mm。
实现保持以下规则：

- AL<=23 与 AL>23 使用不同的 M/G 分支；
- 正切计算先把角度转换为弧度；
- AL 截断只用于 Q/ELP 部分，光学部分仍使用原始 AL；
- 目标屈光度在光学部分处理，不改变患者 ELP。

术前实测 ACD 不等于 pACD；标准 Hoffer Q 不使用实测 ACD、LT、WTW。
接口由 A 常数推导 pACD，结果不应自动视为与任意设备晶体库的优化常数一致。
型号已收录在内置 ULIB 快照时，请求里声明 `iol_model` 即可让服务端
查表取优化 pACD；不声明型号时才用 `hoffer_q_pacd` 或由 A 常数推导。

## 5. Haigis

实现位置：src/formula/haigis.py。

ELP 由三常数公式预测：

```text
d = a0 + a1×ACD + a2×AL
```

光学部分使用 Haigis 自己的角膜折射率 nC=1.3315。实现先根据原始输入
K-index 恢复角膜半径，再计算 Haigis 所需的角膜屈光度。

常数有两种来源：

1. **型号或显式三常数**：请求声明了命中 ULIB 的 `iol_model` 时，
   服务端查出该晶体的 a0/a1/a2 并直接使用；未声明型号时才用请求里的
   `haigis_constants`。两种情况下都不再从 A 常数推导 a0。常数应与
   IOL Master 或晶体库中的具体晶体一致。
2. **标准近似起点**：固定 a1=0.4、a2=0.1，并由
   a0=0.62467×A−72.434 推导 a0。该结果不是个体化优化常数，
   与设备使用的晶体专属常数可能明显不同，结果会给出警告并降低置信度。
   该线性式属于「厂商标准关系」，与 ULIB 的「优化常数关系」不同，
   详见第 7 节。

Haigis 应优先使用实测 ACD。未提供时使用明确的默认值并标记
ACD_defaulted、LOW_CONFIDENCE；默认值不能解释为患者的真实 ACD。

## 6. Haigis-T（Haigis toric）

实现位置：src/formula/haigis_toric.py。模型名和公式名均为 `haigis-toric`，
只支持 offline，经 `formula.calculate` 或 POST `/api/calculate` 调用。
球镜 SE、ELP 和球镜候选表直接复用 `haigis.calculate`，无新运行时依赖、
网络请求、患者数据持久化或校准数据文件。

Web 页面：切换到「散光」后，可选择 **Barrett Toric · 在线** 或
**Haigis-T · 本地**。两种散光公式各自保留参数，非散光公式选择独立保留；
Haigis 三常数与非散光 Haigis 共用，支持报告识别回填。

Haigis-T 必须填写完整 a0/a1/a2、AL、前表面 K1/K2 及正交轴位、
**术前实测 ACD**。实测 ACD 使用独立输入，不采用 Barrett 表单的默认 3.00。
LT、WTW、A 常数和正负柱镜符号控件在该模式隐藏，且不提交给求解器。
后表面参数按所选 none/measured/total/estimated 模式显示，仅提交当前模式
字段；估算模式明确显示未验证的固定 PCA 代理说明。可供档位填写真实
IOL 平面柱镜，用逗号分隔；留空不猜测厂商档位。任一启用眼缺少必填值、
轴位不正交或柱镜档位无效时，页面禁用计算并提示具体问题。

结果分别显示拟植入方案的角膜平面残余（光学强子午线与等效负柱镜轴位）、
ELP 相关换算、连续柱镜解、可供档位推荐及 Haigis 球镜 SE 候选。
档位推荐按最佳轴位比较，与拟植入轴位的残余预测分开展示。

浏览器回归测试（所有网络请求被拦截，Haigis-T 使用真实本地计算结果）：

```bash
uv run --with playwright playwright install chromium
uv run --with playwright pytest tests/test_webui_toric_browser.py
```

可通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE` 指定已有的 Chromium 路径；
未安装 Playwright 的普通 `uv run pytest` 会跳过该浏览器测试模块。

### 6.1 来源与可确认范围

本模块是**公开框架近轴实现**，完整商用 Haigis-T 一手算法尚未核实，
返回 `model=Haigis-T-paraxial`、`LOW_CONFIDENCE` 与来源限制警告。

2026-11-04 检索记录：

- 任务提供的 Haigis W. *Calculation of Astigmatism Correction With the
  Toric Intraocular Lens.* J Refract Surg. 2015;31(10):669–676，
  在 Europe PMC/PubMed 题名检索与 Crossref 题录检索中未能确认。
  该期相关页码的可检索记录为 Esteve-Taboada 等的
  *Effect of Large Apertures on the Optical Quality of Three Multifocal
  Lenses*，[PMID 26469074](https://pubmed.ncbi.nlm.nih.gov/26469074/)，
  Europe PMC 标注 666–676；这是题录冲突，不能据所给引文声称实现了原文。
  [可复查的题名查询](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=TITLE:%22Calculation%20of%20Astigmatism%20Correction%22&format=json)。
- Haigis 2009，*IOL calculation using paraxial matrix optics*，
  Ophthalmic Physiol Opt. 29(4):458–463，
  [PMID 19523090](https://pubmed.ncbi.nlm.nih.gov/19523090/)，
  doi:10.1111/j.1475-1313.2008.00629.x。公开摘要确认用近轴矩阵处理
  IOL、目标屈光及厚/薄透镜。本模块下述式子由主平面聚散度关系推导，
  未声称逐式转录该文全文。
- Fabian & Wehner 2019，J Refract Surg. 35(6):362–368，
  [PMID 31185101](https://pubmed.ncbi.nlm.nih.gov/31185101/)，
  doi:10.3928/1081597X-20190422-02。公开摘要确实比较 Haigis-T 使用 K
  与含后表面的 TK，支持区别 K 与 TK 的处理；未公开 PCA 估算系数。
  本模块的总散光输入仅替换散光矢量，不复现该研究的整套 TK 球镜计算。
- Koch 等 2012，*Contribution of posterior corneal astigmatism to total
  corneal astigmatism*，J Cataract Refract Surg. 38(12):2080–2087，
  [PMID 23069271](https://pubmed.ncbi.nlm.nih.gov/23069271/)，
  doi:10.1016/j.jcrs.2012.08.036。公开摘要报告 PCA 平均量值 −0.30 D、
  后表面曲率陡轴多数垂直，并指出忽略 PCA 会使 WTR 过矫、ATR 欠矫。
  这是群体研究，不能证明 Haigis-T 使用固定 0.30 D 或固定轴位。
- [EyeWiki 生物测量总表](https://eyewiki.org/Biometry_for_Intra-Ocular_Lens_(IOL)_Power_Calculation)
  只用于核对 ELP、角膜屈光力与近轴光学的一般框架，未据其推定
  Haigis-T 专属系数。此次 CRST 检索未取得可核实的 Haigis-T 公式正文，
  未把其作为数值系数的依据。

### 6.2 输入参数

以下眼部字段位于 `right_eye` / `left_eye`；`haigis_constants` 等在请求级。
AL、K、ACD、目标屈光、三常数使用已有类型与医学范围校验。
K1/K2 分别校验 30–60 D，K2≥K1，规则散光要求两轴正交；
0 和 180 度等价，轴归一到 [0,180)。数值拒绝布尔值、NaN 和无穷大。

| 参数 | 单位/约定 | 缺省与用途 |
|---|---|---|
| `AL` | mm，12–38 | 必填 |
| `K1`, `K2` | 前表面角膜曲率计 D，K-index 由请求指定 | 必填，球镜使用两者平均值 |
| `K1Axis`, `K2Axis` | 度，K1 弱、K2 强子午线 | 必填；只支持规则散光 |
| `ACD` | 术前实测 mm，0.5–8 | 必填，保留两位小数；不回退到假定 ACD |
| `haigis_constants` | 请求级 `{a0,a1,a2}`，沿用已有范围 | 完整三常数必填，不由 A 常数推导 |
| `k_index` | 请求级 1.3375 / 1.332 | 默认 1.3375，先恢复同一角膜半径 |
| `a_constant` | 请求级，沿用通用解析与两位小数 | 优化三常数已提供，因此不参与求解 |
| `Refraction` | 眼镜平面目标 SE，D | 默认 0；沿用 Haigis 的 12 mm 顶点换算 |
| `iol_cylinder` | IOL 平面非负柱镜量值，D | 默认 0，用于实际植入残余预测 |
| `iol_axis` | IOL **光学弱子午线**对齐方向，度 | 非零 `iol_cylinder` 时必填 |
| `iol_spherical_equivalent` | IOL 平面 SE，−10–45 D | 默认 Haigis 球镜表的推荐 SE；可传实际植入 SE |
| `posterior_mode` | `none` / `measured` / `estimated` / `total` | 默认 `none`，明确警告未计入 PCA |
| `posterior_cylinder`, `posterior_axis` | 等效角膜平面光学 PCA 非负量值/强子午线 | `measured` 时两者必填；其他模式传入会报错 |
| `total_cylinder`, `total_axis`, `total_source` | 等效角膜平面总散光量值/强子午线；来源 `TK` / `TCRP` | `total` 时三者必填；替换前表面/PCA，防止重复叠加 |
| `incision_sia`, `incision_location` | 角膜平面扁平化量 D / 切口位置 0–360 度 | 默认量值 0；非零时位置必填，SICA 沿切口子午线减去 |
| `cylinder_powers` | IOL 平面可供的非负柱镜档位数组 | 调用者提供；去重排序，最低残余档位唯一推荐；未提供时只返回连续解 |
| `step` | 请求级球镜表步长，D | 默认 0.5；不是散光柱镜档距 |
| `LenThickness`, `WTW` | mm | 不参与 Haigis-T，结果中列为忽略 |

`iol_axis` 是光学弱子午线约定，不能未经核对就当作任意厂商的刻线方向。
若实际产品标注的是球镜基底度数，须先按该产品定义转成 SE 再传入
`iol_spherical_equivalent`，否则柱镜两子午线中心度数会不同。

后表面因折射率差为负，其曲率陡轴不等于光学强子午线；例如后表面
曲率垂直更陡的典型 PCA，在本接口中表达为 ATR 光学量值 @0 度。
`posterior_cylinder` 和 `total_cylinder` 必须已按设备测量定义校准到
等效角膜平面 D。不能把后表面曲率差直接当光学 D，也不能未经校准
混用 TK/TCRP 不同区域、算法或折射率定义下的输出。本模块不从一个
总散光量值猜测后表面球镜屈光力；`total` 模式球镜仍使用前表面平均 K。

### 6.3 双角矢量与近轴换算

通用算术位于 `common.astigmatism_vector` / `vector_astigmatism`。
当前 `barrett_toric.py` 是官网适配器，没有本地双角矢量工具可复用；
保留其 K1/K1Axis、K2/K2Axis 与切口字段约定，不改变在线爬虫路径。

使用全柱镜矢量（不是 J0/J45 半柱镜量值）：

```text
v(C, a) = (C*cos(2a), C*sin(2a))
Ca = Haigis_K(K2) - Haigis_K(K1)
Vnet = v(Ca,K2Axis) + Vpca - v(SICA,incision_location)
Vnet(total) = v(total_cylinder,total_axis) - v(SICA,incision_location)
Vresidual = Vnet - v(C_IOL*factor,iol_axis)
```

其中两条前表面 K 均先归一到 1.3375，再沿用 `haigis.py` 的
`Haigis_K(K)=K*331.5/337.5`。这使无 PCA/SICA 的两子午线与既有 Haigis
光学传播一致；商用 Haigis-T 是否对散光同样换算，尚未取得一手确认。
实测 PCA/总散光已是等效角膜平面量值，不再次应用这项 K-index 换算。

光线用 `(height, n*angle)` 表示，平移矩阵 `T(l,n)=[[1,l/n],[0,1]]`，
等效薄透镜矩阵 `L(P)=[[1,0],[-P,1]]`，长度在此用 m。
IOL 的主平面位置直接取现有 Haigis ELP：

```text
d_mm = a0 + a1*ACD + a2*AL
t = d_mm/1336
u = (AL-d_mm)/1336
B = 1/u - P_SE
G(B) = B/(1+t*B)
```

`G` 是把 IOL 前的所需聚散度传播回角膜平面的量。
IOL 两子午线功率为 `P_SE ± C_IOL/2`，相减得：

```text
h = 1+t*B
C_cornea = G(B+C_IOL/2) - G(B-C_IOL/2)
factor = C_cornea/C_IOL = 1/(h²-(t*C_IOL/2)²)
```

零柱镜时因子取连续极限 `1/h²`。当 `P_SE` 为 Haigis 的连续正视解，
极限为 `(1-d_mm*K_Haigis/1336)²`；因此因子受 ELP、球镜 SE 及柱镜量值
影响，并非固定 1/1.46。目标屈光通过 Haigis 推荐 SE 影响换算，
不改变 ELP；若显式固定实际 IOL SE，改变目标不改变其物理矫正能力。

推荐轴取净角膜散光强子午线，令 `C=|Vnet|`，解出的连续 IOL 柱镜为：

```text
C_IOL_exact = 2*C*h² / (1+sqrt(1+(C*t*h)²))
```

这是主平面近轴矩阵的化简，不猜测 IOL 厚度、材料折射率和前后曲面设计。
实测 PCA 与 SICA 按等效角膜平面矢量输入，不进行未知的厚角膜重建。
传播分母非正、ELP≤0、ELP≥AL、总散光使角膜主子午线屈光力非正时拒绝求解。

输出中 `residual_astigmatism` 是**实际植入柱镜与轴位**下的角膜平面
残余，包含非负 `cylinder`、光学强子午线 `axis`、矫正它的负柱镜处方轴
`minus_cylinder_axis=(axis+90)%180`、双角矢量和 `plane="corneal"`。
零残余的轴无定义，返回 null。该结果不是眼镜平面的柱镜处方。

`toric_options` 则在**推荐轴**上逐个评估可供柱镜，每行返回 IOL 柱镜、
角膜平面因子与等效矫正、残余及推荐标记；相同残余优先较低档位。
`iol_options` / `predicted_refraction` 仍为复用的 Haigis **球镜 SE**结果，
不把它伪装为含柱镜后的完整球柱镜术后处方。

### 6.4 UNVERIFIED-PENDING-PRIMARY 清单

| 项目 | 当前状态与行为 |
|---|---|
| `ESTIMATED_PCA_CYLINDER=0.30 D` | Koch 2012 支持群体平均量值；作为固定个体代理、以及是否属于 Haigis-T 算法均 **UNVERIFIED-PENDING-PRIMARY** |
| `ESTIMATED_PCA_AXIS=0°`（ATR 光学强子午线） | 根据后表面负屈光力及多数曲率陡轴垂直推定的简化；固定所有个体轴位 **UNVERIFIED-PENDING-PRIMARY** |
| 两子午线沿用 `331.5/337.5` | 来自已有 Haigis 球镜约定；扩展到商用 Haigis-T 散光是否一致 **UNVERIFIED-PENDING-PRIMARY** |
| 本模块的近轴矩阵化简与总散光替换路径 | 是可复查的公开光学推导/接口扩展；与任务所列 2015 原文及商用 Haigis-T 的逐式对应 **UNVERIFIED-PENDING-PRIMARY** |

PCA 代理仅在 `posterior_mode="estimated"` 时使用，同时在响应中警告。
默认 `none` 没有任何隐藏的 PCA 定值。没有额外的 Haigis-T 回归系数、
固定 IOL/角膜柱镜比、厂商柱镜库存或从 A 常数猜测的三常数。
实测 PCA 路径可避开固定 PCA 代理，但仍保留完整一手算法未核实的标记。

### 6.5 可运行示例与验证边界

POST `/api/calculate` 的示例请求（未启用 PCA 代理）：

```json
{
  "model": "haigis-toric",
  "haigis_constants": {"a0": 1.4, "a1": 0.4, "a2": 0.1},
  "right_eye": {
    "AL": 24, "ACD": 3,
    "K1": 44, "K1Axis": 0, "K2": 46, "K2Axis": 90,
    "Refraction": 0,
    "iol_spherical_equivalent": 20,
    "iol_cylinder": 3, "iol_axis": 90,
    "posterior_mode": "none",
    "incision_sia": 0,
    "cylinder_powers": [0, 1.5, 2.25, 3, 3.75]
  }
}
```

可在本地同步运行同一例子，无须启动 Worker：

```bash
PYTHONPATH=src uv run python - <<'PY'
from formula import calculate_formula

r = calculate_formula(
    "haigis-toric", 24, 45, acd=3,
    constants={"a0": 1.4, "a1": 0.4, "a2": 0.1},
    k1=44, k2=46, k1_axis=0, k2_axis=90,
    iol_spherical_equivalent=20, iol_cylinder=3, iol_axis=90,
    cylinder_powers=[0, 1.5, 2.25, 3, 3.75],
)
print(r["elp"], r["corneal_factor"], r["residual_astigmatism"])
PY
```

手算：ELP=5 mm；`h=1.1883075953356445`；3 D IOL 柱镜的因子为
`0.7081935166422379`，对应角膜平面矫正 `2.124580549926714 D`。
前表面有效散光 `1.9644444444444444 D@90°`，残余为
`0.1601361054822692 D@0°`（ATR 光学强子午线，负柱镜处方轴 90°）。
这组输入下可供档位推荐为 3 D；它是合成手算参考，**不是发表的临床样本**。

`tests/test_haigis_toric.py` 验证 WTR/ATR/斜轴双角矢量、手算参考、
独立逐面光线传播、球镜复用、ELP/目标敏感性、旋转协变、IOL 错轴、
连续解抵消、SICA 扁平化方向、忽略 PCA 的 WTR 过矫/ATR 欠矫、
TK/TCRP 总散光禁止重复 PCA、输入边界、AI 常数到调度、双眼 API 与零网络。
这些测试证明算术和接口一致性，不等于设备等价性或临床准确度验证。

## 7. 常数来源：ULIB 快照与 A 常数换算的边界

### 7.1 常数从哪来

IOLMaster 的优化常数不是蔡司自行维护的数据，而是来自公开的 ULIB
（User Group for Laser Interference Biometry，Wolfgang Haigis）。链条是：

```text
临床数据 -> ULIB（2016-10-31 停更）-> 打包进 IOLMaster
         -> IOLCon（2017 年起，Steinbeis / Saarland 大学）作为后继平台
```

- ULIB 常数表：http://www.ocusoft.de/ulib/c1.htm
- ULIB 常数换算器：http://ocusoft.de/scripts2/ciolc.php
- IOLCon（后继平台）：https://iolcon.org

ULIB 表每款晶体给出：名义 A、Haigis a0/a1/a2、Hoffer Q pACD、
Holladay 1 SF、SRK/T A、SRK II A、样本量 n，以及文献编号。
本项目的 `src/formula/data_ulib.py` 是它的**事实字段快照**（304 条），
不含原页面的文献编号列与晶体别名对照表。

### 7.2 Barrett 型号 → ULIB 的手工映射

Barrett 官网下拉是固定的一小份清单（文献记载 18 个），每款带一个
Lens Factor；不在清单里的晶体走「A 常数 → 自动换算 LF」。ULIB 是另一套
命名体系（旧厂名 + 完整型号串），收 304 款。

两者**没有稳定的自动映射规则**。实测按名称直接匹配只命中 21/304，按
`(pACD, SF)` 双值指纹匹配命中 66/304 但大量多义（一款 ULIB 条目会撞上
十几个型号）。因此 `src/formula/data_model_map.py` 逐条人工对照：

| 类型 | 数量 | 含义 |
|---|---:|---|
| `exact` | 6 | 同一款晶体，型号完全对应 |
| `series` | 5 | 系列型号与 ULIB 合并条目对应（如 SN6AD → SN6AD1/3） |
| 无（None） | 7 | ULIB 未收录或型号不同，**不做近似替代** |

无法映射的 7 个（`Alcon SND1Tx`、`Alcon MN60MA`、`AMO ZCT`、
`AMO AR40M`、`Hoya iSert 351`、`Bausch & Lomb BL1UT`、
`Bausch & Lomb LI60AO`）在表里写 `None` 并注明原因，绝不挑"最接近的
那一款"。

### 7.3 计算时的常数选择规则

```text
Barrett（离线/在线/Toric）  -> 用自己的 Lens Factor，不读 ULIB
                              （ULIB 表内根本没有 LF 列）

SRK/T、Hoffer Q、Haigis     -> 型号能映射到 ULIB 时用 ULIB 优化常数
   型号无映射 / 未选型号    -> 退回 A 常数按厂商标准关系换算（并标注来源）
```

覆盖范围（`src/formula/formula.py:_resolve_offline_constants`）：

| 公式 | 型号映射命中时改用 |
|---|---|
| SRK/T | ULIB 优化后的 SRK/T A |
| Hoffer Q | ULIB 优化后的 pACD |
| Haigis / Haigis-T | ULIB 的 a0 / a1 / a2 |

**声明了型号就以型号为准**：请求里带了能命中 ULIB 的 `iol_model` 时，
同类的 `a_constant` / `hoffer_q_pacd` / `haigis_constants` 直接被屏蔽，
不再参与计算；没有声明型号时才按请求给的常数算。ULIB 恰好缺某一项时
回落到请求值，并在 `warnings` 中说明来源混杂。

Haigis-T 因此有两种给常数的路径：直接给 `haigis_constants`，或给一个
命中 ULIB 的 `iol_model` 让服务端查表。两者都没有时返回 400。

响应里的 `constants_source` 说明实际用了什么：

| 字段 | 含义 |
|---|---|
| `source` | `ulib`（型号映射命中）或 `a_constant_conversion`（退回换算） |
| `barrett_model` / `ulib_name` | Barrett 型号名与对应的 ULIB 条目名 |
| `match` | `exact` / `series` |
| `applied` | 型号提供并实际生效的字段，如 `["a_constant", "hoffer_q_pacd"]` |
| `ignored_request` | 被型号屏蔽的请求字段，如 `["a_constant"]` |
| `note` | 映射说明；退回换算时说明"不是晶体优化常数" |

每眼的 `ignored_inputs` 也会列出被屏蔽的字段，便于调用方核对。

实测（AL 23.5 / K 44.0 / ACD 3.2，`iol_model=AMO ZCB00`）：

| 公式 | 声明型号（A=119.3） | 不声明型号、A=118.8 |
|---|---|---|
| SRK/T | 21 D（A=119.3） | 20.5 D |
| Hoffer Q | 21 D（pACD=5.80） | 20.5 D |
| Haigis | 21 D（a0=−1.302） | 21.5 D（a0=1.78 近似） |

### 7.4 内置快照的用途

`GET /api/iol-models?model=<型号>` 先查型号映射，再查 ULIB 原始型号名，
未收录才回退 Barrett 官网。响应中的 `source` 字段标明数据来源：

| 字段 | 含义 |
|---|---|
| `a_constant` | 优先取 ULIB 优化后的 SRK/T A；快照缺该值时用名义 A |
| `haigis_constants` | `[a0, a1, a2]` 优化三常数，可直接填入计算请求 |
| `hoffer_q_pacd` | Hoffer Q 优化 pACD（mm） |
| `holladay1_sf` | Holladay 1 SF（本项目未实现 Holladay 1，仅作记录） |
| `srkt_a` / `srk2_a` | 两种 SRK 的优化 A |
| `nominal_a` | 厂商名义 A |
| `samples` / `preliminary` | 优化样本量；小于 50 时原页面标注 prelim。 |
| `source_revision` | 快照对应的 ULIB 修订日期 |

匹配规则刻意保守：宁可不命中，也不混用地区版本。例如
`Alcon SN60WF` 与 `Alcon SN60WF (Japan)` 的 Haigis 常数完全不同
（−0.769/0.234/0.217 对 −1.268/0.342/0.233）；`Alcon MA60MA` 有
(+) 与 (−) 两个版本，去掉正负标记后不会匹配到任何一条。

快照是固定文件，运行时不联网、不读取外部文件。更新需重新生成并经评审。

### 7.5 不要用 A 常数换算替代优化常数

ULIB 换算器把「优化常数关系」和「厂商标准关系」作为两套结果分别给出：

| 关系 | pACD | a0 | SF |
|---|---|---|---|
| 厂商标准关系 | 0.58357·A − 63.896 | 0.62467·A − 72.434 | 0.5663·A − 65.60 |
| 优化常数关系 | 0.51255·A − 55.677 | 0.5296·A − 61.925 | 0.5114·A − 59.33 |

`hoffer_q.PACD_SLOPE` / `PACD_INTERCEPT` 与 `haigis.A0_SLOPE` /
`A0_INTERCEPT` 采用的是**厂商标准关系**，这是缺常数时的兜底起点，不是
优化结果。同一 A 常数可以对应差异很大的优化常数（ULIB 中 A=118.0 对应
15 个不同的 Barrett LF），因此拿 A 常数反推 pACD/a0 只应视为近似。

实测差异（AL 23.5 mm、K 44.0 D、ACD 3.2 mm、target 0）：

| 公式 | A 常数近似 | ULIB 优化常数 |
|---|---|---|
| Haigis | a0=1.714 → 21.5 D | a0=−0.769 → 21.0 D |
| Hoffer Q | pACD=5.374 → 20.0 D | pACD=5.64 → 20.5 D |
| SRK/T | A=118.7 → 20.5 D | A=119.0 → 21.0 D |

Barrett 的 Lens Factor 同理：`barrett.a_constant_to_lens_factor` 的
线性式来自四组厂商常数对，ULIB 表本身不提供 LF，IOLCon 才给。需要精确
LF 时应显式传入，而不是由 A 常数推算。

## 8. 常数、适用域与临床限制

- 公式专属常数不能不加区分地相互代入。设备或晶体库提供优化常数时，
  应优先使用同一公式、同一晶体的常数。
- **不要用 A 常数去反查晶体**。ULIB 里名义 A 只有 32 个取值、SRK/T A 只有
  33 个，单个 A 值平均对应 9~11 款晶体；例如 SRK/T A=119.30 撞上 11 个
  型号，Haigis 度数跨度 0.48 D，选错看不出来。反查只能用 Haigis 三常数
  这类高区分度组合（66% 唯一）。
- 晶体型号选择 `AMO ZCB00` 这类**能映射到 ULIB 的名称**时，非 Barrett
  公式会自动采用优化常数；选 `Personal Constant` 或无法映射的型号时，
  常数来自 A 常数换算，两者相差可达 0.5 D 以上。响应中
  `constants_source.applied` 会标明实际替换了哪些字段。
- 当前通用舒适域为 AL 22–26 mm、K 38–48 D；超出时返回
  LOW_CONFIDENCE 和警告，不等于该公式在临床上绝对不可用。
- 超出硬边界或输入在物理上无法计算时拒绝返回推荐度数。
- 角膜屈光术后、圆锥角膜及其他特殊眼不能直接套用普通路径，需要专用方法。
- 本地公式用于估算和横向对照，不保证术后误差不超过某个固定值。
- 临床使用前仍需验证测量值、晶体常数、目标屈光度和公式选择。

## 9. 主要文献

- Barrett GD. Intraocular lens calculation formulas for new intraocular lens
  implants. J Cataract Refract Surg. 1987;13(4):389-396.
- Barrett GD. An improved universal theoretical formula for intraocular lens
  power prediction. J Cataract Refract Surg. 1993;19(6):713-720. PMID 8271166.
- Retzlaff JA, Sanders DR, Kraff MC. Development of the SRK/T intraocular lens
  implant power calculation formula. J Cataract Refract Surg.
  1990;16(3):333-340；Erratum 1990;16(4):528.
- Hoffer KJ. The Hoffer Q formula: a comparison of theoretic and regression
  formulas. J Cataract Refract Surg. 1993;19(6):700-712；
  Errata 1994;20(6):677、2007;33(2):193.
- Haigis W, Lege B, Miller N, Schneider B. Comparison of immersion ultrasound
  biometry and partial coherence interferometry for intraocular lens
  calculation according to Haigis. Graefes Arch Clin Exp Ophthalmol.
  2000;238(9):765-773.
- Haigis W. The Haigis Formula. In: Intraocular Lens Calculations.
  Springer; 2024. doi:10.1007/978-3-031-50666-6_41.

关于一份无法检索的 2021 年文献及社区实现审计，见
[校准报告第 3 节](calibration_report.md#3-公式出处审计重要)；项目不声称按该文实现。
