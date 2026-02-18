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
            "sabre_hotel_name": "",
            "odyssea_hotel_name": "",
            "sabre_rows_count": 0,
            "odyssea_rows_count": 0,
            "eshet_sabre_found": False,
            "eshet_odyssea_found": False,
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

    sabre_found = False
    odyssea_found = False
    sabre_confirmed_name = ""
    odyssea_confirmed_name = ""
    sabre_result: dict = {
        "found": False,
        "package_url": "",
        "package_id": "",
        "detected_vendor": "Unknown",
        "expected_vendor": SABRE_VENDOR,
        "hotel_header": "",
        "hotel_source": "",
    }
    odyssea_result: dict = {
        "found": False,
        "package_url": "",
        "package_id": "",
        "detected_vendor": "Unknown",
        "expected_vendor": ODYSSEA_VENDOR,
        "hotel_header": "",
        "hotel_source": "",
    }
    sabre_checked: list[str] = []
    odyssea_checked: list[str] = []
    eshet_errors: list[str] = []

    sabre_candidates = list(dict.fromkeys(selected.get("sabre_hotel_candidates") or [selected["sabre_hotel_name"]]))[:5]
    odyssea_candidates = list(dict.fromkeys(selected.get("odyssea_hotel_candidates") or [selected["odyssea_hotel_name"]]))[:5]

    with allure.step("אימות הגעה באתר אשת"):
        with allure.step("אימות מלון ראשון"):
            for candidate in sabre_candidates:
                if not candidate.strip():
                    continue
                sabre_checked.append(candidate)
                try:
                    result = eshet.confirm_hotel_arrival(
                        eshet_url=eshet_url,
                        hotel_name=candidate,
                        expected_vendor=SABRE_VENDOR,
                    )
                    sabre_result = result if isinstance(result, dict) else {"found": bool(result)}
                    sabre_found = bool(sabre_result.get("found"))
                except Exception as exc:
                    sabre_found = False
                    sabre_result = {
                        "found": False,
                        "package_url": "",
                        "package_id": "",
                        "detected_vendor": "Unknown",
                        "expected_vendor": SABRE_VENDOR,
                        "hotel_header": "",
                        "hotel_source": "error",
                    }
                    eshet_errors.append(f"sabre_error: {exc}")
                    allure.attach(
                        str(exc),
                        name="eshet_sabre_error.txt",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                if sabre_found:
                    sabre_confirmed_name = candidate
                    break
            allure.attach(
                json.dumps(sabre_result, ensure_ascii=False, indent=2),
                name="eshet_sabre_result.json",
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                "נמצא" if sabre_found else "לא נמצא",
                name="eshet_sabre_status.txt",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("אימות מלון שני"):
            for candidate in odyssea_candidates:
                if not candidate.strip():
                    continue
                odyssea_checked.append(candidate)
                try:
                    result = eshet.confirm_hotel_arrival(
                        eshet_url=eshet_url,
                        hotel_name=candidate,
                        expected_vendor=ODYSSEA_VENDOR,
                    )
                    odyssea_result = result if isinstance(result, dict) else {"found": bool(result)}
                    odyssea_found = bool(odyssea_result.get("found"))
                except Exception as exc:
                    odyssea_found = False
                    odyssea_result = {
                        "found": False,
                        "package_url": "",
                        "package_id": "",
                        "detected_vendor": "Unknown",
                        "expected_vendor": ODYSSEA_VENDOR,
                        "hotel_header": "",
                        "hotel_source": "error",
                    }
                    eshet_errors.append(f"odyssea_error: {exc}")
                    allure.attach(
                        str(exc),
                        name="eshet_odyssea_error.txt",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                if odyssea_found:
                    odyssea_confirmed_name = candidate
                    break
            allure.attach(
                json.dumps(odyssea_result, ensure_ascii=False, indent=2),
                name="eshet_odyssea_result.json",
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                "נמצא" if odyssea_found else "לא נמצא",
                name="eshet_odyssea_status.txt",
                attachment_type=allure.attachment_type.TEXT,
            )

    status = "passed" if sabre_found and odyssea_found else "failed"

    final_summary = {
        "status": status,
        "created_at": now_local.isoformat(),
        "start_date": selected["start_date"],
        "end_date": selected["end_date"],
        "tourgateway_url": selected["tourgateway_url"],
        "eshet_url": eshet_url,
        "sabre_hotel_name": sabre_confirmed_name or selected["sabre_hotel_name"],
        "odyssea_hotel_name": odyssea_confirmed_name or selected["odyssea_hotel_name"],
        "sabre_hotel_name_source": selected["sabre_hotel_name"],
        "odyssea_hotel_name_source": selected["odyssea_hotel_name"],
        "sabre_checked_hotels": sabre_checked,
        "odyssea_checked_hotels": odyssea_checked,
        "sabre_rows_count": selected["sabre_rows_count"],
        "odyssea_rows_count": selected["odyssea_rows_count"],
        "eshet_sabre_found": sabre_found,
        "eshet_odyssea_found": odyssea_found,
        "sabre_package_url": sabre_result.get("package_url", ""),
        "sabre_package_id": sabre_result.get("package_id", ""),
        "sabre_detected_vendor": sabre_result.get("detected_vendor", "Unknown"),
        "sabre_expected_vendor": SABRE_VENDOR,
        "sabre_hotel_source_type": sabre_result.get("hotel_source", ""),
        "odyssea_package_url": odyssea_result.get("package_url", ""),
        "odyssea_package_id": odyssea_result.get("package_id", ""),
        "odyssea_detected_vendor": odyssea_result.get("detected_vendor", "Unknown"),
        "odyssea_expected_vendor": ODYSSEA_VENDOR,
        "odyssea_hotel_source_type": odyssea_result.get("hotel_source", ""),
        "eshet_errors": eshet_errors,
        "attempts": attempts,
    }

    write_json(SUMMARY_PATH, final_summary)
    allure.attach(
        json.dumps(final_summary, ensure_ascii=False, indent=2),
        name="summary_selected_window.json",
        attachment_type=allure.attachment_type.JSON,
    )

    if not sabre_found or not odyssea_found:
        pytest.fail("На Эшет подтвержден не полный набор отелей")

    assert selected["sabre_hotel_name"], f"Не найден отель для {SABRE_VENDOR}"
    assert selected["odyssea_hotel_name"], f"Не найден отель для {ODYSSEA_VENDOR}"
