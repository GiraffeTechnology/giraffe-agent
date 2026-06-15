"""
Validate the @giraffetechnology/openclaw-aivan ClawHub plugin package.

Checks:
  1. Plugin package.json exists with required fields
  2. OpenClaw compatibility metadata is present
  3. Required environment variables are documented in README
  4. Plugin entry point (index.ts) exists
  5. SECURITY.md exists
  6. No secrets are present in committed files
  7. AIVAN_BASE_URL must be configured to reach AIVAN

Usage:
  python scripts/validate_clawhub_aivan_plugin.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = ROOT / "integrations" / "openclaw-aivan-plugin"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}{': ' + detail if detail else ''}")
        failures.append(label)
    return condition


def skip(label: str, reason: str) -> None:
    print(f"  {SKIP}  {label} — {reason}")


# ─── 1. Plugin directory ───────────────────────────────────────────────────────

print("\n[1] Plugin directory structure")

check("integrations/openclaw-aivan-plugin/ exists", PLUGIN_DIR.is_dir())

pkg_path = PLUGIN_DIR / "package.json"
check("package.json exists", pkg_path.exists())

index_path = PLUGIN_DIR / "index.ts"
check("index.ts exists", index_path.exists())

readme_path = PLUGIN_DIR / "README.md"
check("README.md exists", readme_path.exists())

security_path = PLUGIN_DIR / "SECURITY.md"
check("SECURITY.md exists", security_path.exists())

# ─── 2. package.json metadata ─────────────────────────────────────────────────

print("\n[2] package.json metadata")

pkg: dict = {}
if pkg_path.exists():
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        check("package.json is valid JSON", False, str(e))

if pkg:
    check('name == "@giraffetechnology/openclaw-aivan"', pkg.get("name") == "@giraffetechnology/openclaw-aivan")
    check('version is set', bool(pkg.get("version")))
    check('version starts with 0.1', pkg.get("version", "").startswith("0.1"))
    check('type == "module"', pkg.get("type") == "module")
    check('description is set', bool(pkg.get("description")))
    check('license is set', bool(pkg.get("license")))
    check('repository.url is set', bool((pkg.get("repository") or {}).get("url")))

# ─── 3. OpenClaw compatibility metadata ───────────────────────────────────────

print("\n[3] OpenClaw compatibility metadata")

if pkg:
    openclaw = pkg.get("openclaw", {})
    check("openclaw key exists in package.json", bool(openclaw))
    check("openclaw.compat.pluginApi is set", bool((openclaw.get("compat") or {}).get("pluginApi")))
    check("openclaw.build.openclawVersion is set", bool((openclaw.get("build") or {}).get("openclawVersion")))

    extensions = openclaw.get("extensions", [])
    check("openclaw.extensions is a non-empty list", isinstance(extensions, list) and len(extensions) > 0)

    ext_ids = [e.get("id") for e in extensions]
    check("aivan.health extension defined", "aivan.health" in ext_ids)
    check("aivan.forwardEvent extension defined", "aivan.forwardEvent" in ext_ids)
    check("aivan.getPendingDrafts extension defined", "aivan.getPendingDrafts" in ext_ids)
    check("aivan.approveDraft extension defined", "aivan.approveDraft" in ext_ids)
    check("aivan.rejectDraft extension defined", "aivan.rejectDraft" in ext_ids)

# ─── 4. Environment variable documentation ────────────────────────────────────

print("\n[4] Environment variable documentation")

if readme_path.exists():
    readme = readme_path.read_text(encoding="utf-8")
    check("AIVAN_BASE_URL documented in README", "AIVAN_BASE_URL" in readme)
    check("AIVAN_API_KEY documented in README", "AIVAN_API_KEY" in readme)
    check("Mock mode documented in README", "mock" in readme.lower() or "Mock" in readme)
    check("Human approval gate documented in README", "approval" in readme.lower())

if security_path.exists():
    security = security_path.read_text(encoding="utf-8")
    check("No credential storage documented in SECURITY.md", "credential" in security.lower())
    check("Approval gate documented in SECURITY.md", "approval" in security.lower())
    check("Local data boundary documented in SECURITY.md", "local" in security.lower())

# ─── 5. Skill listing ─────────────────────────────────────────────────────────

print("\n[5] Skill listing")

skill_dir = ROOT / "skills" / "aivan-trade-salesperson"
skill_md = skill_dir / "SKILL.md"
check("skills/aivan-trade-salesperson/SKILL.md exists", skill_md.exists())

if skill_md.exists():
    skill_text = skill_md.read_text(encoding="utf-8")
    check("Skill slug defined", "aivan-trade-salesperson" in skill_text)
    check("AIVAN_BASE_URL referenced in skill", "AIVAN_BASE_URL" in skill_text)
    check("Human approval referenced in skill", "approval" in skill_text.lower())

# ─── 6. Secret safety check ───────────────────────────────────────────────────

print("\n[6] Secret safety check")

SECRET_PATTERNS = [
    "sk-", "api_key=", "apikey=", "password=", "secret=",
    "token=", "Authorization: Bearer",
]

files_to_check = list(PLUGIN_DIR.rglob("*"))
secret_found = False
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build"}
for fpath in files_to_check:
    if not fpath.is_file():
        continue
    # Skip vendored/generated directories
    if any(part in SKIP_DIRS for part in fpath.parts):
        continue
    try:
        content = fpath.read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        continue
    for pattern in SECRET_PATTERNS:
        # Allow references in docs/comments, flag actual assignments
        idx = content.find(pattern.lower())
        if idx != -1:
            line = content[max(0, idx - 20):idx + 60].replace("\n", " ")
            # Skip if it's clearly a comment or documentation example
            if "your-" not in line and "example" not in line and "placeholder" not in line:
                print(f"  {FAIL}  Potential secret in {fpath.relative_to(ROOT)}: ...{line}...")
                failures.append(f"secret in {fpath.name}")
                secret_found = True
                break

if not secret_found:
    print(f"  {PASS}  No hardcoded secrets found in plugin files")

# ─── 7. AIVAN_BASE_URL safety ─────────────────────────────────────────────────

print("\n[7] AIVAN_BASE_URL configuration")

base_url = os.environ.get("AIVAN_BASE_URL", "")
if base_url:
    check("AIVAN_BASE_URL is set", True, base_url)
else:
    skip(
        "AIVAN_BASE_URL not set",
        "set AIVAN_BASE_URL=http://localhost:8000 to run against a live AIVAN service"
    )

# ─── Summary ──────────────────────────────────────────────────────────────────

print()
if failures:
    print(f"RESULT: {len(failures)} check(s) failed:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("RESULT: All checks passed. Plugin is ready for ClawHub publication dry-run.")
    print()
    print("Next steps:")
    print("  npm i -g clawhub")
    print("  clawhub login")
    print("  clawhub package publish integrations/openclaw-aivan-plugin --family code-plugin --dry-run")
