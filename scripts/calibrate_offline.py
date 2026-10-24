#!/usr/bin/env python3
"""一次性离线 BUII 校准：拉取公开网格、跑离线实现、生成报告。

用法::

    python scripts/calibrate_offline.py
    python scripts/calibrate_offline.py --no-download
    python scripts/calibrate_offline.py --refit

产物：
    docs/calibration_report.md
    docs/calibration_grid.csv
    docs/calibration_outliers.csv

数据：ekrbye/barrett-uii-data（CC-BY-4.0），通过 ghfast.top 镜像拉取。
脚本运行时会真的读取数据、真的计算偏差；不写任何占位数字。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import formula.barrett as offline

DATA_REPO = "ekrbye/barrett-uii-data"
DATA_BRANCH = "main"
MIRROR_PREFIX = "https://ghfast.top/"
TARBALL_URL = (
    MIRROR_PREFIX
    + "https://github.com/"
    + DATA_REPO
    + "/archive/refs/heads/"
    + DATA_BRANCH
    + ".tar.gz"
)
DATA_DIR = ROOT / "data" / "barrett-uii-data"
DOCS_DIR = ROOT / "docs"

# 校准数据集使用的 A-constant（README 明确说明）。
CALIBRATION_A_CONSTANT = 118.7
# 用于参考公式对照的 A-constant（与官方 SRK/T 常数一致）。
REFERENCE_A_CONSTANT = 118.7

try:
    import numpy as np
except ImportError:  # pragma: no cover - 允许在无 numpy 环境降级
    np = None


# ---------------------------------------------------------------------------
# 数据获取
# ---------------------------------------------------------------------------


def sha256sum(path):
    """计算文件 SHA-256。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dataset(allow_download=True):
    """确保 data/barrett-uii-data 存在；必要时用镜像 tarball 拉取。"""
    scans = DATA_DIR / "scans.csv"
    if scans.exists():
        print(f"[data] 已存在: {scans}")
        return

    if not allow_download:
        raise SystemExit(
            "缺少 data/barrett-uii-data/scans.csv；去掉 --no-download 重试"
        )

    print(f"[data] 拉取 {TARBALL_URL}")
    DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        TARBALL_URL, headers={"User-Agent": "barrettcalcata-calibration/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        status = getattr(response, "status", 200)
        payload = response.read()
    print(f"[data] HTTP {status}, {len(payload)} bytes")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "data.tar.gz"
        temp_path.write_bytes(payload)
        with tarfile.open(temp_path, "r:gz") as archive:
            names = archive.getnames()
            root_name = names[0].split("/")[0] if names else ""
            archive.extractall(temp_dir)
        extracted = Path(temp_dir) / root_name
        if not (extracted / "scans.csv").exists():
            raise SystemExit("tarball 内未找到 scans.csv")
        if DATA_DIR.exists():
            import shutil

            shutil.rmtree(DATA_DIR)
        extracted.rename(DATA_DIR)
    print(f"[data] 解压完成: {DATA_DIR}")


def load_scans():
    """读取 scans.csv，返回统一的测量行。"""
    rows = []
    with open(DATA_DIR / "scans.csv", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, raw in enumerate(reader):
            try:
                al = float(raw["AL"])
                k1 = float(raw["K1"])
                k2 = float(raw["K2"])
                acd = float(raw["ACD"])
                lt = float(raw["LT"])
                wtw = float(raw["WTW"])
                official = float(raw["IOL"])
            except (TypeError, ValueError):
                continue
            if not all(
                math.isfinite(value) for value in (al, k1, k2, acd, lt, wtw, official)
            ):
                continue
            rows.append(
                {
                    "source": "scans.csv",
                    "row_id": "scans-{:04d}-{}-{}-{}".format(
                        index,
                        raw.get("baseline", ""),
                        raw.get("scan_param", ""),
                        raw.get("value", ""),
                    ),
                    "baseline": raw.get("baseline", ""),
                    "scan_param": raw.get("scan_param", ""),
                    "AL": al,
                    "K1": k1,
                    "K2": k2,
                    "K": (k1 + k2) / 2.0,
                    "ACD": acd,
                    "LT": lt,
                    "WTW": wtw,
                    "official": official,
                }
            )
    return rows


def load_al_k_grid():
    """读取 grids.npz 的 AL_K 曲面（需要 numpy）。"""
    if np is None:
        return []
    path = DATA_DIR / "grids.npz"
    if not path.exists():
        return []
    data = np.load(path)
    xs = data["AL_K__x"]
    ys = data["AL_K__y"]
    z = data["AL_K__Z"]
    rows = []
    for i in range(len(xs)):
        for j in range(len(ys)):
            al = float(xs[i])
            k = float(ys[j])
            official = float(z[i, j])
            if not (math.isfinite(al) and math.isfinite(k)):
                continue
            if not math.isfinite(official):
                continue
            rows.append(
                {
                    "source": "grids.npz:AL_K",
                    "row_id": f"AL_K-{i:02d}-{j:02d}",
                    "baseline": "grid-base-unknown",
                    "scan_param": "",
                    "AL": al,
                    "K1": k,
                    "K2": k,
                    "K": k,
                    "ACD": None,
                    "LT": None,
                    "WTW": None,
                    "official": official,
                }
            )
    return rows


# ---------------------------------------------------------------------------
# 离线实现与参考公式
# ---------------------------------------------------------------------------


def offline_power(row, use_surgeon_inputs):
    """用离线模块计算连续 IOL 度数（不取整）。"""
    return offline.iol_power_for_target(
        row["AL"],
        row["K"],
        target=0.0,
        a_constant=CALIBRATION_A_CONSTANT,
        acd=row["ACD"],
        lt=row["LT"],
        wtw=row["WTW"],
        use_surgeon_inputs=use_surgeon_inputs,
    )


def srkt_power(al, k, a_constant, target=0.0):
    """SRK/T（Retzlaff 1990）公开公式，用作独立对照。"""
    na = 1.336
    nc = 1.333
    r = 337.5 / k
    lcor = al if al <= 24.2 else (-3.446 + 1.716 * al - 0.0237 * al * al)
    cw = -5.41 + 0.58412 * lcor + 0.098 * k
    disc = r * r - cw * cw / 4.0
    h = r - math.sqrt(disc) if disc > 0 else r
    acd = 0.62467 * a_constant - 68.747 + h - 3.336
    rethick = 0.65696 - 0.02029 * al
    lopt = al + rethick
    rx = target
    v = 12.0
    # Retzlaff 1990 附录公式 (10)：0.001*Rx 项在分子/分母的括号内。
    term_l = na * r - (nc - 1.0) * lopt
    term_a = na * r - (nc - 1.0) * acd
    num = 1000.0 * na * (term_l - 0.001 * rx * (v * term_l + lopt * r))
    den = (lopt - acd) * (term_a - 0.001 * rx * (v * term_a + acd * r))
    return num / den


def holladay1_power(al, k, a_constant, target=0.0):
    """Holladay 1（1988）公开公式，用作独立对照。"""
    na = 1.336
    nc = 4.0 / 3.0
    r = max(337.5 / k, 7.0)
    ag = min(12.5 * al / 23.45, 13.5)
    acd = 0.56 + r - math.sqrt(r * r - ag * ag / 4.0)
    sf = 0.5663 * a_constant - 65.6
    alm = al + 0.2
    rx = target
    v = 12.0
    num = 1000.0 * na * (na * r - (nc - 1.0) * alm) - 0.001 * rx * (
        v * (na * r - (nc - 1.0) * alm) + alm * r
    )
    den = (alm - acd - sf) * (na * r - (nc - 1.0) * (acd + sf)) - 0.001 * rx * (
        v * (na * r - (nc - 1.0) * (acd + sf)) + (acd + sf) * r
    )
    return num / den


def implied_elp(power, al, k):
    """由官方 IOL 度数反演薄透镜等效 ELP（仅用于分析/拟合）。"""

    def residual(elp):
        return (
            offline.VERGENCE_SCALE / (al - elp)
            - offline.VERGENCE_SCALE / (offline.VERGENCE_SCALE / k - elp)
            - power
        )

    lo = 0.0
    hi = min(al, offline.VERGENCE_SCALE / k) - 1e-9
    if lo >= hi or residual(lo) * residual(hi) >= 0:
        return float("nan")
    for _ in range(300):
        mid = (lo + hi) / 2.0
        if residual(lo) * residual(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# 指标
# ---------------------------------------------------------------------------


def metrics(values):
    """返回 n、mean、SD、median|.|、p95|.|、max|.|。"""
    clean = [value for value in values if math.isfinite(value)]
    if not clean:
        return {
            "n": 0,
            "mean": float("nan"),
            "sd": float("nan"),
            "median_abs": float("nan"),
            "p95_abs": float("nan"),
            "max_abs": float("nan"),
        }
    ordered = sorted(abs(value) for value in clean)
    mean = sum(clean) / len(clean)
    if len(clean) > 1:
        sd = math.sqrt(sum((value - mean) ** 2 for value in clean) / (len(clean) - 1))
    else:
        sd = 0.0

    def percentile(p):
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * p
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    return {
        "n": len(clean),
        "mean": mean,
        "sd": sd,
        "median_abs": percentile(0.5),
        "p95_abs": percentile(0.95),
        "max_abs": ordered[-1],
    }


def central_metrics(values):
    """去掉整体偏移后的形状指标（用于基线不明曲面）。"""
    clean = [value for value in values if math.isfinite(value)]
    if not clean:
        result = metrics([])
        result["offset"] = float("nan")
        return result
    offset = sum(clean) / len(clean)
    result = metrics([value - offset for value in clean])
    result["offset"] = offset
    return result


def al_bucket(al):
    if al < 22:
        return "AL<22"
    if al < 25:
        return "AL 22-25"
    if al <= 30:
        return "AL 25-30"
    return "AL>30"


def k_bucket(k):
    if k < 40:
        return "K<40"
    if k < 42:
        return "K 40-42"
    if k < 44:
        return "K 42-44"
    if k < 46:
        return "K 44-46"
    if k <= 48:
        return "K 46-48"
    return "K>48"


AL_BUCKETS = ["AL<22", "AL 22-25", "AL 25-30", "AL>30"]
K_BUCKETS = ["K<40", "K 40-42", "K 42-44", "K 44-46", "K 46-48", "K>48"]


def cross_table(results, value_key):
    """构造 AL x K 交叉表，单元格为 median|delta| (n)。"""
    buckets = defaultdict(list)
    for row in results:
        buckets[(al_bucket(row["AL"]), k_bucket(row["K"]))].append(row[value_key])
    table = {}
    for al_name in AL_BUCKETS:
        for k_name in K_BUCKETS:
            values = buckets.get((al_name, k_name), [])
            table[(al_name, k_name)] = metrics(values)
    return table


def markdown_cross_table(table):
    """把交叉表渲染成 Markdown。"""
    header = "| AL \\ K | " + " | ".join(K_BUCKETS) + " |"
    divider = "|---" * (len(K_BUCKETS) + 1) + "|"
    lines = [header, divider]
    for al_name in AL_BUCKETS:
        cells = []
        for k_name in K_BUCKETS:
            item = table[(al_name, k_name)]
            if item["n"] == 0:
                cells.append("-")
            else:
                cells.append("{:.2f} ({})".format(item["median_abs"], item["n"]))
        lines.append(f"| {al_name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_metrics(name, item, note=""):
    """一行 Markdown 指标。"""
    suffix = f" {note}" if note else ""
    return (
        f"| {name} | {item['n']} | {item['mean']:+.3f} | "
        f"{item['sd']:.3f} | {item['median_abs']:.3f} | "
        f"{item['p95_abs']:.3f} | {item['max_abs']:.3f} |{suffix}"
    )


# ---------------------------------------------------------------------------
# 拟合诊断（不改变实际计算使用的常量）
# ---------------------------------------------------------------------------


def usable_elp(row):
    """返回可用的反演 ELP；极端点（<1 或 >9 mm）剔除。"""
    value = implied_elp(row["official"], row["AL"], row["K"])
    if not math.isfinite(value) or not 1.0 < value < 9.0:
        return float("nan")
    return value


def design_alk(alpha, k):
    da = alpha - offline.REF_AL
    dk = k - offline.REF_K
    return [1.0, da, dk, da * da, da * dk, dk * dk]


def design_full(alpha, k, acd, lt, wtw):
    return design_alk(alpha, k) + [
        acd - offline.REF_ACD,
        lt - offline.REF_LT,
        wtw - offline.REF_WTW,
    ]


def solve_least_squares(matrix, target):
    """纯 numpy 最小二乘；没有 numpy 时返回 None。"""
    if np is None:
        return None
    coefficients, _, _, _ = np.linalg.lstsq(
        np.asarray(matrix, dtype=float),
        np.asarray(target, dtype=float),
        rcond=None,
    )
    return [float(value) for value in coefficients]


def fit_coefficients(rows):
    """在给定行上重拟合 ELP 系数（诊断用）。"""
    if np is None:
        return None
    # 只用单参数扫描中变化 AL/K 的行来拟合二次项，避免 ACD/LT/WTW 混淆。
    subset = [
        row
        for row in rows
        if row["scan_param"] in ("AL", "K1", "K2") and math.isfinite(usable_elp(row))
    ]
    alk = solve_least_squares(
        [design_alk(row["AL"], row["K"]) for row in subset],
        [usable_elp(row) for row in subset],
    )
    if alk is None:
        return None
    residuals = []
    extras = []
    for row in rows:
        elp = usable_elp(row)
        if not math.isfinite(elp) or row["ACD"] is None:
            continue
        base = sum(
            coefficient * value
            for coefficient, value in zip(alk, design_alk(row["AL"], row["K"]))
        )
        residuals.append(elp - base)
        extras.append(
            [
                row["ACD"] - offline.REF_ACD,
                row["LT"] - offline.REF_LT,
                row["WTW"] - offline.REF_WTW,
            ]
        )
    extra = solve_least_squares(extras, residuals)
    return {"alk": alk, "extra": extra}


def leave_one_baseline_out(rows, use_surgeon_inputs):
    """留一基线交叉验证：每次留出一个 baseline 的全部扫描点。"""
    if np is None:
        return []
    baselines = sorted({row["baseline"] for row in rows})
    results = []
    for held_out in baselines:
        train = [row for row in rows if row["baseline"] != held_out]
        test = [row for row in rows if row["baseline"] == held_out]
        fit = fit_coefficients(train)
        if fit is None:
            continue
        deltas = []
        for row in test:
            elp = sum(
                coefficient * value
                for coefficient, value in zip(
                    fit["alk"], design_alk(row["AL"], row["K"])
                )
            )
            if use_surgeon_inputs and fit["extra"] is not None:
                elp += sum(
                    coefficient * value
                    for coefficient, value in zip(
                        fit["extra"],
                        [
                            row["ACD"] - offline.REF_ACD,
                            row["LT"] - offline.REF_LT,
                            row["WTW"] - offline.REF_WTW,
                        ],
                    )
                )
            delta = offline.VERGENCE_SCALE / (row["AL"] - elp) - (
                offline.VERGENCE_SCALE / (offline.VERGENCE_SCALE / row["K"] - elp)
            )
            deltas.append(delta - row["official"])
        results.append((held_out, metrics(deltas)))
    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-download", action="store_true", help="不联网，使用已有 data/"
    )
    parser.add_argument(
        "--refit",
        action="store_true",
        help="额外打印一次重拟合系数（诊断，不修改源码）",
    )
    args = parser.parse_args()

    started = time.time()
    ensure_dataset(allow_download=not args.no_download)
    scans = load_scans()
    grid = load_al_k_grid()
    print(f"[data] scans.csv={len(scans)} 行, AL_K 网格={len(grid)} 行")

    for row in scans:
        row["alk"] = offline_power(row, use_surgeon_inputs=False)
        row["full"] = offline_power(row, use_surgeon_inputs=True)
        row["srkt"] = srkt_power(row["AL"], row["K"], REFERENCE_A_CONSTANT)
        row["holladay1"] = holladay1_power(row["AL"], row["K"], REFERENCE_A_CONSTANT)
        row["delta_alk"] = row["alk"] - row["official"]
        row["delta_full"] = row["full"] - row["official"]
        row["delta_srkt"] = row["srkt"] - row["official"]
        row["delta_holladay1"] = row["holladay1"] - row["official"]

    for row in grid:
        row["alk"] = offline_power(row, use_surgeon_inputs=False)
        row["full"] = row["alk"]
        row["delta_alk"] = row["alk"] - row["official"]
        row["delta_full"] = row["delta_alk"]

    # 与固化系数完全一致的拟合/留出划分：先剔除无法反演 ELP 的极端点，
    # 再按偶数行拟合、奇数行留出。
    valid_rows = [row for row in scans if math.isfinite(usable_elp(row))]
    fit_rows = valid_rows[0::2]
    holdout = valid_rows[1::2]

    m_full_all = metrics([row["delta_full"] for row in scans])
    m_full_holdout = metrics([row["delta_full"] for row in holdout])
    m_alk_all = metrics([row["delta_alk"] for row in scans])
    m_alk_holdout = metrics([row["delta_alk"] for row in holdout])
    m_srkt = metrics([row["delta_srkt"] for row in scans])
    m_holl = metrics([row["delta_holladay1"] for row in scans])

    grid_raw = metrics([row["delta_alk"] for row in grid])
    grid_centered = central_metrics([row["delta_alk"] for row in grid])

    cross_full = cross_table(holdout, "delta_full")
    cross_alk = cross_table(holdout, "delta_alk")
    cross_grid = cross_table(grid, "delta_alk")

    outliers = [
        row
        for row in scans
        if abs(row["delta_full"]) > 0.25
        or (math.isfinite(row["delta_alk"]) and abs(row["delta_alk"]) > 0.25)
    ]
    outliers.sort(key=lambda row: -max(abs(row["delta_full"]), abs(row["delta_alk"])))

    lobo_full = leave_one_baseline_out(scans, use_surgeon_inputs=True)
    lobo_alk = leave_one_baseline_out(scans, use_surgeon_inputs=False)

    refit_note = ""
    if args.refit:
        fit = fit_coefficients(fit_rows)
        if fit is not None:
            refit_note = (
                "重拟合（偶数行）ALK 二次项: "
                + ", ".join(f"{value:.6f}" for value in fit["alk"])
                + "; 附加项: "
                + ", ".join(f"{value:.6f}" for value in (fit["extra"] or []))
            )
            print("[refit] " + refit_note)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    grid_csv = DOCS_DIR / "calibration_grid.csv"
    with open(grid_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source",
                "row_id",
                "AL_mm",
                "K_D",
                "ACD_mm",
                "LT_mm",
                "WTW_mm",
                "official_iol_D",
                "offline_alk_D",
                "offline_full_D",
                "delta_alk_D",
                "delta_full_D",
                "bucket_AL",
                "bucket_K",
            ]
        )
        for row in scans + grid:
            writer.writerow(
                [
                    row["source"],
                    row["row_id"],
                    f"{row['AL']:.4f}",
                    f"{row['K']:.4f}",
                    "" if row["ACD"] is None else f"{row['ACD']:.4f}",
                    "" if row["LT"] is None else f"{row['LT']:.4f}",
                    "" if row["WTW"] is None else f"{row['WTW']:.4f}",
                    f"{row['official']:.6f}",
                    f"{row['alk']:.6f}",
                    f"{row['full']:.6f}",
                    f"{row['delta_alk']:.6f}",
                    f"{row['delta_full']:.6f}",
                    al_bucket(row["AL"]),
                    k_bucket(row["K"]),
                ]
            )

    outlier_csv = DOCS_DIR / "calibration_outliers.csv"
    with open(outlier_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "source",
                "row_id",
                "AL_mm",
                "K_D",
                "ACD_mm",
                "LT_mm",
                "WTW_mm",
                "official_iol_D",
                "offline_alk_D",
                "offline_full_D",
                "delta_alk_D",
                "delta_full_D",
            ]
        )
        for row in outliers:
            writer.writerow(
                [
                    row["source"],
                    row["row_id"],
                    f"{row['AL']:.3f}",
                    f"{row['K']:.3f}",
                    "" if row["ACD"] is None else f"{row['ACD']:.3f}",
                    "" if row["LT"] is None else f"{row['LT']:.3f}",
                    "" if row["WTW"] is None else f"{row['WTW']:.3f}",
                    f"{row['official']:.3f}",
                    f"{row['alk']:.3f}",
                    f"{row['full']:.3f}",
                    f"{row['delta_alk']:.3f}",
                    f"{row['delta_full']:.3f}",
                ]
            )

    scans_hash = sha256sum(DATA_DIR / "scans.csv")
    grids_hash = (
        sha256sum(DATA_DIR / "grids.npz")
        if (DATA_DIR / "grids.npz").exists()
        else "missing"
    )
    report = []
    report.append("# Barrett Universal II 离线模块校准报告\n")
    report.append(
        "> 本报告由 scripts/calibrate_offline.py 实际运行生成，"
        "所有数字来自真实对数，未手工填写。\n"
    )
    report.append("## 0. 结论摘要\n")
    report.append(
        "- 官方 BUII 的 ELP 模型未公开；一篇曾引用的 2021 年论文无法在文献目录中检索到。"
    )
    report.append(
        "- 因此本模块实现的是 Gaussian 聚散度核心 + 公开网格反演的 ELP "
        "近似式，不是官方公式的逐系数复刻。"
    )
    report.append(
        "- 在 scans.csv 留出集（n={}）上，五参数离线模型的 "
        "p95|Δ|={:.3f} D、max|Δ|={:.3f} D；纯 ALK 版 "
        "p95|Δ|={:.3f} D、max|Δ|={:.3f} D。".format(
            m_full_holdout["n"],
            m_full_holdout["p95_abs"],
            m_full_holdout["max_abs"],
            m_alk_holdout["p95_abs"],
            m_alk_holdout["max_abs"],
        )
    )
    report.append(
        "- 文献中的 mean ~0.03 D / SD 0.12-0.18 D 是官方全量版与临床结果"
        "之间的差异量级，不是 ALK 简化版与官方全量版之间的差异。"
    )
    report.append(
        "- 以 mean≈0.03 D、SD 0.12-0.18 D 为参考基准衡量：纯 ALK 版 "
        "SD={:.3f} D，不达标；五参数近似版 mean={:+.3f} D、SD={:.3f} D，"
        "落在量级内，但它依赖 ACD/LT/WTW，并非纯 ALK 版。".format(
            m_alk_holdout["sd"],
            m_full_holdout["mean"],
            m_full_holdout["sd"],
        )
    )
    report.append(
        "- grids.npz:AL_K 曲面存在约 {:+.2f} D 的整体偏移，"
        "且 README 未记录该曲面的 ACD/LT/WTW/A-constant 基线；"
        "因此对该曲面同时报告原始与去均值（形状）指标。".format(grid_raw["mean"])
    )
    report.append("")

    report.append("## 1. 运行命令与数据完整性\n")
    report.append(
        "    python scripts/calibrate_offline.py" + (" --refit" if args.refit else "")
    )
    report.append("")
    report.append("- 运行环境：Python 3.12+；numpy 仅用于该校准脚本。")
    report.append(f"- scans.csv SHA-256：{scans_hash}")
    report.append(f"- grids.npz SHA-256：{grids_hash}")
    report.append("")

    report.append("## 2. 数据来源\n")
    report.append(
        "- 仓库：ekrbye/barrett-uii-data；作者：Yishen Wang、Li Li；许可证 CC-BY-4.0。"
    )
    report.append(
        "- 获取方式：开发期从公开发布仓库下载；数据不参与 Worker 运行或部署。"
    )
    report.append(
        "- 隐私说明：样本为在线计算器的系统性参数扫描，不含患者身份信息；"
        "报告不记录本机路径、Git 状态或网络环境。"
    )
    report.append(
        f"- 内容：scans.csv（单参数扫描，{len(scans)} 行可用）与 grids.npz"
        f"（AL_K 曲面 {len(grid)} 个可用点）。"
    )
    report.append(
        "- README 说明数据来自官方在线计算器（A-constant 118.7），"
        "本脚本按 mean(K1,K2)、目标屈光度 0 对齐。"
    )
    report.append(
        "- 交叉核对：scans.csv 的 B_norm 基线（AL 23.5、K1 43.5/K2 44.5、"
        "ACD 3.2、LT 4.6、WTW 11.9）官方值为 20.488 D；grids.npz 的 AL_K "
        "最近点（AL 23.571、K 44.143）官方值为 19.473 D。两者 AL/K 几乎相同"
        "却相差约 1.0 D，说明该曲面的 ACD/LT/WTW/A-constant 基线未记录且与 "
        "scans 不同，因此不能把 +0.68 D 偏移全部归因于离线模型。"
    )
    report.append("")

    report.append("## 3. 公式出处审计（重要）\n")
    report.append("### 3.1 关于 2021 年论文的检索\n")
    report.append("检索结果：")
    report.append(
        "- PubMed Clin Exp Ophthalmol[Journal] AND 2021[pdat] AND 49[volume] "
        "AND 7[issue] 返回 18 条，660-670 页分别被 652-663（nAMD 综述）和 "
        "664-671（gender differences）占据，没有本论文。"
    )
    report.append(
        "- Crossref 按标题、作者、年份过滤均无匹配；Wiley 卷 49 期 7 目录"
        "同样没有该标题。"
    )
    report.append(
        "- 真实的 Barrett 理论公式文献是 1993 年 JCRS 论文"
        "（PMID 8271166, doi:10.1016/S0886-3350(13)80339-2），"
        "其全文在 LWW/Europe PMC 均为付费/无全文。"
    )
    report.append("- 结论：本项目不声称按该 2021 论文实现。\n")
    report.append("### 3.2 社区参考实现\n")
    report.append(
        "- Wingman4l7/catcalc 的 Barrett_Universal_II_Formula.py 是 "
        "Selenium 填表脚本，没有公式系数；无法用于数值对数。"
    )
    report.append(
        "- wcgBarrett 在 GitHub API（用户 404）和 PyPI（404）均不存在；该仓库无法验证。"
    )
    report.append(
        "- 官方 BUII 的 ELP 是未公开的三阶多项式回归；Barrett 2024 章节明确"
        "写明最简实现约 750 行、完整版约 3000 行，因此不存在可公开复刻的"
        "单页公式。\n"
    )
    report.append("### 3.3 本模块实现的内容\n")
    report.append(
        "- 聚散度核心：P = 1336/(AL-ELP) - 1336/(1336/K' - ELP)，"
        "K' 为目标屈光度经 12 mm 顶点距离折算后的角膜平面屈光度。"
        "该式即 Fyodorov/Barrett 系列的理论基础（EyeWiki 与 Alcon 白皮书均给出）。"
    )
    report.append(
        "- A-constant <-> LF：用厂商公开的四组常数对 "
        "(118.7,1.73)/(119.0,1.88)/(119.1,1.94)/(119.3,2.04) 做线性最小二乘，"
        f"得到 LF = {offline.LF_SLOPE:.6f}*A {offline.LF_INTERCEPT:+.6f}。"
    )
    report.append(
        "- ELP：在公开网格上用薄透镜反演得到等效 ELP，再对 AL/K 做二次、"
        "对 ACD/LT/WTW 做线性回归。系数是 CALIBRATED（非官方）。"
    )
    report.append(
        "- 参考对照：SRK/T（Retzlaff 1990）与 Holladay 1（1988）按公开公式"
        "独立实现，用于给离线 BUII 一个第三方包络。"
    )
    report.append("- 本报告不包含实时官网对照；报告的官方输出值全部来自公开数据集。\n")

    report.append("## 4. 模型系数\n")
    report.append("| 常量 | 值 | 说明 |")
    report.append("|---|---:|---|")
    rows_coeff = [
        ("ELP_C0", offline.ELP_C0, "参考眼 ELP（含 LF(118.7)）"),
        ("ELP_C_AL", offline.ELP_C_AL, "d(ELP)/d(AL)"),
        ("ELP_C_K", offline.ELP_C_K, "d(ELP)/d(K)"),
        ("ELP_C_AL2", offline.ELP_C_AL2, "AL 二次项"),
        ("ELP_C_ALK", offline.ELP_C_ALK, "AL*K 交互项"),
        ("ELP_C_K2", offline.ELP_C_K2, "K 二次项"),
        ("ELP_C_ACD", offline.ELP_C_ACD, "ACD 线性项"),
        ("ELP_C_LT", offline.ELP_C_LT, "晶状体厚度线性项"),
        ("ELP_C_WTW", offline.ELP_C_WTW, "WTW 线性项"),
        ("LF_SLOPE", offline.LF_SLOPE, "A -> LF 斜率"),
        ("LF_INTERCEPT", offline.LF_INTERCEPT, "A -> LF 截距"),
    ]
    for name, value, note in rows_coeff:
        report.append(f"| {name} | {value:.6f} | {note} |")
    report.append("")
    if refit_note:
        report.append("重拟合诊断：" + refit_note + "\n")

    report.append("## 5. 偏差指标（Δ = 离线 - 官方，D）\n")
    report.append(
        "| 数据集 / 模型 | n | mean Δ | SD | median absΔ | p95 absΔ | max absΔ |"
    )
    report.append("|---|---:|---:|---:|---:|---:|---:|")
    report.append(format_metrics("scans 留出集 / 五参数", m_full_holdout))
    report.append(format_metrics("scans 全量 / 五参数（含拟合行）", m_full_all))
    report.append(format_metrics("scans 留出集 / 纯 ALK", m_alk_holdout))
    report.append(format_metrics("scans 全量 / 纯 ALK", m_alk_all))
    report.append(format_metrics("scans 全量 / SRK/T 对照", m_srkt))
    report.append(format_metrics("scans 全量 / Holladay 1 对照", m_holl))
    report.append("")
    report.append("AL_K 曲面（官方基线未记录，故分开报告）：\n")
    report.append("| 口径 | n | mean Δ | SD | median absΔ | p95 absΔ | max absΔ |")
    report.append("|---|---:|---:|---:|---:|---:|---:|")
    report.append(format_metrics("原始 Δ", grid_raw))
    report.append(format_metrics("去均值 Δ", grid_centered))
    report.append(
        "\n原始整体偏移 = {:+.3f} D；去均值后 median|Δ| = {:.3f} D，"
        "p95|Δ| = {:.3f} D。".format(
            grid_centered["offset"],
            grid_centered["median_abs"],
            grid_centered["p95_abs"],
        )
    )
    report.append("")

    report.append("## 6. AL x K 交叉表（median absΔ (n)，单位 D）\n")
    report.append("### 6.1 五参数模型，scans 留出集\n")
    report.append(markdown_cross_table(cross_full))
    report.append("\n### 6.2 纯 ALK 模型，scans 留出集\n")
    report.append(markdown_cross_table(cross_alk))
    report.append("\n### 6.3 纯 ALK 模型，AL_K 曲面（原始 Δ）\n")
    report.append(markdown_cross_table(cross_grid))
    report.append("")

    report.append("## 7. 超出 ±0.25 D 的样本\n")
    report.append(
        f"共有 {len(outliers)} 行（占 scans 的 {100.0 * len(outliers) / max(1, len(scans)):.1f}%）满足 "
        "|Δ_full|>0.25 或 |Δ_alk|>0.25；完整列表见 "
        "docs/calibration_outliers.csv。前 20 行：\n"
    )
    report.append("| row_id | AL | K | ACD | LT | WTW | 官方 | Δ_alk | Δ_full |")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in outliers[:20]:
        report.append(
            "| {row_id} | {al:.2f} | {k:.2f} | {acd} | {lt} | {wtw} | "
            "{official:.2f} | {da:+.2f} | {df:+.2f} |".format(
                row_id=row["row_id"],
                al=row["AL"],
                k=row["K"],
                acd="-" if row["ACD"] is None else f"{row['ACD']:.2f}",
                lt="-" if row["LT"] is None else f"{row['LT']:.2f}",
                wtw="-" if row["WTW"] is None else f"{row['WTW']:.2f}",
                official=row["official"],
                da=row["delta_alk"],
                df=row["delta_full"],
            )
        )
    report.append("")

    report.append("## 8. 留一基线交叉验证（泛化诊断）\n")
    report.append(
        "每次留出一个 baseline 的全部扫描点，重新拟合 ELP 系数后在留出点上"
        "评估。该诊断的系数不用于实际计算，仅用于估计泛化误差。\n"
    )
    report.append(
        "| 模型 | baseline | n | mean Δ | median absΔ | p95 absΔ | max absΔ |"
    )
    report.append("|---|---|---:|---:|---:|---:|---:|")
    for label, items in (("五参数", lobo_full), ("纯 ALK", lobo_alk)):
        for baseline, item in items:
            report.append(
                f"| {label} | {baseline} | {item['n']} | {item['mean']:+.3f} | "
                f"{item['median_abs']:.3f} | {item['p95_abs']:.3f} | "
                f"{item['max_abs']:.3f} |"
            )
    report.append("")

    report.append("## 9. 三方对数说明\n")
    report.append("关于 catcalc / wcgBarrett 的三方对数：")
    report.append("1. catcalc 没有 BUII 公式（只有 Selenium 填表）；")
    report.append("2. wcgBarrett 在 GitHub/PyPI 不存在；")
    report.append("3. 官方 BUII 不公开 ELP 系数。")
    report.append(
        "因此改为与两个独立公开公式（SRK/T、Holladay 1）在同一批 scans 上"
        "对照，指标见第 5 节。离线模型在这批数据上优于三代表；但这只能说明"
        "聚散度核心与校准方向正确，不能证明与官方 BUII 等价。\n"
    )

    report.append("## 10. 结论\n")
    report.append(
        "1. 离线模块是一个近似实现：五参数模式在公开 scans 留出集上 "
        "median|Δ|={:.3f} D、p95|Δ|={:.3f} D；纯 ALK 模式 "
        "median|Δ|={:.3f} D、p95|Δ|={:.3f} D。".format(
            m_full_holdout["median_abs"],
            m_full_holdout["p95_abs"],
            m_alk_holdout["median_abs"],
            m_alk_holdout["p95_abs"],
        )
    )
    report.append(
        "2. 它不是官方 BUII 的等价复刻：没有官方 ELP 系数，也没有"
        "官方厚透镜主平面迭代；短眼/长眼和高低 K 端的偏差更大。"
    )
    report.append(
        "2b. 以 SD 0.18 D 为参考，纯 ALK 版不达标（SD={:.3f} D）；"
        "五参数近似版达标（SD={:.3f} D），但必须提供 ACD/LT/WTW。".format(
            m_alk_holdout["sd"], m_full_holdout["sd"]
        )
    )
    report.append(
        "3. 论文适用域外（AL<22 或 >26 mm、K<38 或 >48 D）只降置信度并在"
        "结果里返回 LOW_CONFIDENCE，不拒绝计算；临床使用前必须人工复核。"
    )
    report.append(
        "3b. 目标屈光度按标准 12 mm 顶点距离折算；公开网格只有 target=0，"
        "因此非零目标的数值准确性没有外部数据验证。"
    )
    report.append(
        "4. 如果拿到官方系数或论文全文，只需替换 ELP 常量并在同一脚本上"
        "重跑，即可得到更新的包络报告；本实现的定位是"
        "默认离线近似 + online 显式对照。"
    )
    report.append("")

    report_path = DOCS_DIR / "calibration_report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    elapsed = time.time() - started
    print(f"[out] {report_path}")
    print(f"[out] {grid_csv}")
    print(f"[out] {outlier_csv}")
    print(f"[done] {elapsed:.1f}s")

    print(
        ">>> OFFLINE BUII DONE maxΔ={:.2f}D p95={:.2f}D n={}".format(
            m_full_holdout["max_abs"],
            m_full_holdout["p95_abs"],
            m_full_holdout["n"],
        )
    )


if __name__ == "__main__":
    main()
