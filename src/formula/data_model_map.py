"""Barrett 官网型号 → ULIB 条目 的手工映射表。

背景
----
Barrett 官网计算器的型号下拉是固定的一小份清单（文献记载 18 个），
每款带一个 Lens Factor；不在清单里的晶体走「A 常数 → 自动换算 LF」。
ULIB 是另一套命名体系（旧厂名 + 完整型号串），收 304 款。

两者没有稳定的自动映射规则：实测按名称、按 (pACD, SF) 指纹匹配都不可靠。
因此这里逐条手工对照，宁可写 None，也不做模糊猜测。

收录原则
--------
1. 只在「能确定是同一款晶体」时建立映射；
2. 系列型号（如 SN6AD 对应 SN6AD1/SN6AD3）用 match="series" 标注；
3. ULIB 未收录或型号明显不同时写 None，并在 note 里说明原因；
4. ULIB 有多地区版本时，优先选样本量最大、无地区后缀的那条。

数据来源
--------
- Barrett 官网型号清单：catcalc 项目脚本里注释留存的 18 项下拉内容
  （https://github.com/Wingman4l7/catcalc），与 Hoffer/Savini 2024 年
  教科书 IOL Power Calculations 第 57 章「one of 18 IOL models」一致；
- ULIB 条目名为 src/formula/data_ulib.py 快照中的原始写法。
"""

# match 取值：
#   "exact"  —— 同一款晶体，型号完全对应
#   "series" —— 系列型号与 ULIB 合并条目对应（ULIB 把几个型号合并成一行）
#   None     —— ULIB 没有可安全对应的条目
BARRETT_TO_ULIB = (
    ("Alcon SN60WF", "Alcon SN60WF", "exact", ""),
    (
        "Alcon SN6AD",
        "Alcon ReSTOR SN6AD1/3",
        "series",
        "SN6AD 是系列名，ULIB 把 SN6AD1 与 SN6AD3 合并为一行的 n=885",
    ),
    (
        "Alcon SN6ATx",
        "Alcon Toric SN6AT(2-9)",
        "series",
        "x 表示柱镜度数 2~9，ULIB 合并统计",
    ),
    (
        "Alcon SND1Tx",
        None,
        None,
        "ULIB 未收录 SND1T 系列；Panoptix TFNT00 是另一款型号，不可替代",
    ),
    (
        "Alcon SV25Tx",
        "Alcon ReSTOR SV25T0",
        "series",
        "Barrett 的 x 对应 SV25T0 的 0（散光度数档）",
    ),
    ("Alcon SA60AT", "Alcon SA60AT", "exact", ""),
    (
        "Alcon MN60MA",
        None,
        None,
        "ULIB 只收录 MA60MA，MN60MA 是不同平台；两者的正/负度数版本常数差异极大，不可混用",
    ),
    ("AMO ZCB00", "AMO Tecnis 1 ZCB00", "exact", ""),
    (
        "AMO ZCT",
        None,
        None,
        "ULIB 未收录 Tecnis Toric（ZCT）系列",
    ),
    ("AMO AR40e", "AMO Sensar AR40E", "exact", ""),
    (
        "AMO AR40M",
        None,
        None,
        "ULIB 只有 AR40E 与 AR40；AR40M 是低度数版本，常数不同，不可替代",
    ),
    ("Zeiss 409M", "ZEISS CT ASPHINA 409M (Acri.Smart 46LC)", "exact", ""),
    (
        "Zeiss 709M",
        "ZEISS AT TORBI 709 MP",
        "series",
        "Barrett 的 709M 与 ULIB 的 AT TORBI 709 MP 是否同一款需人工确认",
    ),
    (
        "Hoya iSert 251",
        "Hoya iMics1 NY-60 Hoya iSert 250/251 (+)",
        "series",
        "ULIB 把 iSert 250 与 251 合并为一行",
    ),
    (
        "Hoya iSert 351",
        None,
        None,
        "ULIB 未收录 iSert 351；ULIB 的等价表把 351 toric 与 311 toric 视为同款，但两者都不在常数表内",
    ),
    ("Bausch & Lomb MX60", "Bausch&Lomb enVista MX60", "exact", ""),
    (
        "Bausch & Lomb BL1UT",
        None,
        None,
        "ULIB 未收录 BL1UT",
    ),
    (
        "Bausch & Lomb LI60AO",
        None,
        None,
        "ULIB 只有 LI61AO SofPort，与 LI60AO 不是同一代型号",
    ),
)

# 名称归一化后的快速索引，键为 (去标点小写)
BARRETT_MODEL_KEYS = {
    "".join(ch for ch in name.lower() if ch.isalnum()): name
    for name, _ulib, _match, _note in BARRETT_TO_ULIB
}

__all__ = [
    "BARRETT_MODEL_KEYS",
    "BARRETT_TO_ULIB",
]
