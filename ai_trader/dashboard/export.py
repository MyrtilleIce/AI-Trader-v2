"""Helpers for exporting data in various formats."""

from __future__ import annotations

import io
from typing import Iterable

try:  # pragma: no cover - optional dependency
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None


def trades_csv(rows: Iterable[dict]) -> bytes:
    """Return CSV bytes for a list of trade dictionaries."""

    if pd is None:
        # minimal manual CSV
        if not rows:
            return b""
        keys = rows[0].keys()
        out = ",".join(keys) + "\n"
        for r in rows:
            out += ",".join(str(r.get(k, "")) for k in keys) + "\n"
        return out.encode()
    df = pd.DataFrame(list(rows))
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode()


def metrics_xlsx(metrics: dict) -> bytes:
    """Return XLSX bytes for the provided metrics dictionary."""

    if pd is None:
        return b""
    buf = io.BytesIO()
    df = pd.DataFrame([metrics])
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:  # type: ignore[call-arg]
        df.to_excel(writer, index=False)
    return buf.getvalue()


def report_pdf(summary: dict) -> bytes:
    """Return a simple PDF report.

    Uses reportlab when available. Falls back to a tiny text based PDF-like
    payload when the dependency is missing.
    """

    try:  # pragma: no cover - optional dependency
        from reportlab.pdfgen import canvas
    except Exception:  # pragma: no cover
        return b"PDF generation unavailable"

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 800, "AI-Trader Report")
    y = 760
    for k, v in summary.items():
        c.drawString(100, y, f"{k}: {v}")
        y -= 20
    c.save()
    return buf.getvalue()
