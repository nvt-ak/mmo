#!/usr/bin/env python3
"""
Export TikTok cookies from a local Chromium-based browser into Cookie-Editor JSON.

Uses browser_cookie3 (reads/decrypts the browser cookie DB).

Supported: chrome, chromium, brave, edge, opera, vivaldi, **comet** (Perplexity).

Comet stores data at:
  ~/Library/Application Support/Comet/<Profile>/Cookies
Keychain service:
  "Comet Safe Storage"

Usage (repo root):
  pip install 'browser-cookie3>=0.19'
  # Quit Comet first (Cmd+Q)
  PYTHONPATH=. python scripts/export_chrome_tiktok_cookies.py --browser comet
  PYTHONPATH=. python scripts/export_chrome_tiktok_cookies.py --browser comet --profile "Profile 4"
  PYTHONPATH=. python scripts/export_chrome_tiktok_cookies.py --browser comet --profile all

Then test:
  PYTHONPATH=. python scripts/test_tiktok_ms_token.py --diagnose --keyword aespa --no-cache
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "videoscout" / "tiktok_cookies.json"
DOMAIN_NEEDLE = "tiktok.com"

BROWSER_LOADERS = {
    "chrome": "chrome",
    "chromium": "chromium",
    "brave": "brave",
    "edge": "edge",
    "opera": "opera",
    "vivaldi": "vivaldi",
}

COMET_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "Comet"
COMET_LOCAL_STATE = COMET_SUPPORT_DIR / "Local State"
COMET_KEY_SERVICE = "Comet Safe Storage"
COMET_KEY_USERS = ("Comet", "Chrome", "Chromium")


def _load_browser_cookie3():
    try:
        import browser_cookie3
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pip install 'browser-cookie3>=0.19'\n"
            f"Import error: {exc}"
        ) from exc
    return browser_cookie3


def list_comet_profiles() -> List[str]:
    """Return profile folder names that have a Cookies DB."""
    if not COMET_SUPPORT_DIR.is_dir():
        return []
    names: List[str] = []
    for path in sorted(COMET_SUPPORT_DIR.iterdir()):
        if not path.is_dir():
            continue
        if path.name in ("System Profile", "Guest Profile"):
            continue
        if (path / "Cookies").is_file() or (path / "Network" / "Cookies").is_file():
            names.append(path.name)
    # Prefer Default first
    if "Default" in names:
        names.remove("Default")
        names.insert(0, "Default")
    return names


def comet_cookie_db_path(profile: str) -> Path:
    base = COMET_SUPPORT_DIR / profile
    network = base / "Network" / "Cookies"
    legacy = base / "Cookies"
    if network.is_file():
        return network
    return legacy


def _comet_jar(domain: str, *, profile: str):
    """Load a cookiejar for one Comet profile via ChromiumBased + Comet Keychain."""
    bc = _load_browser_cookie3()
    cookie_file = comet_cookie_db_path(profile)
    if not cookie_file.is_file():
        raise SystemExit(
            f"Comet profile cookie DB not found: {cookie_file}\n"
            f"Available profiles: {', '.join(list_comet_profiles()) or '(none)'}"
        )
    key_file = str(COMET_LOCAL_STATE) if COMET_LOCAL_STATE.is_file() else None

    last_err: Optional[BaseException] = None
    for key_user in COMET_KEY_USERS:
        class CometBrowser(bc.ChromiumBased):
            def __init__(self, cookie_file=None, domain_name="", key_file=None):
                args = {
                    "linux_cookies": [],
                    "windows_cookies": [],
                    "osx_cookies": [str(cookie_file)],
                    "windows_keys": [key_file] if key_file else [],
                    "os_crypt_name": "chrome",
                    "osx_key_service": COMET_KEY_SERVICE,
                    "osx_key_user": key_user,
                }
                super().__init__(
                    browser="Comet",
                    cookie_file=cookie_file,
                    domain_name=domain_name,
                    key_file=key_file,
                    **args,
                )

        try:
            return CometBrowser(
                cookie_file=str(cookie_file),
                domain_name=domain,
                key_file=key_file,
            ).load()
        except Exception as exc:  # noqa: BLE001 — try next key_user
            last_err = exc
            continue

    hint = (
        "\nHint: fully quit Comet (Cmd+Q), allow Keychain access for "
        f"'{COMET_KEY_SERVICE}', then retry."
    )
    raise SystemExit(f"Failed to read Comet cookies ({profile}): {last_err}{hint}") from last_err


def _cookie_jar_for(browser: str, domain: str, *, profile: Optional[str] = None):
    if browser == "comet":
        profiles = list_comet_profiles()
        if not profiles:
            raise SystemExit(
                f"No Comet profiles under {COMET_SUPPORT_DIR}. "
                "Is Comet installed and have you opened it at least once?"
            )
        chosen = profile or "Default"
        if chosen == "all":
            # Caller expands; should not hit here for jar
            raise ValueError("use export for --profile all")
        if chosen not in profiles:
            raise SystemExit(
                f"Unknown Comet profile {chosen!r}. Available: {', '.join(profiles)}"
            )
        try:
            return _comet_jar(domain, profile=chosen)
        except SystemExit:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            hint = ""
            if "locked" in msg or "busy" in msg or "permission" in msg:
                hint = "\nHint: fully quit Comet (Cmd+Q), then re-run."
            raise SystemExit(f"Failed to read comet cookies: {exc}{hint}") from exc

    bc = _load_browser_cookie3()
    loader_name = BROWSER_LOADERS[browser]
    loader: Callable[..., Any] = getattr(bc, loader_name)
    try:
        return loader(domain_name=domain)
    except Exception as exc:
        msg = str(exc).lower()
        hint = ""
        if "locked" in msg or "busy" in msg or "permission" in msg:
            hint = (
                "\nHint: fully quit the browser (Cmd+Q), then re-run. "
                "macOS may also prompt to allow Keychain access."
            )
        raise SystemExit(f"Failed to read {browser} cookies: {exc}{hint}") from exc


def cookie_to_editor_dict(cookie: Any) -> dict[str, Any]:
    """Map http.cookiejar.Cookie → Cookie-Editor JSON object."""
    expires = getattr(cookie, "expires", None)
    http_only = False
    rest = getattr(cookie, "_rest", None) or getattr(cookie, "rest", None) or {}
    if isinstance(rest, dict):
        http_only = "HttpOnly" in rest or "httpOnly" in rest or bool(
            rest.get("HttpOnly") or rest.get("httpOnly")
        )

    same_site = None
    if isinstance(rest, dict):
        raw_ss = rest.get("SameSite") or rest.get("sameSite")
        if raw_ss:
            same_site = str(raw_ss).lower()
            if same_site == "none":
                same_site = "no_restriction"

    return {
        "domain": cookie.domain or "",
        "expirationDate": float(expires) if expires else None,
        "hostOnly": not str(cookie.domain or "").startswith("."),
        "httpOnly": http_only,
        "name": cookie.name,
        "path": cookie.path or "/",
        "sameSite": same_site,
        "secure": bool(cookie.secure),
        "session": expires is None,
        "storeId": None,
        "value": cookie.value or "",
    }


def _rows_from_jar(jar: Iterable[Any]) -> List[dict[str, Any]]:
    rows: List[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for cookie in jar:
        host = (cookie.domain or "").lstrip(".").lower()
        if DOMAIN_NEEDLE not in host:
            continue
        key = (cookie.domain or "", cookie.path or "/", cookie.name or "")
        if key in seen:
            continue
        seen.add(key)
        rows.append(cookie_to_editor_dict(cookie))
    rows.sort(
        key=lambda r: (
            0 if r.get("name") == "msToken" else 1,
            -(len(r.get("value") or "")),
            r.get("name") or "",
        )
    )
    return rows


def _score_rows(rows: Sequence[dict[str, Any]]) -> tuple[int, int, int]:
    names = {r.get("name") for r in rows}
    has_ms = 1 if "msToken" in names else 0
    has_sid = 1 if ("sessionid" in names or "sessionid_ss" in names) else 0
    return (has_ms, has_sid, len(rows))


def export_tiktok_cookies(
    *,
    browser: str,
    domain: str = DOMAIN_NEEDLE,
    profile: Optional[str] = None,
) -> tuple[List[dict[str, Any]], str]:
    """
    Returns (rows, source_label).

    For comet --profile all: pick the profile with the best TikTok session score.
    """
    if browser == "comet" and (profile or "Default") == "all":
        best_rows: List[dict[str, Any]] = []
        best_label = ""
        best_score = (-1, -1, -1)
        for name in list_comet_profiles():
            try:
                jar = _comet_jar(domain, profile=name)
                rows = _rows_from_jar(jar)
            except SystemExit:
                continue
            score = _score_rows(rows)
            print(f"  scanned {name}: cookies={len(rows)} score={score}")
            if score > best_score:
                best_score = score
                best_rows = rows
                best_label = f"comet/{name}"
        return best_rows, best_label or "comet/(none)"

    source = browser
    if browser == "comet":
        source = f"comet/{profile or 'Default'}"
    jar = _cookie_jar_for(browser, domain, profile=profile)
    return _rows_from_jar(jar), source


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export TikTok cookies from Chrome / Comet / Brave / …",
    )
    parser.add_argument(
        "--browser",
        choices=sorted([*BROWSER_LOADERS, "comet"]),
        default="comet",
        help="Browser cookie store (default: comet)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help=(
            "Comet profile folder name (Default, 'Profile 4', …) or 'all' to auto-pick. "
            "List with --list-profiles."
        ),
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List Comet profiles that have a Cookies DB, then exit",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSON path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--domain",
        default=DOMAIN_NEEDLE,
        help="Domain filter (default: tiktok.com)",
    )
    args = parser.parse_args()

    if args.list_profiles:
        profiles = list_comet_profiles()
        print(f"Comet support dir: {COMET_SUPPORT_DIR}")
        if not profiles:
            print("(no profiles found)")
            return 1
        for name in profiles:
            db = comet_cookie_db_path(name)
            print(f"  {name}  →  {db}")
        return 0

    if args.browser != "comet" and args.profile:
        print("WARN: --profile only applies to --browser comet; ignoring.", file=sys.stderr)

    profile = args.profile
    if args.browser == "comet" and profile is None:
        profile = "all"

    print(f"Exporting TikTok cookies from {args.browser}"
          + (f" profile={profile}" if args.browser == "comet" else "")
          + " …")
    print("(Quit Comet/Chrome first if the DB is locked.)")

    rows, source = export_tiktok_cookies(
        browser=args.browser,
        domain=args.domain,
        profile=profile,
    )
    if not rows:
        print(
            f"FAIL: no cookies for *{DOMAIN_NEEDLE}* in {source}. "
            "Open tiktok.com while logged in (in that profile), quit the browser, retry.",
            file=sys.stderr,
        )
        if args.browser == "comet":
            print(
                "Profiles: "
                + (", ".join(list_comet_profiles()) or "(none)")
                + "  (use --list-profiles)",
                file=sys.stderr,
            )
        return 1

    names = {r["name"] for r in rows}
    has_ms = "msToken" in names
    has_sid = "sessionid" in names or "sessionid_ss" in names
    print(f"source: {source}")
    print(f"cookies: {len(rows)}")
    print(f"has_msToken: {has_ms}")
    print(f"has_sessionid: {has_sid}")
    print(f"names: {', '.join(sorted(names)[:20])}{'…' if len(names) > 20 else ''}")

    if not has_ms:
        print(
            "WARN: msToken missing — login on tiktok.com in that browser/profile first.",
            file=sys.stderr,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote: {args.out.resolve()}")
    print(f"exported_at: {datetime.now(timezone.utc).isoformat()}")
    print("Next:")
    print("  PYTHONPATH=. python scripts/test_tiktok_ms_token.py --diagnose --keyword aespa --no-cache")
    return 0 if has_ms else 2


if __name__ == "__main__":
    raise SystemExit(main())
