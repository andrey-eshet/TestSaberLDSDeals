from __future__ import annotations

from pathlib import Path
import smtplib
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_settings
from src.mailer import send_email
from src.report_builder import build_email_body, build_email_html, build_email_subject
from src.schedule import evaluate_schedule
from src.utils import (
    build_allure_generate_command,
    now_in_tz,
    read_json,
    run_command,
)

ALLURE_RESULTS_DIR = ROOT / "allure-results"
ALLURE_REPORT_DIR = ROOT / "allure-report"
SUMMARY_PATH = ROOT / "artifacts" / "summary.json"
MAIL_SCREENSHOT_DIR = ROOT / "artifacts" / "mail"


def _collect_mail_screenshots() -> list[Path]:
    required = [
        ROOT / "artifacts" / "mail" / "tourgw_selected_vendors.png",
        ROOT / "artifacts" / "mail" / "eshet_package_sabre.png",
        ROOT / "artifacts" / "mail" / "eshet_package_odyssea.png",
    ]
    return [path for path in required if path.exists()]


def _send_with_fallback(
    settings,
    subject: str,
    body_text: str,
    summary: dict,
    dt_local,
    screenshots: list[Path],
) -> None:
    variants = [screenshots[:3], screenshots[:1], []]
    last_exc: Exception | None = None

    for idx, candidate in enumerate(variants, start=1):
        cids = [f"screenshot_{i + 1}" for i in range(len(candidate))]
        body_html = build_email_html(
            summary=summary,
            dt_local=dt_local,
            inline_image_cids=cids,
        )
        inline_images = list(zip(cids, candidate))
        try:
            send_email(
                settings=settings,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=[],
                inline_images=inline_images,
            )
            if idx == 1:
                print("Email sent with inline screenshots.")
            elif idx == 2:
                print("Email sent with one inline screenshot.")
            else:
                print("Email sent without screenshots.")
            return
        except smtplib.SMTPResponseException as exc:
            last_exc = exc
            if exc.smtp_code == 552:
                continue
            raise
        except smtplib.SMTPException as exc:
            last_exc = exc
            if idx < len(variants):
                continue
            raise

    if last_exc:
        raise last_exc


def _send_mail(settings, decision, force: bool = False) -> None:
    if not force and not decision.should_send_mail:
        print("Mail sending disabled by schedule decision.")
        return

    if not settings.smtp_ready():
        print("SMTP configuration is missing. Email sending skipped.")
        return

    summary = read_json(SUMMARY_PATH)
    if not summary:
        summary = {"status": "unknown", "attempts": []}

    now_local = now_in_tz(settings.schedule_tz)
    subject = build_email_subject(summary=summary, dt_local=now_local)
    body_text = build_email_body(summary=summary, dt_local=now_local)
    screenshots = _collect_mail_screenshots()
    _send_with_fallback(
        settings=settings,
        subject=subject,
        body_text=body_text,
        summary=summary,
        dt_local=now_local,
        screenshots=screenshots,
    )


def main() -> int:
    email_only = "--email-only" in sys.argv

    settings = load_settings()
    decision = evaluate_schedule(settings)

    print(f"Current local time: {decision.now_local.isoformat()}")
    print(f"Schedule decision: {decision.reason}")

    if email_only:
        _send_mail(settings, decision, force=True)
        return 0

    if not decision.should_run_tests:
        print("Outside work schedule. Tests and email are skipped with exit code 0.")
        return 0

    if ALLURE_RESULTS_DIR.exists():
        shutil.rmtree(ALLURE_RESULTS_DIR, ignore_errors=True)
    if ALLURE_REPORT_DIR.exists():
        shutil.rmtree(ALLURE_REPORT_DIR, ignore_errors=True)
    if MAIL_SCREENSHOT_DIR.exists():
        shutil.rmtree(MAIL_SCREENSHOT_DIR, ignore_errors=True)

    pytest_code = run_command([sys.executable, "-m", "pytest"], cwd=ROOT)
    allure_cmd = build_allure_generate_command(
        results_dir=ALLURE_RESULTS_DIR,
        report_dir=ALLURE_REPORT_DIR,
    )
    if allure_cmd:
        report_code = run_command(allure_cmd, cwd=ROOT)
    else:
        print("Allure CLI not found. Report generation skipped.")
        report_code = 127

    if report_code != 0:
        if ALLURE_REPORT_DIR.exists():
            shutil.rmtree(ALLURE_REPORT_DIR, ignore_errors=True)
        print("Allure report generation failed.")

    _send_mail(settings, decision)

    if pytest_code != 0:
        return pytest_code
    return report_code


if __name__ == "__main__":
    raise SystemExit(main())
