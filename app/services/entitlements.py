from __future__ import annotations

from datetime import timedelta


def package_timedelta(pkg) -> timedelta:
    """
    Hotspot validity duration based on Dmpolin packages.

    Supported:
    - hourly (1h)   -> 1 hour
    - 6 hours       -> 6 hours
    - 12 hours      -> 12 hours
    - daily         -> 1 day
    - weekly        -> 7 days
    - monthly       -> 30 days
    """

    identifier = (
        getattr(pkg, "code", None)
        or getattr(pkg, "slug", None)
        or getattr(pkg, "name", "")
    ).lower()

    # Hour-based
    if "12h" in identifier or "12hr" in identifier or "12 hrs" in identifier or "12 hours" in identifier:
        return timedelta(hours=12)

    if "6h" in identifier or "6hr" in identifier or "6 hrs" in identifier or "6 hours" in identifier:
        return timedelta(hours=6)

    # Be careful: "1 user" could accidentally match "1h" if written poorly, so check hour keywords
    if "1h" in identifier or "1hr" in identifier or "1 hour" in identifier or "hourly" in identifier:
        return timedelta(hours=1)

    # Day/Week/Month
    if "daily" in identifier:
        return timedelta(days=1)

    if "weekly" in identifier:
        return timedelta(days=7)

    if "monthly" in identifier:
        return timedelta(days=30)

    # Safest fallback
    return timedelta(hours=1)
