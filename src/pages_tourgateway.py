from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlencode

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.config import (
    ODYSSEA_VENDOR,
    SABRE_VENDOR,
    TOURGW_BASE_URL,
    TOURGW_STATIC_QUERY,
)
from src.utils import clean_hotel_name, normalize_text


class TourGatewayPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @staticmethod
    def build_search_url(start_date: date, end_date: date) -> str:
        params = dict(TOURGW_STATIC_QUERY)
        params["startDate"] = start_date.isoformat()
        params["endDate"] = end_date.isoformat()
        return f"{TOURGW_BASE_URL}?{urlencode(params)}"

    def open_and_collect(self, start_date: date, end_date: date) -> dict[str, Any]:
        url = self.build_search_url(start_date, end_date)

        self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self.page.wait_for_load_state("networkidle", timeout=60_000)

        try:
            self.page.wait_for_selector("table tbody", state="attached", timeout=30_000)
        except PlaywrightTimeoutError as exc:
            raise AssertionError("Не найдена таблица результатов TourGW") from exc

        parsed = self.page.evaluate(
            r"""
            () => {
                const norm = (value) => (value || '').toString().trim().toLowerCase();
                const tables = Array.from(document.querySelectorAll('table'));

                for (const table of tables) {
                    const body = table.querySelector('tbody');
                    if (!body) continue;

                    const rows = Array.from(body.querySelectorAll('tr'));

                    const headerCells = Array.from(table.querySelectorAll('thead th, thead td'));
                    let headers = headerCells.map((el, idx) => norm(el.textContent) || `col_${idx}`);

                    const rowData = rows.map((row) => {
                        return Array.from(row.querySelectorAll('td, th')).map((cell) => {
                            return (cell.textContent || '').replace(/\s+/g, ' ').trim();
                        });
                    });

                    if (!headers.length && rowData.length > 0) {
                        headers = rowData[0].map((_, idx) => `col_${idx}`);
                    }

                    let vendorIndex = headers.findIndex((h) => h.includes('vendor'));
                    let hotelIndex = headers.findIndex((h) => h.includes('hotel'));

                    if (vendorIndex < 0 && rowData.length > 0) {
                        let bestIndex = -1;
                        let bestScore = 0;
                        const maxColumns = Math.max(...rowData.map((r) => r.length));

                        for (let col = 0; col < maxColumns; col += 1) {
                            let score = 0;
                            for (const row of rowData) {
                                const value = norm(row[col]);
                                if (value === 'sabrelds' || value === 'odyssea') {
                                    score += 1;
                                }
                            }
                            if (score > bestScore) {
                                bestScore = score;
                                bestIndex = col;
                            }
                        }

                        if (bestScore > 0) {
                            vendorIndex = bestIndex;
                        }
                    }

                    if (hotelIndex < 0) {
                        hotelIndex = headers.findIndex((h) => h.includes('name') || h.includes('property'));
                    }
                    if (hotelIndex < 0) {
                        hotelIndex = 0;
                    }

                    return {
                        headers,
                        rowData,
                        vendorIndex,
                        hotelIndex,
                        tbodyHtml: body.outerHTML,
                        tableHtml: table.outerHTML,
                    };
                }

                return null;
            }
            """
        )

        if not parsed:
            raise AssertionError("Не удалось разобрать таблицу TourGW")

        sabre_hotels: list[str] = []
        odyssea_hotels: list[str] = []

        row_data: list[list[str]] = parsed.get("rowData", [])
        vendor_index = int(parsed.get("vendorIndex", -1))
        hotel_index = int(parsed.get("hotelIndex", 0))

        for row in row_data:
            if vendor_index < 0 or vendor_index >= len(row):
                continue

            vendor = row[vendor_index].strip()
            hotel = row[hotel_index].strip() if hotel_index < len(row) else ""
            if not hotel:
                hotel = next((cell.strip() for cell in row if cell.strip()), "")
            hotel = clean_hotel_name(hotel)
            if not hotel:
                continue

            norm_vendor = normalize_text(vendor)
            if norm_vendor == normalize_text(SABRE_VENDOR):
                sabre_hotels.append(hotel)
            if norm_vendor == normalize_text(ODYSSEA_VENDOR):
                odyssea_hotels.append(hotel)

        return {
            "url": url,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "sabre_rows_count": len(sabre_hotels),
            "odyssea_rows_count": len(odyssea_hotels),
            "sabre_hotel_name": sabre_hotels[0] if sabre_hotels else "",
            "odyssea_hotel_name": odyssea_hotels[0] if odyssea_hotels else "",
            "sabre_hotel_candidates": list(dict.fromkeys(sabre_hotels)),
            "odyssea_hotel_candidates": list(dict.fromkeys(odyssea_hotels)),
            "tbody_html": parsed.get("tbodyHtml", ""),
            "table_html": parsed.get("tableHtml", ""),
            "screenshot_bytes": self.page.screenshot(full_page=True),
        }
