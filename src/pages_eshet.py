from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

import allure
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError

from src.config import (
    ESHET_BASE_URL,
    ESHET_STATIC_QUERY,
    ODYSSEA_VENDOR,
    SABRE_VENDOR,
    Settings,
)
from src.utils import clean_hotel_name, ensure_dir, normalize_text

MAIL_SCREENSHOT_DIR = Path("artifacts") / "mail"
MAIL_SABRE_SCREENSHOT = MAIL_SCREENSHOT_DIR / "eshet_package_sabre.png"
MAIL_ODYSSEA_SCREENSHOT = MAIL_SCREENSHOT_DIR / "eshet_package_odyssea.png"


class EshetSearchPage:
    def __init__(self, page: Page, settings: Settings) -> None:
        self.page = page
        self.settings = settings

    @staticmethod
    def build_search_url(start_date: date, end_date: date) -> str:
        params = dict(ESHET_STATIC_QUERY)
        params["startdate"] = start_date.strftime("%d.%m.%Y")
        params["enddate"] = end_date.strftime("%d.%m.%Y")
        return f"{ESHET_BASE_URL}?{urlencode(params)}"

    def open_results(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        try:
            self.page.wait_for_load_state("networkidle", timeout=15_000)
        except PlaywrightTimeoutError:
            # Eshet often keeps background network activity.
            # We continue with fixed wait according to test requirement.
            pass
        self.page.wait_for_timeout(self.settings.eshet_results_wait_ms)

    def _result_cards(self) -> Locator:
        return self.page.locator(
            "article, li, [class*='card'], [data-testid*='card'], [class*='result']"
        )

    @staticmethod
    def _normalize_for_match(value: str) -> str:
        return normalize_text(clean_hotel_name(value))

    @staticmethod
    def _match_hotel_name(left: str, right: str) -> bool:
        a = EshetSearchPage._normalize_for_match(left)
        b = EshetSearchPage._normalize_for_match(right)
        if not a or not b:
            return False
        return a in b or b in a

    @staticmethod
    def _classify_vendor_by_package_id(package_id: str) -> str:
        digits = re.sub(r"\D+", "", package_id or "")
        if len(digits) < 7:
            return ODYSSEA_VENDOR
        if len(digits) > 8:
            return SABRE_VENDOR
        return "Unknown"

    @staticmethod
    def _normalize_room_key_for_url(room_key: str) -> str:
        parts = room_key.split("_")
        if len(parts) >= 4 and parts[1] == "0" and parts[2] == "0":
            return f"{parts[0]}_{'_'.join(parts[3:])}"
        return room_key

    @staticmethod
    def _mail_screenshot_path_for_vendor(expected_vendor: str) -> Path:
        if expected_vendor == SABRE_VENDOR:
            return MAIL_SABRE_SCREENSHOT
        if expected_vendor == ODYSSEA_VENDOR:
            return MAIL_ODYSSEA_SCREENSHOT
        return MAIL_SCREENSHOT_DIR / "eshet_package_unknown.png"

    def _deals_api_url_from_search_url(self, eshet_url: str) -> str:
        parsed = urlparse(eshet_url)
        query = parse_qs(parsed.query)

        params = {
            "destination": (query.get("destination") or [""])[0],
            "startdate": (query.get("startdate") or [""])[0],
            "enddate": (query.get("enddate") or [""])[0],
            "r0": (query.get("r0") or ["2_"])[0],
            "Subject": (query.get("subject") or ["27"])[0],
        }
        return f"https://www.eshet.com/api/deals/searchresults?{urlencode(params)}"

    def _build_package_url_from_deal(self, deal: dict) -> dict | None:
        pricing_options = deal.get("PricingOptions") or []
        if not pricing_options:
            return None

        room_key = str(pricing_options[0])
        room_prices = deal.get("RoomPricesDictionary") or {}
        room = room_prices.get(room_key) or {}

        package_id = str(room.get("PackageId") or deal.get("PackageId") or "").strip()
        if not package_id:
            return None

        room_price = room.get("RoomPrice") or {}
        price_raw = (
            room_price.get("DisplayPriceAfterDiscount")
            or room_price.get("PriceAfterDiscount")
            or room_price.get("NetPrice")
            or 0
        )
        try:
            price_value = str(int(round(float(price_raw))))
        except Exception:
            price_value = ""

        hotel_name = clean_hotel_name(str(deal.get("Name") or ""))
        slug = quote(hotel_name.lower(), safe="")
        room_key_url = self._normalize_room_key_for_url(room_key)
        flight_key = str(deal.get("FlightPricingKey") or "")
        hotel_id = str(deal.get("HotelId") or "")
        subject_value = str(deal.get("Subject") if deal.get("Subject") is not None else "27")
        destination_value = str(deal.get("DestinationCode") or ESHET_STATIC_QUERY["destination"])
        start_date = str(deal.get("StartDate") or "")
        end_date = str(deal.get("EndDate") or "")

        query = {
            "startdate": start_date,
            "enddate": end_date,
            "hotelId": hotel_id,
            "flight": flight_key,
            "price": price_value,
            "roomskeys": room_key_url,
            "destination": destination_value,
            "packageid": package_id,
            "Subject": subject_value,
        }
        url = f"https://www.eshet.com/deals/dealdetails/georgia/batumi/{slug}?{urlencode(query)}"
        return {
            "url": url,
            "hotel_name": hotel_name,
            "package_id": package_id,
            "detected_vendor": self._classify_vendor_by_package_id(package_id),
        }

    def _find_package_via_api(
        self,
        eshet_url: str,
        hotel_name: str,
        expected_vendor: str,
    ) -> dict | None:
        api_url = self._deals_api_url_from_search_url(eshet_url)
        response = self.page.request.get(api_url, timeout=120_000)
        if response.status != 200:
            return None

        payload = response.json()
        deals = payload.get("dealsDictionary") or {}
        if not isinstance(deals, dict):
            return None

        candidates: list[dict] = []

        for deal in deals.values():
            if not isinstance(deal, dict):
                continue
            deal_name = clean_hotel_name(str(deal.get("Name") or ""))
            if not self._match_hotel_name(hotel_name, deal_name):
                continue

            package_data = self._build_package_url_from_deal(deal)
            if not package_data:
                continue

            package_data["api_url"] = api_url
            candidates.append(package_data)

        if not candidates:
            return None

        preferred = [c for c in candidates if c.get("detected_vendor") == expected_vendor]
        if preferred:
            return preferred[0]
        return candidates[0]

    def _validate_package_url(
        self,
        package_url: str,
        hotel_name: str,
        expected_vendor: str,
        source: str,
        package_name_hint: str = "",
    ) -> dict:
        parsed_url = urlparse(package_url)
        package_id = (parse_qs(parsed_url.query).get("packageid") or [""])[0]
        detected_vendor = self._classify_vendor_by_package_id(package_id)

        self.page.goto(package_url, wait_until="domcontentloaded", timeout=120_000)
        self.page.wait_for_timeout(2_000)

        h1 = self.page.locator("h1")
        header_text = h1.first.inner_text().strip() if h1.count() > 0 else ""

        package_screenshot = self.page.screenshot(full_page=True)
        allure.attach(
            package_screenshot,
            name=f"eshet_package_{source}.png",
            attachment_type=allure.attachment_type.PNG,
        )
        ensure_dir(MAIL_SCREENSHOT_DIR)
        self._mail_screenshot_path_for_vendor(expected_vendor).write_bytes(package_screenshot)

        header_ok = self._match_hotel_name(hotel_name, header_text)
        hint_ok = self._match_hotel_name(hotel_name, package_name_hint)

        slug = unquote(parsed_url.path.rsplit("/", 1)[-1]).replace("-", " ").strip()
        slug_ok = self._match_hotel_name(hotel_name, slug)

        vendor_ok = detected_vendor == expected_vendor
        found = vendor_ok and (header_ok or hint_ok or slug_ok)

        return {
            "found": found,
            "package_url": package_url,
            "package_id": package_id,
            "detected_vendor": detected_vendor,
            "expected_vendor": expected_vendor,
            "hotel_header": header_text,
            "hotel_source": source,
        }

    def _find_visible_card(self, hotel_name: str) -> Locator | None:
        cards = self._result_cards().filter(has_text=hotel_name)
        count = cards.count()
        for idx in range(count):
            card = cards.nth(idx)
            if card.is_visible():
                return card

        text_match = self.page.get_by_text(hotel_name, exact=False)
        if text_match.count() > 0 and text_match.first.is_visible():
            return text_match.first

        return None

    def _click_card(self, card: Locator, hotel_name: str) -> None:
        preferred_click = card.locator("a, button, h1, h2, h3, [role='link']").filter(
            has_text=hotel_name
        )

        if preferred_click.count() > 0:
            preferred_click.first.click(timeout=20_000)
            return

        any_clickable = card.locator("a, button, h1, h2, h3, [role='link']")
        if any_clickable.count() > 0:
            any_clickable.first.click(timeout=20_000)
            return

        card.click(timeout=20_000)

    def _find_hotel_in_schema(self, hotel_name: str) -> dict | None:
        return self.page.evaluate(
            """
            (targetRaw) => {
                const normalize = (value) =>
                    (value || '').toString().replace(/\\s+/g, ' ').trim().toLowerCase();
                const target = normalize(targetRaw);
                if (!target) return null;

                const isMatch = (name) => {
                    const normName = normalize(name);
                    return !!normName && (normName.includes(target) || target.includes(normName));
                };

                const scripts = Array.from(
                    document.querySelectorAll('script[type="application/ld+json"]')
                );

                for (const script of scripts) {
                    let parsed = null;
                    try {
                        parsed = JSON.parse(script.textContent || '');
                    } catch (_) {
                        continue;
                    }

                    const queue = Array.isArray(parsed) ? [...parsed] : [parsed];
                    while (queue.length > 0) {
                        const node = queue.shift();
                        if (!node || typeof node !== 'object') {
                            continue;
                        }

                        const name = node.name || node.headline || '';
                        const url = node.url || node['@id'] || '';

                        if (isMatch(name) && typeof url === 'string' && url.length > 0) {
                            return { name, url };
                        }

                        for (const key of Object.keys(node)) {
                            const value = node[key];
                            if (value && typeof value === 'object') {
                                queue.push(value);
                            }
                        }
                    }
                }

                return null;
            }
            """,
            hotel_name,
        )

    def _open_and_validate_schema_item(self, schema_item: dict, hotel_name: str) -> bool:
        if not schema_item or not schema_item.get("url"):
            return False

        self.page.goto(str(schema_item["url"]), wait_until="domcontentloaded", timeout=120_000)
        self.page.wait_for_timeout(2_000)

        h1 = self.page.locator("h1")
        header_text = ""
        if h1.count() > 0:
            header_text = h1.first.inner_text().strip()

        schema_name = str(schema_item.get("name", "")).strip()
        norm_header = normalize_text(header_text)
        norm_hotel = normalize_text(hotel_name)
        norm_schema_name = normalize_text(schema_name)

        allure.attach(
            self.page.screenshot(full_page=True),
            name="eshet_hotel_page_from_schema.png",
            attachment_type=allure.attachment_type.PNG,
        )

        if norm_hotel and norm_hotel in norm_header:
            return True
        if norm_schema_name and norm_schema_name in norm_header:
            return True

        parsed = urlparse(str(schema_item["url"]))
        slug = unquote(parsed.path.rsplit("/", 1)[-1]).replace("-", " ").strip()
        norm_slug = normalize_text(slug)
        if norm_slug and (norm_hotel in norm_slug or norm_slug in norm_hotel):
            return True

        return False

    def confirm_hotel_arrival(self, eshet_url: str, hotel_name: str, expected_vendor: str) -> dict:
        hotel_name = clean_hotel_name(hotel_name)
        if not hotel_name.strip():
            return {
                "found": False,
                "package_url": "",
                "package_id": "",
                "detected_vendor": "Unknown",
                "expected_vendor": expected_vendor,
                "hotel_header": "",
                "hotel_source": "empty_hotel_name",
            }

        self.open_results(eshet_url)
        allure.attach(
            self.page.screenshot(full_page=True),
            name="eshet_results_loaded.png",
            attachment_type=allure.attachment_type.PNG,
        )

        try:
            api_package = self._find_package_via_api(
                eshet_url=eshet_url,
                hotel_name=hotel_name,
                expected_vendor=expected_vendor,
            )
        except Exception:
            api_package = None

        if api_package:
            return self._validate_package_url(
                package_url=str(api_package["url"]),
                hotel_name=hotel_name,
                expected_vendor=expected_vendor,
                source="api",
                package_name_hint=str(api_package.get("hotel_name") or ""),
            )

        schema_item = self._find_hotel_in_schema(hotel_name)
        if schema_item and schema_item.get("url"):
            return self._validate_package_url(
                package_url=str(schema_item["url"]),
                hotel_name=hotel_name,
                expected_vendor=expected_vendor,
                source="schema",
                package_name_hint=str(schema_item.get("name") or ""),
            )

        for scroll_idx in range(self.settings.eshet_max_scrolls + 1):
            card = self._find_visible_card(hotel_name)
            if card is not None:
                self._click_card(card, hotel_name)
                self.page.wait_for_load_state("domcontentloaded", timeout=120_000)
                self.page.wait_for_timeout(2_000)
                if "/deals/dealdetails/" in self.page.url.lower():
                    return self._validate_package_url(
                        package_url=self.page.url,
                        hotel_name=hotel_name,
                        expected_vendor=expected_vendor,
                        source="click",
                    )

            if scroll_idx < self.settings.eshet_max_scrolls:
                self.page.mouse.wheel(0, 2500)
                self.page.wait_for_timeout(self.settings.eshet_scroll_wait_ms)

        schema_item = self._find_hotel_in_schema(hotel_name)
        if schema_item and schema_item.get("url"):
            return self._validate_package_url(
                package_url=str(schema_item["url"]),
                hotel_name=hotel_name,
                expected_vendor=expected_vendor,
                source="schema_after_scroll",
                package_name_hint=str(schema_item.get("name") or ""),
            )

        cards_count = self._result_cards().count()
        allure.attach(
            self.page.content(),
            name="eshet_results_fragment.html",
            attachment_type=allure.attachment_type.HTML,
        )
        allure.attach(
            self.page.screenshot(full_page=True),
            name="eshet_results_not_found.png",
            attachment_type=allure.attachment_type.PNG,
        )

        if cards_count == 0:
            raise AssertionError("Нужен html карточки результата для точного локатора")

        return {
            "found": False,
            "package_url": "",
            "package_id": "",
            "detected_vendor": "Unknown",
            "expected_vendor": expected_vendor,
            "hotel_header": "",
            "hotel_source": "not_found",
        }
