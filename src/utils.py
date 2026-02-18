from __future__ import annotations

import calendar
import json
import os
import re
import shutil
import subprocess
import zipfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    collapsed = re.sub(r"\s+", " ", value)
    return collapsed.strip().lower()


def clean_hotel_name(value: str | None) -> str:
    if not value:
        return ""

    text = re.sub(r"\s+", " ", value).strip()
    text = re.split(r"(?i)\bnights?\s*:\s*\d+\b|\bshift\s*:\s*-?\d+\b", text)[0]
    text = re.sub(r"\s*[|,;/:-]\s*$", "", text).strip()
    return text


def add_months(source_date: date, months: int) -> date:
    month_index = source_date.month - 1 + months
    year = source_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year=year, month=month, day=day)


def now_in_tz(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    ensure_dir(zip_path.parent)
    if zip_path.exists():
        zip_path.unlink()

    if not source_dir.exists():
        return

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in source_dir.rglob("*"):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(source_dir)
            zf.write(file_path, arcname=str(relative))


def find_allure_executable() -> str | None:
    if os.name != "nt":
        return shutil.which("allure")

    candidates: list[Path] = []
    home = Path.home()
    candidates.append(home / "scoop" / "shims" / "allure.cmd")
    candidates.append(home / "scoop" / "apps" / "allure" / "current" / "bin" / "allure.bat")

    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        candidates.append(Path(appdata) / "npm" / "allure.cmd")

    for name in ["allure.cmd", "allure.bat", "allure"]:
        from_path = shutil.which(name)
        if from_path:
            candidates.append(Path(from_path))

    for candidate in candidates:
        text_path = str(candidate)
        is_windows_path = bool(re.match(r"^[A-Za-z]:\\", text_path)) or text_path.startswith("\\\\")
        if candidate.exists() and is_windows_path:
            return text_path

    return None


def build_allure_generate_command(results_dir: Path, report_dir: Path) -> list[str] | None:
    executable = find_allure_executable()
    if not executable:
        return None

    args = ["generate", str(results_dir), "-o", str(report_dir), "--clean"]

    lowered = executable.lower()
    if os.name == "nt" and (lowered.endswith(".cmd") or lowered.endswith(".bat")):
        return [r"C:\Windows\System32\cmd.exe", "/c", executable, *args]

    return [executable, *args]


def run_command(cmd: list[str], cwd: Path) -> int:
    env = os.environ.copy()
    if not env.get("TMPDIR") and Path("/tmp").exists():
        env["TMPDIR"] = "/tmp"

    try:
        completed = subprocess.run(cmd, cwd=cwd, check=False, env=env)
        return completed.returncode
    except FileNotFoundError:
        print(f"Command not found: {' '.join(cmd)}")
        return 127
    except OSError as exc:
        print(f"Command execution failed: {' '.join(cmd)}")
        print(str(exc))
        return 1
