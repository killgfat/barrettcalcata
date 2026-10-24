# IOL 公式计算层重构计划

> 本文仅描述后续重构方案，不代表这些修改已经实施。
> 核心原则：统一输入、输出和调度，但各公式保持独立算法，不相互拟合。

## 1. 重构目标

- [ ] 将普通晶体、Toric、本地公式和在线 Barrett 调用统一收纳到 src/formula/。
- [ ] 提供 src/formula/formula.py 作为唯一计算调度入口。
- [ ] API 只负责 HTTP 参数和响应，不再直接 import 或编排具体公式。
- [ ] 保留 AL、K1、K2、ACD、目标屈光度输入，加入可选 LT、WTW。
- [ ] 各公式根据自己的定义转换和使用参数，不共享公式专属光学逻辑。
- [ ] Barrett、SRK/T、Hoffer Q、Haigis 独立实现、独立验证。
- [ ] 不用 Barrett 数据或结果校准其他公式，不以“接近 Barrett”为验收标准。
- [ ] 在线失败不静默切换公式；实际使用的公式必须明确返回。

## 2. 目标目录

~~~text
src/
├── formula/
│   ├── __init__.py          # 仅导出公共管理接口
│   ├── formula.py           # 统一调度、能力检查、单双眼编排
│   ├── types.py             # 输入、输出、能力、异常等类型
│   ├── common.py            # 通用校验、取整、表格，不含公式算法
│   ├── barrett.py           # Barrett Offline 独立近似实现
│   ├── barrett_online.py    # Barrett 官网普通晶体在线适配器
│   ├── barrett_toric.py     # Barrett Toric 在线适配器
│   ├── srkt.py              # SRK/T 独立实现
│   ├── hoffer_q.py          # Hoffer Q 独立实现
│   ├── haigis.py            # Haigis 独立实现
│   └── iol_models.py        # 晶体型号和常数查询支持
├── api.py                   # HTTP 参数转换、错误码、响应结构
├── entry.py                 # 路由
├── docs.py                  # OpenAPI
└── webui.py                 # UI，不复制计算公式
~~~

- [ ] 以单数 src/formula/ 为新包，现有 src/formulas/ 仅作为迁移来源。
- [ ] 新路径验证通过后，删除旧公式目录和旧计算模块，不长期保留两套实现。
- [ ] 普通晶体与 Toric 使用不同请求类型，不强行共用 Toric 不需要的输入。

## 3. 统一输入契约

### 3.1 普通晶体输入

保留现有 right_eye、left_eye、a_constant、k_index、formula、mode 结构。

| 外部字段 | 内部字段 | 含义 | 规则 |
|---|---|---|---|
| AL | al | 眼轴，mm | 必填、有限数、范围校验 |
| K1 | k1 | 平坦 K，D | 必填 |
| K2 | k2 | 陡峭 K，D | 必填 |
| ACD | acd | 术前前房深度，mm | 是否必需由公式决定 |
| Refraction | target_refraction | 目标屈光度，D | 默认 0 |
| LenThickness | lt | 晶状体厚度，mm | 可选 |
| WTW | wtw | 白到白距离，mm | 可选 |

- [ ] 在 types.py 定义 EyeInput、CalculationRequest、CalculationResult 等类型。
- [ ] 在 API 边界完成字符串/空值/数值转换，公式模块不读取 HTTP request。
- [ ] 内部统一使用 lt，不再混用 LenThickness、LT、lens_thickness。
- [ ] 可计算 k_mean=(K1+K2)/2，但必须保留原始 k_index 和角膜半径换算信息。
- [ ] 不得在统一管理器里预先把所有 K 转成某个公式专用折射率。
- [ ] 缺少可选值时传 None，不传空字符串。
- [ ] NaN、Inf、布尔值、非法常数及超范围输入必须明确拒绝。

### 3.2 修正 ACD 缺失行为

