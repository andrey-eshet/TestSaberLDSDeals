from __future__ import annotations

from datetime import datetime
import html
from typing import Any


def build_attempts_block(attempts: list[dict[str, Any]]) -> str:
    if not attempts:
        return "אין נתונים"

    lines: list[str] = []

    for idx, attempt in enumerate(attempts, start=1):
        lines.append(f"ניסיון {idx}")
        lines.append(attempt.get("start_date", ""))
        lines.append(attempt.get("end_date", ""))
        lines.append("SabreLDS")
        lines.append(str(attempt.get("sabre_rows_count", 0)))
        lines.append("Odyssea")
        lines.append(str(attempt.get("odyssea_rows_count", 0)))
        lines.append("סיבה")
        lines.append(attempt.get("reason_he", ""))
        lines.append("")

    return "\n".join(lines).strip()


def build_email_subject(summary: dict[str, Any], dt_local: datetime) -> str:
    status_he = "עבר" if summary.get("status") == "passed" else "נכשל"
    sabre_f = summary.get("sabre_found_count", 0)
    sabre_t = summary.get("sabre_total_count", 0)
    odyssea_f = summary.get("odyssea_found_count", 0)
    odyssea_t = summary.get("odyssea_total_count", 0)
    return f"דו\"ח חבילות סגורות {status_he} S:{sabre_f}/{sabre_t} O:{odyssea_f}/{odyssea_t} {dt_local:%Y-%m-%d}"


def _build_vendor_results_block(results: list[dict[str, Any]], vendor: str) -> str:
    if not results:
        return f"{vendor}: אין נתונים"
    lines: list[str] = [f"{vendor} ({len([r for r in results if r.get('found')])}/" f"{len(results)})"]
    for r in results:
        status = "נמצא" if r.get("found") else "לא נמצא"
        lines.append(f"  {r.get('hotel_name', '?')} - {status}")
        if r.get("package_id"):
            lines.append(f"    מזהה: {r.get('package_id', '')}")
    return "\n".join(lines)


def build_email_body(summary: dict[str, Any], dt_local: datetime) -> str:
    attempts_block = build_attempts_block(summary.get("attempts", []))
    passfail = "עבר" if summary.get("status") == "passed" else "נכשל"

    sabre_results = summary.get("sabre_results", [])
    odyssea_results = summary.get("odyssea_results", [])

    lines = [
        "דו\"ח ניטור חבילות סגורות",
        "",
        "תאריך ושעה",
        dt_local.strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "יעד",
        "בטומי",
        "",
        "חלון בדיקה",
        summary.get("start_date", ""),
        summary.get("end_date", ""),
        "",
        "תוצאה",
        passfail,
        "",
        "מקור אמת TourGW",
        summary.get("tourgateway_url", ""),
        f"SabreLDS: {summary.get('sabre_rows_count', 0)}",
        f"Odyssea: {summary.get('odyssea_rows_count', 0)}",
        "",
        "אתר אשת",
        summary.get("eshet_url", ""),
        "",
        "אימות כל החבילות",
        _build_vendor_results_block(sabre_results, "SabreLDS"),
        "",
        _build_vendor_results_block(odyssea_results, "Odyssea"),
        "",
        "ניסיונות חלון תאריכים",
        attempts_block,
    ]

    return "\n".join(lines).strip() + "\n"


