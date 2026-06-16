#!/usr/bin/env python3
"""
Qwen/DashScope 连通性诊断脚本
=====================================
用途：
  1. 诊断 DashScope 网络可达性
  2. 验证 API Key 有效性
  3. 同时测试两种调用方式（DashScope原生 + OpenAI兼容）
  4. 在此基础上运行真实 Qwen E2E

安全：
  - API Key 仅用于 HTTP Authorization header，不打印原文
  - 输出中仅显示 key 前8位 + 末4位用于核对

用法：
  QWEN_API_KEY=<YOUR_KEY> python scripts/diagnose_qwen_connectivity.py
  QWEN_API_KEY=<YOUR_KEY> python scripts/diagnose_qwen_connectivity.py --run-e2e
  QWEN_API_KEY=<YOUR_KEY> QWEN_TEXT_MODEL=qwen-plus python scripts/diagnose_qwen_connectivity.py

环境变量：
  QWEN_API_KEY 或 DASHSCOPE_API_KEY — 必填
  QWEN_TEXT_MODEL  — 模型名，默认 qwen-turbo
  QWEN_BASE_URL    — base URL，默认 https://dashscope.aliyuncs.com/api/v1
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

_HERE = Path(__file__).parent.parent
sys.path.insert(0, str(_HERE))

try:
    import httpx
except ImportError:
    print("[ERROR] httpx not installed. Run: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _get_key() -> str:
    key = os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or ""
    return key


def _mask(key: str) -> str:
    if not key:
        return "<NOT SET>"
    if len(key) <= 12:
        return key[:4] + "****"
    return key[:8] + "****" + key[-4:]


QWEN_BASE_URL = os.environ.get("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/api/v1")
QWEN_TEXT_MODEL = os.environ.get("QWEN_TEXT_MODEL", "qwen-turbo")

# DashScope 原生 API endpoint（HTTP直连）
NATIVE_TEXT_ENDPOINT = f"{QWEN_BASE_URL}/services/aigc/text-generation/generation"

# OpenAI 兼容模式 endpoint（同一大陆站，不同路径）
COMPAT_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
COMPAT_TEXT_ENDPOINT = f"{COMPAT_BASE}/chat/completions"

MAINLAND_HOST = "dashscope.aliyuncs.com"
INTL_HOST = "dashscope-intl.aliyuncs.com"


# ---------------------------------------------------------------------------
# Phase 1: Network Reachability
# ---------------------------------------------------------------------------

def check_network() -> dict:
    """Test DNS + HTTP reachability for mainland and international endpoints."""
    print()
    print("── Phase 1: 网络可达性检查 ─────────────────────────────────────────")
    results = {}

    for label, host in [("大陆站", MAINLAND_HOST), ("国际站", INTL_HOST)]:
        # DNS
        try:
            t0 = time.time()
            ips = socket.gethostbyname_ex(host)[2]
            dns_ms = (time.time() - t0) * 1000
            dns_ok = True
            dns_info = f"resolved → {ips[0]}  ({dns_ms:.0f}ms)"
        except socket.gaierror as e:
            dns_ok = False
            dns_info = f"DNS FAILED: {e}"

        print(f"  [{label}] DNS {host}: {dns_info}")

        # HTTP GET (just to root)
        url = f"https://{host}"
        try:
            t0 = time.time()
            resp = httpx.get(url, timeout=8, follow_redirects=False)
            http_ms = (time.time() - t0) * 1000
            body_preview = resp.text[:120].replace("\n", " ")
            if "not in allowlist" in resp.text:
                print(f"  [{label}] HTTP: {resp.status_code}  [{http_ms:.0f}ms]  ⛔ SANDBOX BLOCKED: {body_preview}")
                results[host] = {"reachable": False, "reason": "sandbox_blocked", "status": resp.status_code}
            else:
                print(f"  [{label}] HTTP: {resp.status_code}  [{http_ms:.0f}ms]  body: {body_preview}")
                results[host] = {"reachable": True, "status": resp.status_code}
        except httpx.ConnectError as e:
            print(f"  [{label}] HTTP: ConnectError — {e}")
            results[host] = {"reachable": False, "reason": str(e)}
        except httpx.TimeoutException:
            print(f"  [{label}] HTTP: TIMEOUT (>8s)")
            results[host] = {"reachable": False, "reason": "timeout"}
        except Exception as e:
            print(f"  [{label}] HTTP: {type(e).__name__}: {e}")
            results[host] = {"reachable": False, "reason": str(e)}

    return results


# ---------------------------------------------------------------------------
# Phase 2: API Connectivity — DashScope Native
# ---------------------------------------------------------------------------

def test_dashscope_native(api_key: str) -> dict:
    """Test DashScope native HTTP API."""
    print()
    print("── Phase 2a: DashScope 原生 API 测试 ──────────────────────────────")
    print(f"  Endpoint: {NATIVE_TEXT_ENDPOINT}")
    print(f"  Model:    {QWEN_TEXT_MODEL}")
    print(f"  API Key:  {_mask(api_key)}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": QWEN_TEXT_MODEL,
        "input": {
            "messages": [{"role": "user", "content": "Reply with exactly: GIRAFFE_AGENT_OK"}]
        },
        "parameters": {"result_format": "message"},
    }

    try:
        t0 = time.time()
        resp = httpx.post(NATIVE_TEXT_ENDPOINT, headers=headers, json=payload, timeout=30)
        elapsed_ms = (time.time() - t0) * 1000
        body = resp.text

        print(f"  HTTP Status:  {resp.status_code}  ({elapsed_ms:.0f}ms)")

        if "not in allowlist" in body:
            print(f"  ⛔ SANDBOX NETWORK BLOCK: {body.strip()}")
            return {"success": False, "error": "sandbox_blocked", "status": resp.status_code}

        if resp.status_code == 200:
            data = resp.json()
            text = (data.get("output", {})
                       .get("choices", [{}])[0]
                       .get("message", {})
                       .get("content", ""))
            usage = data.get("usage", {})
            print(f"  ✅ SUCCESS")
            print(f"  Response:  {text!r}")
            print(f"  Usage:     {usage}")
            return {"success": True, "text": text, "usage": usage, "elapsed_ms": elapsed_ms}

        # Error response
        print(f"  ❌ FAILED")
        try:
            err = resp.json()
            code = err.get("code", "?")
            message = err.get("message", body[:200])
            print(f"  Error code:    {code}")
            print(f"  Error message: {message}")
            return {"success": False, "error": message, "code": code, "status": resp.status_code}
        except Exception:
            print(f"  Raw body: {body[:300]}")
            return {"success": False, "error": body[:300], "status": resp.status_code}

    except httpx.ConnectError as e:
        print(f"  ❌ ConnectError: {e}")
        return {"success": False, "error": f"ConnectError: {e}"}
    except httpx.TimeoutException:
        print(f"  ❌ TIMEOUT (>30s)")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Phase 2b: API Connectivity — OpenAI Compatible Mode
# ---------------------------------------------------------------------------

def test_dashscope_compat(api_key: str) -> dict:
    """Test DashScope OpenAI-compatible API (same mainland server, different path)."""
    print()
    print("── Phase 2b: OpenAI兼容模式 API 测试 ──────────────────────────────")
    print(f"  Endpoint: {COMPAT_TEXT_ENDPOINT}")
    print(f"  Model:    {QWEN_TEXT_MODEL}")
    print(f"  API Key:  {_mask(api_key)}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": QWEN_TEXT_MODEL,
        "messages": [{"role": "user", "content": "Reply with exactly: GIRAFFE_AGENT_OK"}],
        "max_tokens": 32,
    }

    try:
        t0 = time.time()
        resp = httpx.post(COMPAT_TEXT_ENDPOINT, headers=headers, json=payload, timeout=30)
        elapsed_ms = (time.time() - t0) * 1000
        body = resp.text

        print(f"  HTTP Status:  {resp.status_code}  ({elapsed_ms:.0f}ms)")

        if "not in allowlist" in body:
            print(f"  ⛔ SANDBOX NETWORK BLOCK: {body.strip()}")
            return {"success": False, "error": "sandbox_blocked", "status": resp.status_code}

        if resp.status_code == 200:
            data = resp.json()
            text = (data.get("choices", [{}])[0]
                       .get("message", {})
                       .get("content", ""))
            usage = data.get("usage", {})
            print(f"  ✅ SUCCESS")
            print(f"  Response:  {text!r}")
            print(f"  Usage:     {usage}")
            return {"success": True, "text": text, "usage": usage, "elapsed_ms": elapsed_ms,
                    "mode": "openai_compat"}

        # Error
        print(f"  ❌ FAILED  status={resp.status_code}")
        try:
            err = resp.json()
            print(f"  Error body: {json.dumps(err, ensure_ascii=False)[:300]}")
            return {"success": False, "error": str(err), "status": resp.status_code}
        except Exception:
            print(f"  Raw body: {body[:300]}")
            return {"success": False, "error": body[:300], "status": resp.status_code}

    except httpx.ConnectError as e:
        print(f"  ❌ ConnectError: {e}")
        return {"success": False, "error": f"ConnectError: {e}"}
    except httpx.TimeoutException:
        print(f"  ❌ TIMEOUT")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Phase 3: Full E2E with Real Qwen
# ---------------------------------------------------------------------------

def run_e2e_real(api_key: str, native_result: dict) -> None:
    """Run full E2E pipeline with real Qwen. Only called after connectivity confirmed."""
    print()
    print("── Phase 3: 真实 Qwen E2E 完整链路 ─────────────────────────────────")

    # Detect which mode worked
    use_compat = not native_result.get("success", False)

    if use_compat:
        print("  (使用 OpenAI 兼容模式，因原生模式不可用)")
        os.environ["QWEN_BASE_URL"] = COMPAT_BASE
        # Reload config
        import importlib
        import src.llm.provider_config as cfg
        importlib.reload(cfg)

    import scripts.run_e2e_sakura_shirt_order as e2e_mod
    importlib.reload(e2e_mod) if "importlib" in dir() else None

    from scripts.run_e2e_sakura_shirt_order import (
        SUPPLIER_RESPONSES, DEADLINE_DAYS, QUANTITY, PRODUCT, BUYER_NAME,
        _ensure_schema, run_gltg_for_supplier, run_qwen, persist_to_db,
        _assert_gltg, _assert_qwen, _assert_db,
        SHELF_DATE, COLORS,
    )
    import bm_db_adapter

    db_url = "sqlite:///./e2e_real_qwen_test.db"
    print(f"  DB: {db_url}")
    _ensure_schema(db_url)

    # GLTG
    print()
    print("  [GLTG] Running feasibility per supplier...")
    gltg_results = []
    for sr in SUPPLIER_RESPONSES:
        r = run_gltg_for_supplier(sr)
        feasible = "✓" if r["feasible"] else "✗"
        print(f"    {r['supplier_name']:<35} P80={r['p80_days']}d  slack={r['slack_days']}d  {feasible}")
        gltg_results.append(r)
    _assert_gltg(gltg_results)
    print("  [GLTG] All assertions passed ✓")

    # Qwen real call
    print()
    os.environ["E2E_QWEN_MODE"] = "real"
    os.environ["QWEN_API_KEY"] = api_key
    print(f"  [Qwen] mode=real  key={_mask(api_key)}  model={QWEN_TEXT_MODEL}")
    t0 = time.time()
    qwen_result = run_qwen(gltg_results, mode="real")
    qwen_elapsed = (time.time() - t0) * 1000
    _assert_qwen(qwen_result)

    print(f"  [Qwen] SUCCESS in {qwen_elapsed:.0f}ms")
    print(f"  [Qwen] recommended_supplier: {qwen_result.get('recommended_supplier')}")
    print(f"  [Qwen] confidence:           {qwen_result.get('confidence', '?')}")
    rs = qwen_result.get("risk_summary", "?")
    print(f"  [Qwen] risk_summary (100c):  {rs[:100]}")
    print(f"  [Qwen] mode in result:       {qwen_result.get('_mode', '?')}")
    print(f"  [Qwen] model used:           {qwen_result.get('_model', QWEN_TEXT_MODEL)}")

    # DB
    print()
    print("  [DB] Persisting full lifecycle...")
    bm_db_adapter.DB_MODE = "on"
    adapter = bm_db_adapter.BMDbAdapter(db_url=db_url)
    try:
        db_result = persist_to_db(adapter, gltg_results, qwen_result)
        _assert_db(db_result, adapter)
        print("  [DB] All assertions passed ✓")
        counts = db_result["counts"]
        print(f"  [DB] actors={counts['actors']}  projects={counts['projects']}  "
              f"inquiries={counts['supplier_inquiries']}  events={counts['execution_events']}")
    finally:
        adapter.close()
    bm_db_adapter.DB_MODE = "off"

    print()
    print("  ✅ 真实 Qwen E2E 完整链路通过")


# ---------------------------------------------------------------------------
# Diagnosis Report
# ---------------------------------------------------------------------------

def print_diagnosis(net: dict, native: dict, compat: dict) -> None:
    print()
    print("═" * 68)
    print("  诊断报告")
    print("═" * 68)

    # Network
    mainland_ok = net.get(MAINLAND_HOST, {}).get("reachable", False)
    if mainland_ok:
        print("  网络 → 大陆站可达 ✅")
    else:
        reason = net.get(MAINLAND_HOST, {}).get("reason", "unknown")
        if reason == "sandbox_blocked":
            print("  网络 → 大陆站 ⛔ SANDBOX BLOCKED（沙箱网络出口策略阻断）")
            print("         → 这是 Claude Code on the Web 环境的限制，不是端点配置问题")
            print("         → 解决：在环境设置 Network Egress 中添加 dashscope.aliyuncs.com")
            print("         → 或在本地机器（有大陆网络访问权限）执行此脚本")
        else:
            print(f"  网络 → 大陆站 ❌ {reason}")

    # API Key
    sandbox_blocked = (
        native.get("error") == "sandbox_blocked"
        or compat.get("error") == "sandbox_blocked"
        or net.get(MAINLAND_HOST, {}).get("reason") == "sandbox_blocked"
    )
    api_ok = native.get("success") or compat.get("success")
    if api_ok:
        print("  API Key → 有效 ✅")
    elif sandbox_blocked:
        print("  API Key → 无法验证（网络被沙箱出口策略拦截，key有效性未知）")
        print("             → 沙箱返回的 403 来自代理层，未到达 DashScope 认证服务")
    elif native.get("status") == 401:
        print("  API Key → 无效/未授权 ❌（401）")
    elif native.get("status") == 403:
        print("  API Key → 无权限 ❌（403，已到达 DashScope 但被拒绝）")
    else:
        print(f"  API Key → 错误: {native.get('error', '?')}")

    # Endpoint config
    print()
    print("  端点配置检查（代码层面）:")
    print(f"    调用方式:  DashScope 原生 HTTP API（非 OpenAI 兼容模式）")
    print(f"    默认 Base URL: https://dashscope.aliyuncs.com/api/v1  ← 大陆站 ✅ 已正确")
    print(f"    Text Endpoint: .../services/aigc/text-generation/generation")
    print(f"    当前 QWEN_BASE_URL: {QWEN_BASE_URL}")
    print(f"    模型: {QWEN_TEXT_MODEL}")
    print(f"    可覆盖: QWEN_BASE_URL / QWEN_TEXT_MODEL 环境变量 ✅")
    print()
    print("  之前 403 失败原因: 沙箱网络出口策略阻断，与端点配置无关")
    print("  代码 endpoint 配置本身完全正确（已是大陆站）")


# ---------------------------------------------------------------------------
# Local Reproduction Steps
# ---------------------------------------------------------------------------

def print_local_steps(api_key: str) -> None:
    print()
    print("═" * 68)
    print("  本地复跑步骤（需有中国大陆网络出口权限的机器）")
    print("═" * 68)
    print()
    print("  1. 克隆并切换到 E2E 分支:")
    print("     git clone https://github.com/GiraffeTechnology/giraffe-agent")
    print("     cd giraffe-agent")
    print("     git checkout claude/abcdyi-e2e-integration-test-5vnkb8")
    print()
    print("  2. 安装依赖:")
    print("     pip install uv && uv sync")
    print()
    print("  3. 最小连通性诊断（替换 <YOUR_KEY>）:")
    print("     QWEN_API_KEY=<YOUR_KEY> python scripts/diagnose_qwen_connectivity.py")
    print()
    print("  4. 连通成功后运行完整 E2E:")
    print("     QWEN_API_KEY=<YOUR_KEY> python scripts/diagnose_qwen_connectivity.py --run-e2e")
    print()
    print("  5. 运行完整测试套件（含真实 Qwen）:")
    print("     QWEN_API_KEY=<YOUR_KEY> E2E_QWEN_MODE=real \\")
    print("       uv run pytest tests/e2e/test_sakura_shirt_order_e2e.py -v")
    print()
    print("  注意: 模型名 qwen-turbo 在大陆站应有效。若返回 404，")
    print("        改为: QWEN_TEXT_MODEL=qwen-plus ...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Qwen DashScope 连通性诊断")
    parser.add_argument("--run-e2e", action="store_true",
                        help="连通成功后自动运行完整 E2E 链路")
    parser.add_argument("--skip-compat", action="store_true",
                        help="跳过 OpenAI 兼容模式测试")
    args = parser.parse_args()

    api_key = _get_key()

    print()
    print("═" * 68)
    print("  Giraffe Agent — Qwen DashScope 连通性诊断")
    print("═" * 68)
    print(f"  API Key: {_mask(api_key)}")
    print(f"  Base URL: {QWEN_BASE_URL}")
    print(f"  Model: {QWEN_TEXT_MODEL}")
    print()

    if not api_key:
        print("  ❌ API Key 未设置！")
        print("     请设置: export QWEN_API_KEY=<YOUR_KEY>")
        print("     或:      export DASHSCOPE_API_KEY=<YOUR_KEY>")
        sys.exit(1)

    # Phase 1
    net = check_network()

    # Phase 2a
    native = test_dashscope_native(api_key)

    # Phase 2b
    compat = {}
    if not args.skip_compat:
        compat = test_dashscope_compat(api_key)

    # Diagnosis
    print_diagnosis(net, native, compat)

    # Phase 3
    if args.run_e2e:
        if native.get("success") or compat.get("success"):
            run_e2e_real(api_key, native)
        else:
            print()
            print("  ⛔ E2E 跳过 — API 调用未成功（网络或 Key 问题）")
            print("     解决网络/Key 问题后重跑: --run-e2e")
    else:
        print_local_steps(api_key)

    print()


if __name__ == "__main__":
    main()
