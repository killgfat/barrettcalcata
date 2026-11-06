"""IOL 常数查询：在内置 ULIB 快照里按型号名匹配。

本模块只做名称归一化、匹配和返回结构组装；数值来自 data_ulib.py 的
固定快照，运行时不联网、不读取外部文件。

匹配规则刻意保守：宁可不命中，也不把地区版本或不同晶体混用。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .data_model_map import BARRETT_MODEL_KEYS, BARRETT_TO_ULIB
from .data_ulib import (
    ULIB_PRELIMINARY_SAMPLE_SIZE,
    ULIB_SOURCE_REVISION,
    ULIB_SOURCE_URL,
    iter_rows,
)

__all__ = [
    "ULIB_SOURCE_REVISION",
    "ULIB_SOURCE_URL",
    "ULIBEntry",
    "count",
    "iter_entries",
    "list_models",
    "lookup",
    "lookup_constants",
    "lookup_for_barrett_model",
    "normalize_model_name",
    "resolve_model_constants",
    "short_index_size",
]

# 只保留加号：ULIB 用「(+)」「(+diopters)」「(-diopters)」区分不同晶体，
# 例如 Alcon MA60MA 的正负度数版本常数完全不同。保留 + 而把 - 当分隔符，
# 既能让两行保持可区分，又能容忍「ALCON-SN60WF」这类连字符写法。
_NON_ALNUM = re.compile(r"[^0-9a-z+]+")
_PARENTHESIS = re.compile(r"\([^)]*\)")


def normalize_model_name(model_name):
    """把型号名归一化为可比较键：小写并去掉标点与空白。"""
    if model_name is None:
        return ""
    return _NON_ALNUM.sub("", str(model_name).lower())


@dataclass(frozen=True)
class ULIBEntry:
    """ULIB 常数表中的一行。"""

    name: str
    nominal_a: float | None
    haigis_a0: float | None
    haigis_a1: float | None
    haigis_a2: float | None
    pacd: float | None
    sf: float | None
    srkt_a: float | None
    srk2_a: float | None
    samples: int | None

    @property
    def preliminary(self):
        """原页面把样本量小于 50 的条目标注为 preliminary。"""
        if self.samples is None:
            return False
        return self.samples < ULIB_PRELIMINARY_SAMPLE_SIZE

    @property
    def haigis(self):
        """Haigis 三常数；缺任一值返回 None。"""
        if None in (self.haigis_a0, self.haigis_a1, self.haigis_a2):
            return None
        return (self.haigis_a0, self.haigis_a1, self.haigis_a2)

    def warnings(self):
        """返回该条目需要注意的事项。"""
        items = []
        if self.preliminary:
            items.append(
                f"ULIB 条目 {self.name} 的样本量 n={self.samples} 小于 "
                f"{ULIB_PRELIMINARY_SAMPLE_SIZE}，原页面标注为 preliminary"
            )
        return items

    def to_dict(self):
        """转换为 ULIB 条目结构（保留 ULIB 原始字段名）。"""
        return {
            "name": self.name,
            "source": "ulib",
            "source_url": ULIB_SOURCE_URL,
            "source_revision": ULIB_SOURCE_REVISION,
            "samples": self.samples,
            "preliminary": self.preliminary,
            "nominal_a": self.nominal_a,
            "haigis": self.haigis,
            "pacd": self.pacd,
            "sf": self.sf,
            "srkt_a": self.srkt_a,
            "srk2_a": self.srk2_a,
            "warnings": self.warnings(),
        }

    def to_model_result(self):
        """转换为 /api/iol-models 的常数结果结构。"""
        # ULIB 提供的是优化后的 SRK/T A 常数；名义 A 只在缺失时兜底。
        a_constant = self.srkt_a if self.srkt_a is not None else self.nominal_a
        return {
            "a_constant": a_constant,
            "lens_factor": None,
            "source": "ulib",
            "source_revision": ULIB_SOURCE_REVISION,
            "ulib_name": self.name,
            "samples": self.samples,
            "preliminary": self.preliminary,
            "haigis_constants": self.haigis,
            "hoffer_q_pacd": self.pacd,
            "holladay1_sf": self.sf,
            "srkt_a": self.srkt_a,
            "srk2_a": self.srk2_a,
            "nominal_a": self.nominal_a,
            "warnings": self.warnings(),
        }


def iter_entries():
    """把 data_ulib.py 的原始行解析成条目。"""
    for row in iter_rows():
        name, nominal, haigis, pacd, sf, srkt, srk2, samples = row
        a0 = a1 = a2 = None
        if haigis is not None:
            a0, a1, a2 = haigis
        yield ULIBEntry(
            name=name,
            nominal_a=nominal,
            haigis_a0=a0,
            haigis_a1=a1,
            haigis_a2=a2,
            pacd=pacd,
            sf=sf,
            srkt_a=srkt,
            srk2_a=srk2,
            samples=samples,
        )


def _build_indexes():
    """建立整名索引与去括号短名索引。

    短名（去掉括号后缀）只有在唯一对应一个条目时才可用；同名不同地区
    版本会相互冲突，此时全部剔除，避免把 (Japan) 版本当成基础型号。
    """
    exact = {}
    short = {}
    conflicted = set()
    for entry in iter_entries():
        exact[normalize_model_name(entry.name)] = entry
        short_key = normalize_model_name(_PARENTHESIS.sub(" ", entry.name))
        if not short_key:
            continue
        existing = short.get(short_key)
        if existing is not None and existing.name != entry.name:
            conflicted.add(short_key)
        else:
            short[short_key] = entry
    for key in conflicted:
        short.pop(key, None)
    return exact, short


_EXACT_INDEX, _SHORT_INDEX = _build_indexes()


def count():
    """返回内置快照收录的晶体条目数。"""
    return len(_EXACT_INDEX)


def short_index_size():
    """返回可用于短名匹配的条目数（冲突项已剔除）。"""
    return len(_SHORT_INDEX)


def lookup(model_name):
    """按型号名查 ULIB 常数；未收录返回 None。

    匹配顺序：整名（忽略大小写、标点、空白）→ 去掉括号后缀的短名。
    都不命中时返回 None，不做模糊猜测。
    """
    key = normalize_model_name(model_name)
    if not key:
        return None
    entry = _EXACT_INDEX.get(key)
    if entry is not None:
        return entry
    short_key = normalize_model_name(_PARENTHESIS.sub(" ", str(model_name)))
    if not short_key:
        return None
    return _SHORT_INDEX.get(short_key)


def lookup_constants(model_name):
    """返回型号对应的常数包，未收录时返回 None。"""
    entry = lookup(model_name)
    if entry is None:
        return None
    return entry.to_dict()


def list_models():
    """返回精简的晶体列表，供前端做关键词搜索与型号选择。

    每项只带计算真正用得上的常数，去掉地区别名之外的冗余字段，
    控制传输体积（304 条约 30 KB）。
    """
    models = []
    for entry in iter_entries():
        models.append(
            {
                "name": entry.name,
                # 计算时优先用优化后的 SRK/T A，缺失才回退名义 A。
                "a_constant": (
                    entry.srkt_a if entry.srkt_a is not None else entry.nominal_a
                ),
                "haigis": list(entry.haigis) if entry.haigis else None,
                "pacd": entry.pacd,
                "sf": entry.sf,
                "samples": entry.samples,
                "preliminary": entry.preliminary,
            }
        )
    models.sort(key=lambda item: item["name"].lower())
    return models


def resolve_model_constants(model_name):
    """把任意来源的型号名解析为 ULIB 常数包。

    Web UI 的 ULIB 选择器传的是 ULIB 原始型号名，API 调用方可能传 Barrett
    型号名，这里统一处理，避免把「ULIB 原名」误判成「未映射」。

    返回 dict 或 None，结构与 lookup_for_barrett_model 一致，另外用
    matched_by 标明匹配方式：
      "barrett_model"  经 Barrett 型号映射表命中
      "ulib_name"      直接命中 ULIB 原始型号名
    """
    mapped = lookup_for_barrett_model(model_name)
    if mapped is not None:
        mapped["matched_by"] = "barrett_model"
        return mapped

    entry = lookup(model_name)
    if entry is None:
        return None
    result = entry.to_model_result()
    result["barrett_model"] = None
    result["match"] = "ulib_name"
    result["note"] = ""
    result["matched_by"] = "ulib_name"
    return result


def lookup_for_barrett_model(barrett_model_name):
    """按 Barrett 官网型号名查对应的 ULIB 条目。

    映射关系写在 data_model_map.py，是逐条人工对照的结果。未建立映射时
    返回 None，调用方应回退到 A 常数换算路径，而不是猜一个最接近的型号。

    返回 dict，字段名与 ULIBEntry.to_model_result() 一致（即
    /api/iol-models 的输出结构），另外附加：
      barrett_model  Barrett 下拉里的原始名称
      match          "exact" 或 "series"
      note           映射说明（系列合并等）
    """
    key = normalize_model_name(barrett_model_name)
    if not key:
        return None
    canonical = BARRETT_MODEL_KEYS.get(key)
    if canonical is None:
        return None
    for name, ulib_name, match, note in BARRETT_TO_ULIB:
        if name != canonical or ulib_name is None:
            continue
        entry = lookup(ulib_name)
        if entry is None:
            return None
        result = entry.to_model_result()
        result["barrett_model"] = name
        result["match"] = match
        result["note"] = note
        return result
    return None