- [ ] 移除 API 对所有公式统一静默填充 ACD=3.00 的行为。
- [ ] 将用户未提供 ACD 保留为 acd=None 传给公式层。
- [ ] Barrett 若为兼容旧行为采用默认值，应在 Barrett 模块内完成并返回警告。
- [ ] Haigis 优先要求实测 ACD；若允许缺省，必须降低置信度并标明不是实测值。
- [ ] 结果中记录实际使用的输入和默认值，避免用户误解。

### 3.3 按公式分配输入

| 公式 | 必需测量 | 可选或不使用 | 公式专属要求 |
|---|---|---|---|
| Barrett Offline | AL、K1/K2 | ACD、LT、WTW 可选 | 自己的 A/LF 与等效 ELP 近似 |
| Barrett Online | 按现有官网契约 | ACD、LT、WTW 按官网支持转发 | 保留官网字段和解析 |
| SRK/T | AL、K1/K2 | 不使用实测 ACD、LT、WTW | 自己的 A 常数、ELP 和光学公式 |
| Hoffer Q | AL、K1/K2 | 不使用实测 ACD、LT、WTW | 自己的 pACD 和 Q 修正 |
| Haigis | AL、K1/K2、ACD | 不使用 LT、WTW | a0/a1/a2，nC=1.3315 |

- [ ] 每个模块声明 FormulaCapabilities：mode、必需字段、可选字段、忽略字段和常数类型。
- [ ] 公式定义不使用的输入不得为了“利用数据”而加入算法。
- [ ] 可在结果中返回 ignored_inputs，说明某些字段为何未参与计算。
- [ ] 保留 a_constant 兼容输入，同时为 Haigis 优化三常数预留独立 constants 输入。
- [ ] 不用 Barrett Lens Factor 代替其他公式的专属常数。

## 4. 统一输出契约

- [ ] 顶层保留 formula、formula_label、mode、model、model_note、right_eye、left_eye。
- [ ] 每眼保留 biometry、constants、iol_options、recommended_power、predicted_refraction、elp、confidence、warnings。
- [ ] 增加 used_inputs，明确实际使用的 AL、K、ACD、LT、WTW、目标和常数。
- [ ] formula 始终表示实际完成计算的公式，不掩盖公式切换。
- [ ] Barrett Offline 才引用自己的 calibration_report，其他公式不得借用其精度报告。
- [ ] 没有真实晶体设计信息时，不对所有结果硬编码 optic="Biconvex"。
- [ ] 无法物理解算时返回明确错误，不生成貌似正常的推荐值。

## 5. formula.py 的职责

计划提供异步公共接口，以兼容同步本地计算和异步在线调用：

~~~python
async def calculate(request: CalculationRequest) -> CalculationResult:
    ...

async def calculate_toric(request: ToricCalculationRequest) -> ToricCalculationResult:
    ...
~~~

- [ ] 使用显式注册表维护 formula 名称与实现的映射。
- [ ] 负责名称标准化、能力检查、单双眼循环、offline/online 分发和结果组装。
- [ ] 本地公式直接调用；在线适配器必须 await，并保留超时和上游异常。
- [ ] 非 Barrett 的 online 请求必须在网络调用前拒绝。
- [ ] API 只 import formula 公共接口，不直接 import 各公式模块。
- [ ] formula.py 不实现 ELP、折射率转换、目标屈光度或术后屈光反解。
- [ ] 本阶段只支持显式公式选择；自动兜底若需要，另立策略并明确警告和返回字段。

## 6. 各模块实现计划

### 6.1 common.py 去公式化

- [ ] 只保留有限数校验、通用范围校验、取整、候选表和结果容器工具。
- [ ] 不在公共层决定公式折射率、ELP、目标屈光度或反解方法。
- [ ] 初版优先让每个公式模块自包含光学算法。
- [ ] 为 A 常数、ACD、AL、K、LT、WTW 和 ELP 增加物理合理性检查。
- [ ] 非法输入不得仍返回 confidence="OK"。

