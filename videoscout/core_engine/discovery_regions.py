"""Creator Rewards discovery region allowlist (US-079)."""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

DISCOVERY_REGION_ALLOWLIST: frozenset[str] = frozenset(
    {"US", "DE", "GB", "JP", "KR", "ES", "FR", "MX"}
)

DISCOVERY_REGION_LABELS: tuple[tuple[str, str], ...] = (
    ("US", "United States"),
    ("DE", "Germany"),
    ("GB", "United Kingdom"),
    ("JP", "Japan"),
    ("KR", "South Korea"),
    ("ES", "Spain"),
    ("FR", "France"),
    ("MX", "Mexico"),
)

DEFAULT_DISCOVERY_REGION_CODES: tuple[str, ...] = ("US",)


class DiscoveryRegionError(ValueError):
    """Invalid or empty discovery region selection."""


def normalize_discovery_region_codes(
    codes: Optional[Sequence[str] | Iterable[str]],
    *,
    default: Sequence[str] = DEFAULT_DISCOVERY_REGION_CODES,
) -> List[str]:
    """
    Normalize region codes: uppercase, strip duplicates (first-win), allowlist.

    Empty / None → copy of ``default`` (also validated).
    Raises DiscoveryRegionError if any code is outside the allowlist or default is empty.
    """
    if codes is None:
        raw: List[str] = list(default)
    else:
        raw = [str(c).strip().upper() for c in codes if str(c).strip()]
        if not raw:
            raw = list(default)

    if not raw:
        raise DiscoveryRegionError("discovery_region_codes must not be empty")

    seen: set[str] = set()
    out: List[str] = []
    for code in raw:
        if code not in DISCOVERY_REGION_ALLOWLIST:
            raise DiscoveryRegionError(
                f"region '{code}' is not in the Creator Rewards allowlist"
            )
        if code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def resolve_discovery_region_codes(
    *,
    settings_codes: Optional[Sequence[str]] = None,
    region_codes: Optional[Sequence[str]] = None,
    region_code: Optional[str] = None,
) -> List[str]:
    """
    Resolve codes for a Discover run.

    Priority: explicit ``region_codes`` → legacy single ``region_code`` → Settings → default US.
    """
    if region_codes is not None:
        return normalize_discovery_region_codes(region_codes)
    if region_code is not None and str(region_code).strip():
        return normalize_discovery_region_codes([region_code])
    return normalize_discovery_region_codes(settings_codes)
