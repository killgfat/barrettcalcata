#!/usr/bin/env python3
"""IOL Calculator API 的命令行客户端。

用法::

    iol.py calculate --file payload.json
    iol.py calculate --json '{"model": "srkt", ...}'
    cat payload.json | iol.py calculate
    iol.py toric --json '{...}'
    iol.py health

目标实例由 IOL_API_BASE 决定，未设置时指向项目作者的部署。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE = "https://barrettcalcata.killgfat.com"
# 单个总超时。urllib 不支持分离连接/读取超时，取 30 秒：
# 正常请求 1-5 秒返回，缓存未命中或者在线 Barrett 转发也不该超过这个量级。
TIMEOUT_SECONDS = 30
# Cloudflare 会按 UA 拦截默认的 Python-urllib，必须显式声明。
USER_AGENT = "iol-calculator-skill/1.0 (+https://github.com/killgfat/barrettcalcata)"


def api_base(override: str | None = None) -> str:
    """解析 API 根地址：命令行 > 环境变量 > 默认部署。"""
    base = override or os.environ.get("IOL_API_BASE") or DEFAULT_BASE
    return base.rstrip("/")


def request_json(url: str, payload: dict | None = None) -> tuple[int, dict]:
    """发一个 JSON 请求，返回 (HTTP 状态码, 响应体)。"""
    data = None
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": exc.reason, "message": body[:500]}
        return exc.code, parsed
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"无法连接 {url}: {exc.reason}\n"
            "检查网络，或用 --base / IOL_API_BASE 指定其它实例。"
        ) from exc


def read_payload(args) -> dict:
    """按优先级读取请求体：--json > --file > stdin。"""
    if args.json:
        raw = args.json
    elif args.file:
        if args.file == "-":
            raw = sys.stdin.read()
        else:
            with open(args.file, encoding="utf-8") as fh:
                raw = fh.read()
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        raise SystemExit("没有请求体：用 --json、--file 或 stdin 提供 JSON")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"请求体不是合法 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("请求体必须是 JSON 对象")
    return payload


def fmt(value) -> str:
    """把 None 显示成占位符，数字保留两位。"""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def print_eye(name: str, eye: dict) -> None:
    """打印一只眼的关键结果。"""
    print(f"  {name}:")
    if eye.get("recommended_power") is not None:
        print(f"    推荐度数       {eye['recommended_power']} D")
    if eye.get("predicted_refraction") is not None:
        print(f"    预测屈光度     {fmt(eye['predicted_refraction'])} D")
    if eye.get("elp") is not None:
        print(f"    ELP            {fmt(eye['elp'])} mm")
    if eye.get("confidence"):
        print(f"    置信度         {eye['confidence']}")

    used = eye.get("used_inputs") or {}
    constants = {
        key: used[key]
        for key in ("a_constant", "a0", "a1", "a2", "pACD", "SF")
        if used.get(key) is not None
    }
    if constants:
        pairs = ", ".join(f"{k}={fmt(v)}" for k, v in constants.items())
        print(f"    实际常数       {pairs}")

    ignored = eye.get("ignored_inputs") or []
    if ignored:
        print(f"    被忽略的输入   {', '.join(ignored)}")

    options = eye.get("iol_options") or []
    if options:
        recommended = next(
            (row for row in options if row.get("recommended")), options[0]
        )
        print(
            "    推荐晶状体     "
            f"{recommended.get('iol_power')} D"
            f"（残余 {recommended.get('refraction')} D）"
        )

    if eye.get("recommended_iol_cylinder_exact") is not None:
        print(
            "    建议柱镜       "
            f"{eye['recommended_iol_cylinder_exact']:.2f} D（连续解）"
        )
    if eye.get("recommended_axis") is not None:
        print(f"    建议轴位       {fmt(eye['recommended_axis'])}°")
    residual = eye.get("residual_astigmatism") or {}
    if residual.get("cylinder") is not None:
        print(
            "    残余散光       "
            f"{residual['cylinder']:.2f} D @ {fmt(residual.get('axis'))}°"
        )

    for warning in eye.get("warnings") or []:
        print(f"    警告           {warning}")


def print_calculation(body: dict) -> None:
    """打印计算类响应的摘要。"""
    data = body.get("data") or {}
    print(body.get("message") or "完成")
    print(
        f"  模型: {data.get('calculation_model_label') or data.get('formula_label') or '—'}"
    )
    if data.get("mode"):
        print(f"  执行方式: {data['mode']}")

    source = data.get("constants_source") or {}
    if source.get("source") == "ulib":
        print(f"  常数来源: ULIB — {source.get('ulib_name')}")
        if source.get("applied"):
            print(f"    采用型号: {', '.join(source['applied'])}")
        if source.get("ignored_request"):
            print(f"    屏蔽请求: {', '.join(source['ignored_request'])}")
        if source.get("preliminary"):
            print("    注意: 该条目样本量偏小（preliminary）")
    elif source.get("source") == "a_constant_conversion":
        print(f"  常数来源: {source.get('note')}")
    elif source.get("source") == "explicit_sf":
        print(f"  常数来源: {source.get('note')}")
    elif source.get("source") == "castrop_constants":
        print("  常数来源: 调用方传入的 Castrop C/H/R（IOLCon）")
    elif source.get("source") == "castrop_elp":
        print("  ELP 来源: 调用方直接指定，C/H 不参与推导")
    elif source.get("source") == "paper_default":
        print("  常数来源: 论文优化初值 C=0.40/H=0.00/R=0.00（无晶体特异性）")

    for key, label in (("right_eye", "右眼"), ("left_eye", "左眼")):
        if data.get(key):
            print_eye(label, data[key])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="IOL Calculator API 客户端",
        epilog=(f"目标实例由 IOL_API_BASE 指定，默认 {DEFAULT_BASE}"),
    )
    parser.add_argument(
        "--base",
        help="覆盖 IOL_API_BASE，例如 http://localhost:8787",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="输出原始 JSON 而不是摘要",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    calc = sub.add_parser("calculate", help="普通 IOL 计算")
    calc.add_argument("--json", help="请求体 JSON 字符串")
    calc.add_argument("--file", "-f", help="请求体 JSON 文件，- 表示 stdin")

    toric = sub.add_parser("toric", help="Barrett Toric 在线计算")
    toric.add_argument("--json", help="请求体 JSON 字符串")
    toric.add_argument("--file", "-f", help="请求体 JSON 文件，- 表示 stdin")

    sub.add_parser("health", help="检查实例可达性")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = api_base(args.base)

    if args.command == "calculate":
        status, body = request_json(f"{base}/api/calculate", read_payload(args))
    elif args.command == "toric":
        status, body = request_json(f"{base}/api/calculate-toric", read_payload(args))
    else:  # health
        status, body = request_json(f"{base}/hello")

    if args.raw or status >= 400:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0 if status < 400 else 1

    if args.command in {"calculate", "toric"}:
        print_calculation(body)
    else:
        print(f"实例可用: {base}")
        print(json.dumps(body, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
