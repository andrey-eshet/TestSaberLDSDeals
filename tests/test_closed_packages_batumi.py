from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import allure
import pytest

from src.config import ODYSSEA_VENDOR, SABRE_VENDOR, Settings
from src.pages_eshet import EshetSearchPage
from src.pages_tourgateway import TourGatewayPage
from src.utils import add_months, ensure_dir, now_in_tz, write_json

SUMMARY_PATH = Path("artifacts") / "summary.json"
MAIL_SCREENSHOT_DIR = Path("artifacts") / "mail"
MAIL_TOURGW_SCREENSHOT = MAIL_SCREENSHOT_DIR / "tourgw_selected_vendors.png"


def _reason_for_next_step(sabre_rows: int, odyssea_rows: int) -> str:
    if sabre_rows > 0 and odyssea_rows > 0:
        return "נבחר חלון"
    if sabre_rows == 0 and odyssea_rows == 0:
        return "לא נמצאו שני ספקים"
    return "לא נמצא ספק אחד לפחות"


@allure.title("בדיקת חבילות סגורות לבטומי")
def test_closed_packages_batumi(page, settings: Settings) -> None:
    ensure_dir(SUMMARY_PATH.parent)

    now_local = now_in_tz(settings.schedule_tz)
    base_month_date = add_months(now_local.date(), 1)
    base_start_offsets = [1, 2, 3]

    # attempt_id, end_base_shift_days, end_length_days
    # end_date = base_start + end_base_shift_days + end_length_days
    end_attempts = [
        (1, 0, 7),
        (2, 0, 6),
        (3, 0, 8),
        (4, -1, 7),
        (5, -2, 7),
        (6, -3, 7),
        (7, -1, 6),
        (8, -2, 6),
        (9, -3, 6),
        (10, -1, 8),
        (11, -2, 8),
        (12, -3, 8),
    ]
    start_shifts = [-1, 0, 1]

    attempts: list[dict] = []
    selected: dict | None = None
    selected_tourgw_screenshot: bytes | None = None

    tourgw = TourGatewayPage(page)

    with allure.step("בחירת חלון תאריכים ממקור אמת"):
        for base_shift_days in base_start_offsets:
            base_start = base_month_date + timedelta(days=base_shift_days)

            for attempt_id, end_base_shift_days, end_length_days in end_attempts:
                end_date = base_start + timedelta(days=end_base_shift_days + end_length_days)

                for shift in start_shifts:
                    start_date = base_start + timedelta(days=shift)

                    with allure.step("איסוף תוצאות מהטבלה"):
                        result = tourgw.open_and_collect(start_date=start_date, end_date=end_date)

                        allure.attach(
                            result["screenshot_bytes"],
                            name=f"tourgw_base_{base_shift_days}_attempt_{attempt_id}_shift_{shift}.png",
                            attachment_type=allure.attachment_type.PNG,
                        )
                        allure.attach(
                            result["tbody_html"],
                            name=f"tourgw_base_{base_shift_days}_attempt_{attempt_id}_shift_{shift}.html",
                            attachment_type=allure.attachment_type.HTML,
                        )

                    sabre_rows = int(result["sabre_rows_count"])
                    odyssea_rows = int(result["odyssea_rows_count"])
                    reason_he = _reason_for_next_step(sabre_rows=sabre_rows, odyssea_rows=odyssea_rows)

                    attempt_payload = {
                        "attempt_id": attempt_id,
                        "base_shift_days": base_shift_days,
                        "end_base_shift_days": end_base_shift_days,
                        "end_length_days": end_length_days,
                        "start_shift_days": shift,
                        "start_date": result["start_date"],
                        "end_date": result["end_date"],
                        "tourgateway_url": result["url"],
                        "sabre_rows_count": sabre_rows,
                        "odyssea_rows_count": odyssea_rows,
                        "reason_he": reason_he,
                    }
                    attempts.append(attempt_payload)

                    if sabre_rows > 0 and odyssea_rows > 0:
                        selected = {
                            **attempt_payload,
                            "sabre_hotel_name": result["sabre_hotel_name"],
                            "odyssea_hotel_name": result["odyssea_hotel_name"],
                            "sabre_hotel_candidates": result.get("sabre_hotel_candidates", []),
                            "odyssea_hotel_candidates": result.get("odyssea_hotel_candidates", []),
                        }
                        selected_tourgw_screenshot = result.get("screenshot_bytes")
                        break

                if selected:
                    break

            if selected:
                break

    if not selected:
        failed_summary = {
            "status": "failed",
            "created_at": now_local.isoformat(),
            "start_date": "",
            "end_date": "",
            "tourgateway_url": "",
            "eshet_url": "",
            "sabre_rows_count": 0,
            "odyssea_rows_count": 0,
            "sabre_results": [],
            "odyssea_results": [],
            "attempts": attempts,
        }
        write_json(SUMMARY_PATH, failed_summary)

        allure.attach(
            json.dumps(failed_summary, ensure_ascii=False, indent=2),
            name="summary_no_window.json",
            attachment_type=allure.attachment_type.JSON,
        )

        pytest.fail("Не найдено окно дат с двумя поставщиками в TourGW")

    start_date = date.fromisoformat(selected["start_date"])
    end_date = date.fromisoformat(selected["end_date"])
    ensure_dir(MAIL_SCREENSHOT_DIR)
    if selected_tourgw_screenshot:
        MAIL_TOURGW_SCREENSHOT.write_bytes(selected_tourgw_screenshot)

    eshet = EshetSearchPage(page, settings)
    eshet_url = eshet.build_search_url(start_date=start_date, end_date=end_date)

    sabre_candidates = list(dict.fromkeys(
        selected.get("sabre_hotel_candidates") or [selected["sabre_hotel_name"]]
    ))
    odyssea_candidates = list(dict.fromkeys(
        selected.get("odyssea_hotel_candidates") or [selected["odyssea_hotel_name"]]
    ))

    sabre_results: list[dict] = []
    odyssea_results: list[dict] = []

    with allure.step("אימות כל החבילות באתר אשת"):
        with allure.step(f"אימות {len(sabre_candidates)} מלונות SabreLDS"):
            sabre_results = eshet.confirm_all_hotels(
                eshet_url=eshet_url,
                hotel_candidates=sabre_candidates,
                expected_vendor=SABRE_VENDOR,
            )
            allure.attach(
                json.dumps(sabre_results, ensure_ascii=False, indent=2),
                name="eshet_sabre_all_results.json",
                attachment_type=allure.attachment_type.JSON,
            )

        with allure.step(f"אימות {len(odyssea_candidates)} מלונות Odyssea"):
            odyssea_results = eshet.confirm_all_hotels(
                eshet_url=eshet_url,
                hotel_candidates=odyssea_candidates,
                expected_vendor=ODYSSEA_VENDOR,
            )
            allure.attach(
                json.dumps(odyssea_results, ensure_ascii=False, indent=2),
                name="eshet_odyssea_all_results.json",
                attachment_type=allure.attachment_type.JSON,
            )

    sabre_found_count = sum(1 for r in sabre_results if r.get("found"))
    odyssea_found_count = sum(1 for r in odyssea_results if r.get("found"))
    sabre_total = len(sabre_results)
    odyssea_total = len(odyssea_results)
    all_found = sabre_found_count == sabre_total and odyssea_found_count == odyssea_total
    status = "passed" if all_found else "failed"

    final_summary = {
        "status": status,
        "created_at": now_local.isoformat(),
        "start_date": selected["start_date"],
        "end_date": selected["end_date"],
        "tourgateway_url": selected["tourgateway_url"],
        "eshet_url": eshet_url,
        "sabre_rows_count": selected["sabre_rows_count"],
        "odyssea_rows_count": selected["odyssea_rows_count"],
        "sabre_found_count": sabre_found_count,
        "sabre_total_count": sabre_total,
        "odyssea_found_count": odyssea_found_count,
        "odyssea_total_count": odyssea_total,
        "sabre_results": sabre_results,
        "odyssea_results": odyssea_results,
        "attempts": attempts,
    }

    write_json(SUMMARY_PATH, final_summary)
    allure.attach(
        json.dumps(final_summary, ensure_ascii=False, indent=2),
        name="summary_all_packages.json",
        attachment_type=allure.attachment_type.JSON,
    )

    if not all_found:
        missing: list[str] = []
        for r in sabre_results:
            if not r.get("found"):
                missing.append(f"SabreLDS: {r.get('hotel_name', '?')}")
        for r in odyssea_results:
            if not r.get("found"):
                missing.append(f"Odyssea: {r.get('hotel_name', '?')}")
        pytest.fail(
            f"Не все пакеты найдены на Эшет. "
            f"SabreLDS: {sabre_found_count}/{sabre_total}, "
            f"Odyssea: {odyssea_found_count}/{odyssea_total}. "
            f"Не найдены: {', '.join(missing)}"
        )
