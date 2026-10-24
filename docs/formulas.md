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

统一接口不表示各公式使用同一个光学核心：

- SRK/T 与 Hoffer Q 不使用术前实测 ACD、LT、WTW；
- Haigis 使用实测 ACD，不使用 LT、WTW；
- Haigis 光学部分使用自己的 nC=1.3315，不能直接代入 K(1.3375)；
- 目标屈光度不得改变由术前生物测量预测的 ELP；
- 不通过 Barrett 的结果拟合或修正其他公开公式。

## 2. Barrett Universal II

### 2.1 在线模式

barrett_ii 调用 Barrett 官方在线计算器，保留官网表单、会话和结果解析逻辑。
它不是本地公式，官网可用性及返回结构变化会影响该路径。

Toric 使用独立的 barrett_ii_toric 和 POST /api/calculate-toric，需要额外的
轴位、切口 SIA 等参数，不与普通晶体接口混用。

### 2.2 离线模式不是官方公式复刻

官方 Barrett Universal II 的完整 ELP 预测和厚透镜光线追迹未公开。
本地实现由两部分组成：

1. Gaussian 聚散度核心：

   ``P = 1336/(AL-ELP) - 1336/(1336/K'-ELP)
   ``

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
[校准报告](calibration_report.md)。数据保存在开发机未跟踪的 data/ 目录，
不进入部署包。

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

``pACD = 0.58357 × A - 63.896
``

随后根据 AL 和 K 做 Q 修正，并在光学计算中使用 ACD+0.05 mm。
实现保持以下规则：

- AL<=23 与 AL>23 使用不同的 M/G 分支；
- 正切计算先把角度转换为弧度；
- AL 截断只用于 Q/ELP 部分，光学部分仍使用原始 AL；
- 目标屈光度在光学部分处理，不改变患者 ELP。

术前实测 ACD 不等于 pACD；标准 Hoffer Q 不使用实测 ACD、LT、WTW。
当前接口由 A 常数推导 pACD，结果不应自动视为与任意设备晶体库的优化常数一致。

## 5. Haigis

实现位置：src/formula/haigis.py。

ELP 由三常数公式预测：

``d = a0 + a1×ACD + a2×AL
``

光学部分使用 Haigis 自己的角膜折射率 nC=1.3315。实现先根据原始输入
K-index 恢复角膜半径，再计算 Haigis 所需的角膜屈光度。

常数有两种来源：

1. **显式三常数**：请求传入 haigis_constants: {a0,a1,a2}，优先使用，
   此时不再从 A 常数推导 a0。应与 IOL Master 或晶体库中的具体晶体常数一致。
2. **标准近似起点**：固定 a1=0.4、a2=0.1，并由
   a0=0.62467×A−72.434 推导 a0。该结果不是个体化优化常数，
   与设备使用的晶体专属常数可能明显不同，结果会给出警告并降低置信度。

Haigis 应优先使用实测 ACD。未提供时使用明确的默认值并标记
ACD_defaulted、LOW_CONFIDENCE；默认值不能解释为患者的真实 ACD。

## 6. 常数、适用域与临床限制

- 公式专属常数不能不加区分地相互代入。设备或晶体库提供优化常数时，
  应优先使用同一公式、同一晶体的常数。
- 当前通用舒适域为 AL 22–26 mm、K 38–48 D；超出时返回
  LOW_CONFIDENCE 和警告，不等于该公式在临床上绝对不可用。
- 超出硬边界或输入在物理上无法计算时拒绝返回推荐度数。
- 角膜屈光术后、圆锥角膜及其他特殊眼不能直接套用普通路径，需要专用方法。
- 本地公式用于估算和横向对照，不保证术后误差不超过某个固定值。
- 临床使用前仍需验证测量值、晶体常数、目标屈光度和公式选择。

## 7. 主要文献

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