def _safe(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _link(url: str) -> str:
    clean = (url or "").strip()
    if not clean:
        return "-"
    safe_url = _safe(clean)
    return f"<a href=\"{safe_url}\">{safe_url}</a>"


def _build_vendor_html_table(results: list[dict[str, Any]], vendor: str) -> str:
    found_count = len([r for r in results if r.get("found")])
    total = len(results)
    header_color = "#137333" if found_count == total else "#B3261E"

    rows: list[str] = []
    for idx, r in enumerate(results, start=1):
        status = "נמצא" if r.get("found") else "לא נמצא"
        status_color = "#137333" if r.get("found") else "#B3261E"
        pkg_link = _link(r.get("package_url", "")) if r.get("package_url") else "-"
        rows.append(
            "<tr>"
            f"<td style=\"padding:4px 6px;border:1px solid #e2e4e9;\">{idx}</td>"
            f"<td style=\"padding:4px 6px;border:1px solid #e2e4e9;\">{_safe(r.get('hotel_name', '?'))}</td>"
            f"<td style=\"padding:4px 6px;border:1px solid #e2e4e9;color:{status_color};font-weight:600;\">{status}</td>"
            f"<td style=\"padding:4px 6px;border:1px solid #e2e4e9;\">{_safe(r.get('package_id', ''))}</td>"
            f"<td style=\"padding:4px 6px;border:1px solid #e2e4e9;\">{_safe(r.get('detected_vendor', ''))}</td>"
            f"<td style=\"padding:4px 6px;border:1px solid #e2e4e9;\">{pkg_link}</td>"
            "</tr>"
        )

    return f"""
      <h4 style="margin:12px 0 6px 0;color:{header_color};">{vendor} ({found_count}/{total})</h4>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr>
          <th style="text-align:right;padding:4px 6px;border:1px solid #e2e4e9;">#</th>
          <th style="text-align:right;padding:4px 6px;border:1px solid #e2e4e9;">מלון</th>
          <th style="text-align:right;padding:4px 6px;border:1px solid #e2e4e9;">סטטוס</th>
          <th style="text-align:right;padding:4px 6px;border:1px solid #e2e4e9;">מזהה חבילה</th>
          <th style="text-align:right;padding:4px 6px;border:1px solid #e2e4e9;">ספק מזוהה</th>
          <th style="text-align:right;padding:4px 6px;border:1px solid #e2e4e9;">קישור</th>
        </tr></thead>
        <tbody>{''.join(rows) if rows else '<tr><td colspan="6" style="padding:6px;border:1px solid #e2e4e9;">אין נתונים</td></tr>'}</tbody>
      </table>
    """


def build_email_html(
    summary: dict[str, Any],
    dt_local: datetime,
    inline_image_cids: list[str] | None = None,
) -> str:
    passfail = "עבר" if summary.get("status") == "passed" else "נכשל"
    badge_color = "#137333" if summary.get("status") == "passed" else "#B3261E"

    sabre_results = summary.get("sabre_results", [])
    odyssea_results = summary.get("odyssea_results", [])

    attempts = summary.get("attempts", []) or []
    attempt_rows: list[str] = []
    for idx, attempt in enumerate(attempts, start=1):
        attempt_rows.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{_safe(attempt.get('start_date', ''))}</td>"
            f"<td>{_safe(attempt.get('end_date', ''))}</td>"
            f"<td>{_safe(attempt.get('sabre_rows_count', 0))}</td>"
            f"<td>{_safe(attempt.get('odyssea_rows_count', 0))}</td>"
            f"<td>{_safe(attempt.get('reason_he', ''))}</td>"
            "</tr>"
        )

    images_block = ""
    for cid in inline_image_cids or []:
        images_block += (
            "<div style=\"margin-top:12px;\">"
            f"<img src=\"cid:{_safe(cid)}\" style=\"max-width:100%;border:1px solid #d8d8d8;border-radius:8px;\" />"
            "</div>"
        )

    sabre_table = _build_vendor_html_table(sabre_results, "SabreLDS")
    odyssea_table = _build_vendor_html_table(odyssea_results, "Odyssea")

    return f"""
<!doctype html>
<html lang="he" dir="rtl">
  <body style="margin:0;padding:20px;background:#f6f8fb;font-family:Arial,sans-serif;color:#1f2328;">
    <div style="max-width:900px;margin:0 auto;background:#ffffff;border:1px solid #e6e8eb;border-radius:10px;padding:18px;">
      <h2 style="margin:0 0 10px 0;">דו"ח ניטור חבילות סגורות</h2>
      <div style="margin:0 0 16px 0;">
        <span style="display:inline-block;padding:6px 12px;border-radius:20px;background:{badge_color};color:#fff;font-weight:700;">{passfail}</span>
      </div>

      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr><td style="padding:6px;border-top:1px solid #eee;">תאריך ושעה</td><td style="padding:6px;border-top:1px solid #eee;">{_safe(dt_local.strftime("%Y-%m-%d %H:%M:%S"))}</td></tr>
        <tr><td style="padding:6px;border-top:1px solid #eee;">יעד</td><td style="padding:6px;border-top:1px solid #eee;">בטומי</td></tr>
        <tr><td style="padding:6px;border-top:1px solid #eee;">חלון בדיקה</td><td style="padding:6px;border-top:1px solid #eee;">{_safe(summary.get("start_date", ""))}<br>{_safe(summary.get("end_date", ""))}</td></tr>
      </table>

      <h3 style="margin:18px 0 8px 0;">מקור אמת TourGW</h3>
      <div style="margin-top:6px;">{_link(summary.get("tourgateway_url", ""))}</div>
      <div style="margin-top:8px;">SabreLDS: {_safe(summary.get("sabre_rows_count", 0))} | Odyssea: {_safe(summary.get("odyssea_rows_count", 0))}</div>

      <h3 style="margin:18px 0 8px 0;">אתר אשת</h3>
      <div>{_link(summary.get("eshet_url", ""))}</div>

      <h3 style="margin:18px 0 8px 0;">אימות כל החבילות</h3>
      {sabre_table}
      {odyssea_table}

      <h3 style="margin:18px 0 8px 0;">ניסיונות חלון תאריכים</h3>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr>
            <th style="text-align:right;padding:6px;border:1px solid #e2e4e9;">#</th>
            <th style="text-align:right;padding:6px;border:1px solid #e2e4e9;">התחלה</th>
            <th style="text-align:right;padding:6px;border:1px solid #e2e4e9;">סיום</th>
            <th style="text-align:right;padding:6px;border:1px solid #e2e4e9;">SabreLDS</th>
            <th style="text-align:right;padding:6px;border:1px solid #e2e4e9;">Odyssea</th>
            <th style="text-align:right;padding:6px;border:1px solid #e2e4e9;">סיבה</th>
          </tr>
        </thead>
        <tbody>
          {''.join(attempt_rows) if attempt_rows else '<tr><td colspan="6" style="padding:8px;border:1px solid #e2e4e9;">אין נתונים</td></tr>'}
        </tbody>
      </table>

      {images_block}
    </div>
  </body>
</html>
""".strip()