### 6.2 SRK/T

- [ ] 独立保留 LCOR、角膜宽度/高度、ACD const、视网膜厚度和 optical AL。
- [ ] 按论文及 erratum 使用完整常数并记录出处。
- [ ] 修复非零目标：ELP 只由术前 AL、K 和常数决定，不能使用 K′ 计算 ELP。
- [ ] 恢复 SRK/T 自己的目标屈光度项和术后屈光反解，不套用 Barrett 流程。
- [ ] 区分 ELP 阶段的 K/radius 与光学阶段的 nC=1.333。
- [ ] 用独立参考算例验证负、零、正 target。

### 6.3 Hoffer Q

- [ ] 独立保留 pACD、Q 修正、AL 截断和 +0.05 mm 处理。
- [ ] 核对 AL<=23 与 AL>23 分支及角度转弧度。
- [ ] AL 截断只用于 Q 部分，光学计算仍用原始 AL。
- [ ] 目标屈光度不得改变 ELP。
- [ ] 修正测试中 AL=23.5 分支描述错误的注释。
- [ ] 用 Hoffer 论文、errata 或可信独立实现做对数。

### 6.4 Haigis

- [ ] 独立实现 d=a0+a1*ACD+a2*AL。
- [ ] 光学部分使用 Haigis 自己的 nC=1.3315，不直接代入 K(1.3375)。
- [ ] 从原始 K-index 和 K 恢复角膜半径，再按 Haigis 规则换算。
- [ ] 目标屈光度和术后反解使用同一套 Haigis 光学参数。
- [ ] 标准模式保留 a1=0.4、a2=0.1 和 A→a0 换算，并标明未个体化。
- [ ] 支持传入验证后的 a0/a1/a2，避免与 a_constant 同时输入产生歧义。
- [ ] 缺失或非法 ACD、非法三常数必须明确报错或降级警告。

### 6.5 Barrett Offline

- [ ] 将现有 barrett_offline.py 核心迁入 formula/barrett.py，初期保持数值不变。
- [ ] 保留“等效 ELP 反演拟合、不是官方公式”的说明。
- [ ] 保持运行时零网络、零 numpy、零数据文件依赖。
- [ ] ekrbye/barrett-uii-data 仍只用于开发期 Barrett 校准和回归。
- [ ] 校准脚本更新 import 后重跑，确认迁移没有改变数值。

### 6.6 Barrett Online、Toric 和型号数据

- [ ] 将 barrett_calculate.py 的官网普通计算迁入 barrett_online.py。
- [ ] 将 barrett_toric_calculate.py 迁入 barrett_toric.py，保留轴位、SIA 和轴位图逻辑。
- [ ] 保留 ASP.NET 表单、cookies、超时、回退和 HTML 解析兼容性。
- [ ] 在线结果转换为统一结构，并明确 mode="online"。
- [ ] 上游失败返回明确错误，不未经授权切换其他公式。
- [ ] iol_models.py 作为支持模块管理，不混入公式数值算法。
- [ ] 所有在线测试 mock HTTP，不依赖真实官网。

## 7. 推荐迁移顺序

### 阶段 A：建立兼容基线

- [ ] 保存当前单眼、双眼、默认值、非零目标、LT/WTW、online 和 Toric 请求样例。
- [ ] 为 Barrett Offline/Online 建立兼容测试。
- [ ] 不把已发现错误的 SRK/T、Haigis 数值冻结为正确基线。
- [ ] 记录测试中需要迁移的 import 和 monkeypatch 目标。

### 阶段 B：建立新包和独立公式

- [ ] 新建 types.py、common.py、formula.py 和各独立实现。
- [ ] 先迁移 Hoffer Q，再修复 SRK/T、Haigis，最后接入 Barrett。
- [ ] 每个公式分别提交独立参考算例和输入域测试。

### 阶段 C：迁移在线模块并切换 API

