# 触发率评测记录

评测集：`trigger-evals.json`（10 条应触发 + 10 条不应触发）。

## 环境限制

本机 `claude` CLI 未登录（缺 `~/.claude/.credentials.json`，`claude -p` 返回空），
无法运行 skill-creator 的 `run_loop.py`（它依赖 `claude -p` 且每条跑 3 次）。
这里改用独立子代理做近似判断：只看 name + description + query，输出是否触发。
每条只判 1 次，所以有个位数噪声。

官方流程可用时按下面跑：

    cd ~/.agents/skills/skill-creator
    python -m scripts.run_loop \
      --eval-set <repo>/skills/iol-calculator/evals/trigger-evals.json \
      --skill-path <repo>/skills/iol-calculator \
      --model <model-id> --max-iterations 5

## 三轮结果

| 轮次 | 正向 | 负向 | 合计 | 说明 |
|---|---|---|---|---|
| 1 | 6/10 | 7/10 | 13/20 (65%) | 初版 description，纯关键词列举 |
| 2 | 9/10 | 10/10 | 19/20 (95%) | 改为描述「产出具体数值」并显式列排除项 |
| 3 | 9/10 | 10/10 | 19/20 (95%) | 补 #10 表述后复测 |

### 第一轮暴露的问题

漏触发：

- #7 SRK/T 与 Hoffer Q 差一度是否正常 —— 听似知识问答，但需调 API 才能判断
- #8 自己部署了实例想用它算度数 —— 初版未提自部署 / `IOL_API_BASE`

误触发：

- #13 为什么 K 值要用 1.3375 换算
- #17 ULIB 网站还能打开吗
- #20 Haigis 与 Haigis-L 的文献区别

三条都是关键词（角膜曲率 / ULIB / Haigis）命中、但只需概念解释的近似负例。

### 修复方式

把 description 从「列举领域词汇」改为「描述需要产出数值的动作」，并在结尾
显式列出不需要本技能的场景（公式原理、折射率换算、文献差异、查 ULIB 网站）。

### 第二轮残留

#10「报告里的 WTW 11.9 怎么填进计算」漏触发 —— 补了「拿着报告上的某个读数
问它该怎么填进计算、会不会影响结果」。

## 已知的边界用例

#9「散光 1.25D 的话 IOL 平面柱镜应该选哪个档」三轮判断为 触发 / 触发 / 不触发。
多次不一致说明它就在边界上：问的是选档规则，未给出患者生物测量值，模型可能认为
可以凭通用经验回答。若希望更稳命中，可在 description 里补「没有具体眼参数、
只问柱镜档位该怎么选」这类表述；但这也可能连带放大误触发，需重跑评测确认。
