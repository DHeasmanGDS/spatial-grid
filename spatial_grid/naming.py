"""Line and station naming conventions."""
from __future__ import annotations


def line_label(offset_m: float, scheme: str, index: int) -> str:
    """Return a label for a survey line.

    Schemes:
        sequential: L1, L2, L3...
        chainage:   L+100, L0, L-100 (signed metres from baseline)
        signed:     same as chainage (alias)
    """
    if scheme == "sequential":
        return f"L{index + 1}"
    if scheme in ("chainage", "signed"):
        m = int(round(offset_m))
        if m == 0:
            return "L0"
        sign = "+" if m > 0 else "-"
        return f"L{sign}{abs(m)}"
    raise ValueError(f"Unknown line naming scheme: {scheme!r}")


def station_label(offset_m: float, scheme: str, index: int) -> str:
    """Return a label for a station along a line.

    Schemes:
        sequential: S1, S2, S3...
        chainage:   1+00 / 0+00 / -1+00 (engineering chainage, hundred-foot/metre style)
        signed:     S+100, S0, S-100
    """
    if scheme == "sequential":
        return f"S{index + 1}"
    if scheme == "chainage":
        m = int(round(offset_m))
        sign = "" if m >= 0 else "-"
        hundreds = abs(m) // 100
        remainder = abs(m) % 100
        return f"{sign}{hundreds}+{remainder:02d}"
    if scheme == "signed":
        m = int(round(offset_m))
        if m == 0:
            return "S0"
        sign = "+" if m > 0 else "-"
        return f"S{sign}{abs(m)}"
    raise ValueError(f"Unknown station naming scheme: {scheme!r}")
