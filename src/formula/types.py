"""公式层公共类型：输入、请求、公式能力与异常。

API 层只负责把 HTTP JSON 转成这里的 dataclass；公式模块不再读取 request。
所有长度单位 mm，屈光度单位 D。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from . import common


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
class CalculationRequest:
    """普通（非散光）IOL 计算请求。"""

    right_eye: EyeInput | None
    left_eye: EyeInput | None
    a_constant: float = 119.30
    k_index: float = common.K_INDEX_REF
    formula: str = "barrett"
    mode: str = "offline"
    step: float = 0.5
    patient_name: str | None = None
    iol_model: str | None = None
    haigis_constants: HaigisConstants | None = None

    @classmethod
    def from_mapping(cls, body):
        """从 API JSON 对象构造请求，并在边界完成类型转换。"""
        if not isinstance(body, dict):
            raise InputValidationError("请求体必须是JSON对象")

        right_eye = EyeInput.from_mapping(body.get("right_eye"), "右眼")
        left_eye = EyeInput.from_mapping(body.get("left_eye"), "左眼")
        if right_eye is None and left_eye is None:
            raise InputValidationError("至少需要提供右眼或左眼参数")

        formula = body.get("formula")
        formula = "barrett" if formula is None else str(formula).strip().lower()
        if not formula:
            formula = "barrett"

        mode = body.get("mode")
        mode = "offline" if mode is None else str(mode).strip().lower()
        if not mode:
            mode = "offline"

        patient_name = body.get("patient_name")
        iol_model = body.get("iol_model")
        raw_constants = body.get("haigis_constants")
        haigis_constants = None
        if raw_constants not in (None, ""):
            if formula != "haigis":
                raise InputValidationError("haigis_constants 只适用于 formula=haigis")
            haigis_constants = HaigisConstants.from_mapping(raw_constants)
        return cls(
            right_eye=right_eye,
            left_eye=left_eye,
            a_constant=common.parse_a_constant(body.get("a_constant")),
            k_index=common.normalize_k_index(body.get("k_index")),
            formula=formula,
            mode=mode,
            step=common.parse_step(body.get("step", 0.5)),
            patient_name=str(patient_name) if patient_name is not None else None,
            iol_model=str(iol_model) if iol_model is not None else None,
            haigis_constants=haigis_constants,
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
    "EyeInput",
    "FormulaCapabilities",
    "FormulaError",
    "HaigisConstants",
    "InputValidationError",
    "ToricCalculationRequest",
    "UnsupportedFormulaError",
    "UnsupportedModeError",
]
