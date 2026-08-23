"""Barrett Universal II 表单参数配置。"""


DEFAULT_K_INDEX = 1.3375

# Barrett 页面显示的是折射率，表单提交的是不带前导 1 的内部值。
BARRETT_K_INDEX_VALUES = {
    1.3375: "337.5",
    1.332: "332",
}


def normalize_k_index(value=None):
    """标准化角膜K-index，并返回通用的折射率表示。"""
    if value is None:
        return DEFAULT_K_INDEX

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return DEFAULT_K_INDEX

    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("k_index 必须是有效数值") from exc

    for supported_value in BARRETT_K_INDEX_VALUES:
        if abs(normalized - supported_value) < 1e-9:
            return supported_value

    supported = ", ".join(str(item) for item in BARRETT_K_INDEX_VALUES)
    raise ValueError(f"k_index 只支持：{supported}")


def to_barrett_k_index_value(value=None):
    """将通用K-index转换为Barrett表单要求的值。"""
    normalized = normalize_k_index(value)
    return BARRETT_K_INDEX_VALUES[normalized]
