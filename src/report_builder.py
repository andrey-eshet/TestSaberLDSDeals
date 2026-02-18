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
    return f"דו\"ח חבילות סגורות {status_he} {dt_local:%Y-%m-%d}"


def build_email_body(summary: dict[str, Any], dt_local: datetime) -> str:
    attempts_block = build_attempts_block(summary.get("attempts", []))
    passfail = "עבר" if summary.get("status") == "passed" else "נכשל"

    sabre_found = "נמצא" if summary.get("eshet_sabre_found") else "לא נמצא"
    odyssea_found = "נמצא" if summary.get("eshet_odyssea_found") else "לא נמצא"
    sabre_detected_vendor = summary.get("sabre_detected_vendor", "")
    odyssea_detected_vendor = summary.get("odyssea_detected_vendor", "")

    lines = [
        "דו\"ח ניטור חבילות סגורות",
        "",
        "תאריך ושעה",
        dt_local.strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "יעד",
        "בטומי",
        "",
        "קוד יעד",
        "50022",
        "",
        "חלון בדיקה",
        summary.get("start_date", ""),
        summary.get("end_date", ""),
        "",
        "תוצאה",
        passfail,
        "",
        "מקור אמת",
        "TourGW",
        "",
        "קישור חיפוש",
        summary.get("tourgateway_url", ""),
        "",
        "ממצאים במקור אמת",
        "SabreLDS",
        str(summary.get("sabre_rows_count", 0)),
        "Odyssea",
        str(summary.get("odyssea_rows_count", 0)),
        "",
        "מלונות שנבחרו לאימות הגעה",
        "SabreLDS",
        summary.get("sabre_hotel_name", ""),
        "Odyssea",
        summary.get("odyssea_hotel_name", ""),
        "",
        "אתר אשת",
        "",
        "קישור תוצאות",
        summary.get("eshet_url", ""),
        "",
        "אימות לפי שם מלון",
        "SabreLDS",
        sabre_found,
        "Odyssea",
        odyssea_found,
        "",
        "אימות ספק לפי מזהה חבילה",
        "SabreLDS",
        sabre_detected_vendor,
        "מזהה חבילה",
        str(summary.get("sabre_package_id", "")),
        "קישור חבילה",
        summary.get("sabre_package_url", ""),
        "Odyssea",
        odyssea_detected_vendor,
        "מזהה חבילה",
        str(summary.get("odyssea_package_id", "")),
        "קישור חבילה",
        summary.get("odyssea_package_url", ""),
        "",
        "ניסיונות חלון תאריכים",
        attempts_block,
        "",
        "קבצים מצורפים",
        "Allure",
        "צילומי מסך",
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


def build_email_html(
    summary: dict[str, Any],
    dt_local: datetime,
    inline_image_cids: list[str] | None = None,
) -> str:
    passfail = "עבר" if summary.get("status") == "passed" else "נכשל"
    badge_color = "#137333" if summary.get("status") == "passed" else "#B3261E"

    sabre_found = "נמצא" if summary.get("eshet_sabre_found") else "לא נמצא"
    odyssea_found = "נמצא" if summary.get("eshet_odyssea_found") else "לא נמצא"
    attempts = summary.get("attempts", []) or []
    rows: list[str] = []
    for idx, attempt in enumerate(attempts, start=1):
        rows.append(
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
        <tr><td style="padding:6px;border-top:1px solid #eee;">קוד יעד</td><td style="padding:6px;border-top:1px solid #eee;">50022</td></tr>
        <tr><td style="padding:6px;border-top:1px solid #eee;">חלון בדיקה</td><td style="padding:6px;border-top:1px solid #eee;">{_safe(summary.get("start_date", ""))}<br>{_safe(summary.get("end_date", ""))}</td></tr>
      </table>

      <h3 style="margin:18px 0 8px 0;">מקור אמת</h3>
      <div>TourGW</div>
      <div style="margin-top:6px;">{_link(summary.get("tourgateway_url", ""))}</div>
      <div style="margin-top:8px;">SabreLDS</div>
      <div>{_safe(summary.get("sabre_rows_count", 0))}</div>
      <div style="margin-top:6px;">Odyssea</div>
      <div>{_safe(summary.get("odyssea_rows_count", 0))}</div>

      <h3 style="margin:18px 0 8px 0;">מלונות שנבחרו לאימות הגעה</h3>
      <div>SabreLDS</div>
      <div>{_safe(summary.get("sabre_hotel_name", ""))}</div>
      <div style="margin-top:6px;">Odyssea</div>
      <div>{_safe(summary.get("odyssea_hotel_name", ""))}</div>

      <h3 style="margin:18px 0 8px 0;">אתר אשת</h3>
      <div>{_link(summary.get("eshet_url", ""))}</div>
      <div style="margin-top:8px;">SabreLDS</div>
      <div>{_safe(sabre_found)}</div>
      <div style="margin-top:6px;">Odyssea</div>
      <div>{_safe(odyssea_found)}</div>

      <h3 style="margin:18px 0 8px 0;">אימות ספק לפי מזהה חבילה</h3>
      <div>SabreLDS</div>
      <div>{_safe(summary.get("sabre_detected_vendor", ""))}</div>
      <div>{_safe(summary.get("sabre_package_id", ""))}</div>
      <div>{_link(summary.get("sabre_package_url", ""))}</div>
      <div style="margin-top:10px;">Odyssea</div>
      <div>{_safe(summary.get("odyssea_detected_vendor", ""))}</div>
      <div>{_safe(summary.get("odyssea_package_id", ""))}</div>
      <div>{_link(summary.get("odyssea_package_url", ""))}</div>

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
          {''.join(rows) if rows else '<tr><td colspan="6" style="padding:8px;border:1px solid #e2e4e9;">אין נתונים</td></tr>'}
        </tbody>
      </table>

      {images_block}
    </div>
  </body>
</html>
""".strip()
