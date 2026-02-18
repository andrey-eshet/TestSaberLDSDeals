from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import allure
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from src.config import Settings, load_settings
from src.utils import ensure_dir


@pytest.fixture(scope="session")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def browser(settings: Settings) -> Browser:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.headless)
        yield browser
        browser.close()


@pytest.fixture()
def page(browser: Browser) -> Page:
    context = browser.new_context(locale="he-IL")
    page = context.new_page()
    page.set_default_timeout(45_000)
    yield page
    context.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or report.passed:
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    failure_dir = ensure_dir(Path("artifacts") / "failures")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    png_path = failure_dir / f"{item.name}_{stamp}.png"
    html_path = failure_dir / f"{item.name}_{stamp}.html"

    try:
        page.screenshot(path=str(png_path), full_page=True)
        allure.attach.file(
            str(png_path),
            name="צילום כשל",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception:
        pass

    try:
        html_path.write_text(page.content(), encoding="utf-8")
        allure.attach.file(
            str(html_path),
            name="html כשל",
            attachment_type=allure.attachment_type.HTML,
        )
    except Exception:
        pass


def pytest_configure() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
