"""公式层公共类型：输入、请求、公式能力与异常。

API 层只负责把 HTTP JSON 转成这里的 dataclass；公式模块不再读取 request。
所有长度单位 mm，屈光度单位 D。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from . import common
from .holladay1 import SF_MAX, SF_MIN


class FormulaError(ValueError):
    """公式层可预期的输入/计算错误（API 映射为 400）。"""


class InputValidationError(FormulaError):
    """输入字段缺失、类型错误或超出物理范围。"""


class UnsupportedFormulaError(FormulaError):
    """未知公式名称。"""


class UnsupportedModeError(FormulaError):
    """公式不支持请求的执行方式。"""


class CalculationError(FormulaError):
    """公式在合法输入下仍然无法求解。"""


@dataclass(frozen=True)
class EyeInput:
    """一只眼的标准化输入。"""

    al: float
    k1: float
    k2: float
    acd: float | None = None
    target_refraction: float = 0.0
    lt: float | None = None
    wtw: float | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def k_mean(self) -> float:
        """K1/K2 的平均值（本地公式统一使用平均 K）。"""
        return (self.k1 + self.k2) / 2.0

    @classmethod
    def from_mapping(cls, value, eye_name="眼"):
        """把 API 的 eye 字典转换为 EyeInput；缺失字段保持 None。"""
        if value is None:
            return None
        if not isinstance(value, dict):
            raise InputValidationError(f"{eye_name}参数必须是JSON对象")

        al = common.as_float(value.get("AL"), f"{eye_name}AL")
        k1 = common.as_float(value.get("K1"), f"{eye_name}K1")
        k2 = common.as_float(value.get("K2"), f"{eye_name}K2")
        acd = common.parse_optional_float(value.get("ACD"), f"{eye_name}ACD")
        if acd is not None:
            acd = round(acd, 2)
        target = common.parse_optional_float(
            value.get("Refraction"), f"{eye_name}Refraction", 0.0
        )
        lt = common.parse_optional_float(
            value.get("LenThickness"), f"{eye_name}LenThickness"
        )
        wtw = common.parse_optional_float(value.get("WTW"), f"{eye_name}WTW")

        # 在 API 边界完成物理范围校验（在线/离线都适用）。
        common.validate_eye(al, (k1 + k2) / 2.0)
        acd, lt, wtw, target = common.validate_optional_measurements(
            acd=acd,
            lt=lt,
            wtw=wtw,
            target=target,
        )
        return cls(
            al=al,
            k1=k1,
            k2=k2,
            acd=acd,
            target_refraction=target,
            lt=lt,
            wtw=wtw,
            raw=dict(value),
        )

    def provided_inputs(self) -> dict:
        """返回用户实际提交的核心输入（未提供的字段为 None）。"""
        return {
            "AL": self.al,
            "K1": self.k1,
            "K2": self.k2,
            "ACD": self.acd,
            "Refraction": self.target_refraction,
            "LenThickness": self.lt,
            "WTW": self.wtw,
        }

    def online_params(self) -> dict:
        """转换为官网适配器使用的参数字典。

        保留原始字典中的扩展字段；核心字段使用标准化后的数值。
        ACD 缺失时不写入键，让官网适配器按其既有规则处理缺省值。
        """
        data = dict(self.raw)
        data["AL"] = self.al
        data["K1"] = self.k1
        data["K2"] = self.k2
        data["Refraction"] = self.target_refraction
        data["LenThickness"] = "" if self.lt is None else self.lt
        data["WTW"] = "" if self.wtw is None else self.wtw
        if self.acd is None:
            data.pop("ACD", None)
        else:
            data["ACD"] = self.acd
        return data


@dataclass(frozen=True)
class HaigisConstants:
    """Haigis 优化后的三常数；提供后不再用 A 常数推导 a0。"""

    a0: float
    a1: float
    a2: float

    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict):
            raise InputValidationError("haigis_constants 必须是JSON对象")
        try:
            a0 = common.as_float(value.get("a0"), "haigis_constants.a0")
            a1 = common.as_float(value.get("a1"), "haigis_constants.a1")
            a2 = common.as_float(value.get("a2"), "haigis_constants.a2")
        except ValueError as exc:
            raise InputValidationError(str(exc)) from exc
        if not -10.0 <= a0 <= 10.0:
            raise InputValidationError("haigis_constants.a0 超出合理范围 -10~10")
        if not -2.0 <= a1 <= 2.0:
            raise InputValidationError("haigis_constants.a1 超出合理范围 -2~2")
        if not -1.0 <= a2 <= 1.0:
            raise InputValidationError("haigis_constants.a2 超出合理范围 -1~1")
        return cls(a0=a0, a1=a1, a2=a2)


@dataclass(frozen=True)
class CastropConstants:
    """Castrop 公式的 C/H/R 三常数，取自 IOLCon 的 `Castrop(C / H / R)` 列。"""

    c: float
    h: float
    r: float

    @classmethod
    def from_mapping(cls, value):
        if not isinstance(value, dict):
            raise InputValidationError("castrop_constants 必须是JSON对象")
        # IOLCon 页面上写作 C/H/R，也兼容小写与长名写法。
        aliases = {
            "c": ("C", "c", "castrop_c"),
            "h": ("H", "h", "castrop_h"),
            "r": ("R", "r", "castrop_r"),
        }
        parsed = {}
        for name, keys in aliases.items():
            raw = next((value[key] for key in keys if key in value), None)
            if raw in (None, ""):
                raise InputValidationError(
                    f"castrop_constants 缺少 {keys[0]}（需同时提供 C/H/R）"
                )
            try:
                parsed[name] = common.as_float(raw, f"castrop_constants.{keys[0]}")
            except ValueError as exc:
                raise InputValidationError(str(exc)) from exc
        if not 0.20 <= parsed["c"] <= 0.60:
            raise InputValidationError("castrop_constants.C 超出合理范围 0.20~0.60")
        if not -1.0 <= parsed["h"] <= 1.0:
            raise InputValidationError("castrop_constants.H 超出合理范围 -1.0~1.0")
        if not -1.0 <= parsed["r"] <= 1.0:
            raise InputValidationError("castrop_constants.R 超出合理范围 -1.0~1.0")
        return cls(c=parsed["c"], h=parsed["h"], r=parsed["r"])

    def to_dict(self):
        """转换为公式模块使用的 dict（键为 IOLCon 的 C/H/R 写法）。"""
        return {"C": self.c, "H": self.h, "R": self.r}


@dataclass(frozen=True)
class CalculationRequest:
    """IOL 计算请求；本地散光的扩展参数保留在 EyeInput.raw。"""

    right_eye: EyeInput | None
    left_eye: EyeInput | None
    a_constant: float = 119.30
    # 区分「调用方显式给了 A 常数」与「用了默认值」。型号已映射到 ULIB
    # 且调用方没给 A 常数时，才用 ULIB 的优化 A 替换默认值。
    a_constant_provided: bool = False
    k_index: float = common.K_INDEX_REF
    formula: str = "barrett"
    mode: str = "offline"
    model: str | None = None
    step: float = 0.5
    patient_name: str | None = None
    iol_model: str | None = None
    haigis_constants: HaigisConstants | None = None
    hoffer_q_pacd: float | None = None
    holladay1_sf: float | None = None
    castrop_constants: CastropConstants | None = None
    castrop_elp: float | None = None
    castrop_elp_model: str = "acd_lt"
    castrop_cct: float | None = None
    castrop_posterior_ratio: float | None = None
    castrop_al_correction: bool = True

    @classmethod
    def from_mapping(cls, body):
        """从 API JSON 对象构造请求，并在边界完成类型转换。"""
        if not isinstance(body, dict):
            raise InputValidationError("请求体必须是JSON对象")

        right_eye = EyeInput.from_mapping(body.get("right_eye"), "右眼")
        left_eye = EyeInput.from_mapping(body.get("left_eye"), "左眼")
        if right_eye is None and left_eye is None:
            raise InputValidationError("至少需要提供右眼或左眼参数")

        model = body.get("model")
        if model is not None:
            model = str(model).strip().lower()
            if not model:
                model = None

        formula = body.get("formula")
        formula = "barrett" if formula is None else str(formula).strip().lower()
        if not formula:
            formula = "barrett"

        mode = body.get("mode")
        mode = "offline" if mode is None else str(mode).strip().lower()
        if not mode:
            mode = "offline"

        legacy_supplied = any(
            key in body and body.get(key) not in (None, "")
            for key in ("formula", "mode")
        )
        if model is None and not legacy_supplied:
            raise InputValidationError(
                "必须指定 model：barrett_ii_offline, barrett_ii, srkt, "
                "hoffer_q, holladay1, haigis 或 haigis-toric"
            )

        # model 优先于 formula/mode；校验 haigis_constants 时用 model 推导的
        # 实际公式，避免只传 model=haigis 时被默认 formula="barrett" 拒绝。
        effective_formula = formula
        if model is not None:
            from . import formula as formula_module

            effective_formula, _ = formula_module.CALCULATION_MODELS.get(
                model, (formula, None)
            )

        raw_hoffer_q_pacd = body.get("hoffer_q_pacd")
        hoffer_q_pacd = None
        if raw_hoffer_q_pacd not in (None, ""):
            if effective_formula != "hoffer_q":
                raise InputValidationError("hoffer_q_pacd 只适用于 formula=hoffer_q")
            hoffer_q_pacd = common.parse_optional_float(
                raw_hoffer_q_pacd, "hoffer_q_pacd"
            )
            if not 0.0 <= hoffer_q_pacd <= 8.0:
                raise InputValidationError("hoffer_q_pacd 超出合理范围 0~8 mm")
            hoffer_q_pacd = round(hoffer_q_pacd, 2)

        # Holladay 1 的 SF 是公式常数（mm），与 Hoffer Q 的 pACD 同理，
        # 与 A 常数互斥：给了 SF 就不再由 A 常数换算。
        raw_holladay1_sf = body.get("holladay1_sf")
        holladay1_sf = None
        if raw_holladay1_sf not in (None, ""):
            if effective_formula != "holladay1":
                raise InputValidationError("holladay1_sf 只适用于 formula=holladay1")
            holladay1_sf = common.parse_optional_float(raw_holladay1_sf, "holladay1_sf")
            # 边界来自 ULIB 实测跨度（-7.08~10.29 mm），不是凭经验收窄的。
            if not SF_MIN <= holladay1_sf <= SF_MAX:
                raise InputValidationError(
                    f"holladay1_sf 超出合理范围 {SF_MIN:.0f}~{SF_MAX:.0f} mm"
                )
            holladay1_sf = round(holladay1_sf, 2)

        castrop_constants = None
        castrop_elp = None
        castrop_elp_model = "acd_lt"
        castrop_cct = None
        castrop_posterior_ratio = None
        castrop_al_correction = True
        castrop_keys = (
            "castrop_constants",
            "castrop_elp",
            "castrop_elp_model",
            "castrop_cct",
            "castrop_posterior_ratio",
            "castrop_al_correction",
        )
        if any(body.get(key) not in (None, "") for key in castrop_keys):
            if effective_formula != "castrop":
                raise InputValidationError("castrop_* 参数只适用于 formula=castrop")
            raw_castrop_constants = body.get("castrop_constants")
            if raw_castrop_constants not in (None, ""):
                castrop_constants = CastropConstants.from_mapping(raw_castrop_constants)
            castrop_elp = common.parse_optional_float(
                body.get("castrop_elp"), "castrop_elp"
            )
            if castrop_elp is not None and not 2.0 <= castrop_elp <= 12.0:
                raise InputValidationError("castrop_elp 超出合理范围 2.0~12.0 mm")
            raw_elp_model = body.get("castrop_elp_model")
            if raw_elp_model not in (None, ""):
                from . import castrop as castrop_module

                castrop_elp_model = castrop_module.normalize_elp_model(raw_elp_model)
            castrop_cct = common.parse_optional_float(
                body.get("castrop_cct"), "castrop_cct"
            )
            if castrop_cct is not None and not 0.3 <= castrop_cct <= 0.9:
                raise InputValidationError("castrop_cct 超出合理范围 0.3~0.9 mm")
            castrop_posterior_ratio = common.parse_optional_float(
                body.get("castrop_posterior_ratio"), "castrop_posterior_ratio"
            )
            if castrop_posterior_ratio is not None and not (
                0.6 <= castrop_posterior_ratio <= 0.95
            ):
                raise InputValidationError(
                    "castrop_posterior_ratio 超出合理范围 0.60~0.95"
                )
            raw_al_correction = body.get("castrop_al_correction")
            if isinstance(raw_al_correction, bool):
                castrop_al_correction = raw_al_correction
            elif raw_al_correction not in (None, ""):
                raise InputValidationError("castrop_al_correction 必须是布尔值")

        patient_name = body.get("patient_name")
        iol_model = body.get("iol_model")
        raw_constants = body.get("haigis_constants")
        haigis_constants = None
        if raw_constants not in (None, ""):
            if effective_formula not in {"haigis", "haigis-toric"}:
                raise InputValidationError(
                    "haigis_constants 只适用于 formula=haigis/haigis-toric"
                )
            haigis_constants = HaigisConstants.from_mapping(raw_constants)
        raw_a_constant = body.get("a_constant")
        return cls(
            right_eye=right_eye,
            left_eye=left_eye,
            a_constant=common.parse_a_constant(raw_a_constant),
            a_constant_provided=raw_a_constant not in (None, ""),
            k_index=common.normalize_k_index(body.get("k_index")),
            formula=formula,
            mode=mode,
            model=model,
            step=common.parse_step(body.get("step", 0.5)),
            patient_name=str(patient_name) if patient_name is not None else None,
            iol_model=str(iol_model) if iol_model is not None else None,
            haigis_constants=haigis_constants,
            hoffer_q_pacd=hoffer_q_pacd,
            holladay1_sf=holladay1_sf,
            castrop_constants=castrop_constants,
            castrop_elp=castrop_elp,
            castrop_elp_model=castrop_elp_model,
            castrop_cct=castrop_cct,
            castrop_posterior_ratio=castrop_posterior_ratio,
            castrop_al_correction=castrop_al_correction,
        )


@dataclass(frozen=True)
class ToricCalculationRequest:
    """散光（Toric）计算请求；眼睛参数保留原始字典供官网适配器解析。"""

    right_eye: Mapping[str, Any] | None
    left_eye: Mapping[str, Any] | None
    a_constant: float = 119.30
    k_index: float = common.K_INDEX_REF
    cylinder_mode: str = "-ve"
    patient_name: str | None = None
    iol_model: str | None = None

    @classmethod
    def from_mapping(cls, body):
        if not isinstance(body, dict):
            raise InputValidationError("请求体必须是JSON对象")

        right_eye = body.get("toric_right_eye") or body.get("right_eye")
        left_eye = body.get("toric_left_eye") or body.get("left_eye")
        if right_eye is not None and not isinstance(right_eye, dict):
            raise InputValidationError("右眼参数必须是JSON对象")
        if left_eye is not None and not isinstance(left_eye, dict):
            raise InputValidationError("左眼参数必须是JSON对象")
        if not right_eye and not left_eye:
            raise InputValidationError("至少需要提供右眼或左眼散光参数")

        cylinder_mode = str(body.get("cylinder_mode") or "-ve").strip()
        if cylinder_mode not in {"+ve", "-ve", "+", "-"}:
            raise InputValidationError("cylinder_mode 只支持 +ve 或 -ve")

        patient_name = body.get("patient_name")
        iol_model = body.get("iol_model")
        return cls(
            right_eye=dict(right_eye) if right_eye else None,
            left_eye=dict(left_eye) if left_eye else None,
            a_constant=common.parse_a_constant(body.get("a_constant")),
            k_index=common.normalize_k_index(body.get("k_index")),
            cylinder_mode=cylinder_mode,
            patient_name=str(patient_name) if patient_name is not None else None,
            iol_model=str(iol_model) if iol_model is not None else None,
        )


@dataclass(frozen=True)
class FormulaCapabilities:
    """公式能力声明，供调度器和 API 文档使用。"""

    name: str
    label: str
    modes: tuple[str, ...]
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    ignored_inputs: tuple[str, ...]
    constants: str
    supports_toric: bool = False

    def to_dict(self) -> dict:
        """转换为可 JSON 序列化的字典。"""
        return asdict(self)


__all__ = [
    "CalculationError",
    "CalculationRequest",
    "CastropConstants",
    "EyeInput",
    "FormulaCapabilities",
    "FormulaError",
    "HaigisConstants",
    "InputValidationError",
    "ToricCalculationRequest",
    "UnsupportedFormulaError",
    "UnsupportedModeError",
]