- [ ] 迁移 Barrett Online、Toric 和型号支持。
- [ ] API 改为只调用 formula 公共接口。
- [ ] 保持 /api/calculate、/api/calculate-toric、/api/iol-models URL 不变。
- [ ] 新路径通过后删除旧文件和临时兼容 shim。

### 阶段 D：UI、文档和清理

- [ ] UI 支持公式及 offline/online 选择，默认行为保持 Barrett。
- [ ] UI 提供 ACD、LT、WTW，并说明各公式是否使用。
- [ ] 明确显示实际公式、模式、常数、置信度和警告。
- [ ] 更新 OpenAPI、README、模型限制和常数说明。
- [ ] 全仓搜索旧 import、旧路径和旧 monkeypatch，删除残留实现。

## 8. 验证计划

### 8.1 独立数值验证

- [ ] 每个公式覆盖参考眼、短眼、长眼、极端 K、不同常数和非零目标。
- [ ] 期望值来自论文、errata、可信独立实现或确认过的独立计算。
- [ ] 不得只把当前模块输出写死后称为“参考值”。
- [ ] SRK/T：验证 ELP 不随 target 改变及完整目标屈光度公式。
- [ ] Haigis：用同一角膜半径验证 nC=1.3315，并覆盖 ACD 和三常数。
- [ ] Hoffer Q：覆盖 AL=23、AL 截断和 m/g 分支。
- [ ] Barrett：迁移前后数值一致，并重跑校准回归。

### 8.2 通用性质和异常测试

- [ ] 正反解一致性只作为辅助测试，不能代替独立公式算例。
- [ ] 同一角膜半径、不同输入 K-index 时，符合各公式自己的换算规则。
- [ ] 目标变化时推荐度数方向合理，ELP 不随目标改变。
- [ ] 覆盖非法/缺失 ACD、非法常数、NaN/Inf、超界和物理分母异常。
- [ ] 覆盖 0.5 D 取整、推荐档唯一性和非零 target。
- [ ] 不要求不同公式结果必须接近 Barrett。

### 8.3 API 与网络测试

- [ ] 验证统一输出、实际 formula、used_inputs、警告和置信度。
- [ ] 验证 K1/K2、LenThickness、WTW、ACD、target 的转换和按需转发。
- [ ] 验证 Haigis 缺 ACD 不再被全局 3.00 默认值吞掉。
- [ ] 非 Barrett online 必须在网络调用前拒绝。
- [ ] 离线测试禁用或 mock 网络，证明零 HTTP。
- [ ] online/Toric 覆盖上游成功、异常、超时和 HTML 变化。

## 9. 验收命令与上线门槛

- [ ] uv run pytest tests/
- [ ] uv run ruff check src tests
- [ ] uv run ruff format --check src tests
- [ ] python scripts/calibrate_offline.py --no-download（仅 Barrett 校准回归）
- [ ] 本地启动 Worker，smoke test 三个计算/型号端点及 /docs。
- [ ] 确认部署包不包含 data/、校准数据集或 numpy 运行时依赖。
- [ ] 保持 wrangler.jsonc 与私有 Cloudflare 配置的既定隔离政策。
- [ ] 数值独立验证未完成前不部署为兜底路径。

## 10. 完成标准

- [ ] API 只通过 formula/formula.py 进入普通公式计算。
- [ ] 所有晶体计算和在线适配器均位于 src/formula/，旧实现已清理。
- [ ] 各公式没有共享公式专属 ELP、折射率或目标屈光度算法。
- [ ] SRK/T 非零目标和 Haigis nC=1.3315 问题有修复及独立算例。
- [ ] ACD 缺失不再被全局默认值静默处理。
- [ ] LT/WTW 按公式需求使用或明确忽略。
- [ ] 离线路径无网络和数据集依赖，在线路径全部可 mock。
- [ ] 测试、lint、Worker smoke test 和文档更新全部完成。
- [ ] 不存在静默公式替换、错误模型标签或精度夸大。
