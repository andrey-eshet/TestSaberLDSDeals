# autoTestEshet

מאגר של בדיקות אוטומטיות לניטור חבילות סגורות ליעד באטומי.

מחסנית הטכנולוגיות:

* Python
* Playwright
* pytest
* Allure

מה נבדק:

1. ב־TourGW נמצא חלון תאריכים שבו קיימות חבילות סגורות משני ספקים.
2. הספקים במקור האמת:

* SabreLDS
* Odyssea

3. מתוך TourGW נבחר מלון אחד מכל ספק.
4. ב־Eshet מאומתת הגעתם של שני המלונות שנבחרו לפי השם.

## מבנה

```text
repo/
  README.md
  requirements.txt
  pytest.ini
  .env
  src/
    config.py
    schedule.py
    mailer.py
    report_builder.py
    pages_tourgateway.py
    pages_eshet.py
    utils.py
  tests/
    conftest.py
    test_closed_packages_batumi.py
  scripts/
    run_local.py
    run_ci.py
  .github/
    workflows/
      hourly.yml
```

## הכנה מקומית

### PowerShell (Windows)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

### Bash (Linux / macOS / Git Bash)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

יש להתקין את Allure CLI בנפרד:

```bash
npm install -g allure-commandline
```

צרו או עדכנו את קובץ ה־`.env`.

המינימום הנדרש להרצה מקומית:

```env
HEADLESS=true
```

## פקודות הפרויקט

כל הפקודות שלהלן מבוצעות מתוך תיקיית השורש של הפרויקט.

### הרצת הבדיקה ישירות דרך pytest

הרצה רגילה:

```powershell
python -m pytest -s -vv tests/test_closed_packages_batumi.py
```

הרצה עם דפדפן גלוי:

```powershell
$env:HEADLESS="false"
python -m pytest -s -vv tests/test_closed_packages_batumi.py
```

בשורה אחת:

```powershell
$env:HEADLESS="false"; python -m pytest -s -vv tests/test_closed_packages_batumi.py
```

שמירה מפורשת של התוצאות עבור Allure:

```powershell
python -m pytest -s -vv --alluredir=allure-results tests/test_closed_packages_batumi.py
```

### הרצה מקומית באמצעות סקריפט מלא

```powershell
python scripts/run_local.py
```

עם דפדפן גלוי:

```powershell
$env:HEADLESS="false"; python scripts/run_local.py
```

הסקריפט:

1. מריץ את `pytest`.
2. מייצר את `allure-report`.
3. שולח מייל HTML, אם משתני ה־SMTP מולאו.
4. למייל מתווספים קישורים וצילומי מסך מוטמעים.

### הרצת CI בהתאם לחלון העבודה

```powershell
python scripts/run_ci.py
```

התנהגות:

* בתוך חלון העבודה מריץ את הבדיקות ושולח מייל.
* מחוץ לחלון:
* כאשר `RUN_OUTSIDE_SCHEDULE=false` התהליך מסתיים עם `exit 0` ללא בדיקות וללא מייל.
* כאשר `RUN_OUTSIDE_SCHEDULE=true` הבדיקות מורצות, אך מייל לא נשלח.

### Allure

יצירת דוח מתוך תוצאות קיימות:

```powershell
allure generate allure-results -o allure-report --clean
```

פתיחת דוח שכבר נוצר:

```powershell
allure open allure-report
```

יצירה ופתיחה מיידית של דוח זמני:

```powershell
allure serve allure-results
```

### פקודות שימושיות

להריץ את כל הבדיקות:

```powershell
python -m pytest
```

להריץ את כל הבדיקות עם דפדפן גלוי:

```powershell
$env:HEADLESS="false"; python -m pytest
```

## משתני סביבה

נדרשים לשליחת מייל:

* `SMTP_HOST`
* `SMTP_PORT`
* `SMTP_USER`
* `SMTP_PASS`
* `MAIL_TO`

אופציונליים:

* `MAIL_CC`
* `SCHEDULE_TZ` (ברירת מחדל: `Asia/Jerusalem`)
* `SCHEDULE_DAYS` (ברירת מחדל: `Sun,Mon,Tue,Wed,Thu,Fri`)
* `SCHEDULE_START` (ברירת מחדל: `08:00`)
* `SCHEDULE_END` (ברירת מחדל: `17:00`)
* `RUN_OUTSIDE_SCHEDULE` (ברירת מחדל: `false`)
* `HEADLESS` (ברירת מחדל: `true`)

## GitHub Actions

Workflow: `.github/workflows/hourly.yml`

Cron:

* בכל שעה, לפי UTC.

סודות ב־GitHub:

* `SMTP_HOST`
* `SMTP_PORT`
* `SMTP_USER`
* `SMTP_PASS`
* `MAIL_TO`
* `MAIL_CC`

GitHub Variables:

* `SCHEDULE_TZ`
* `SCHEDULE_DAYS`
* `SCHEDULE_START`
* `SCHEDULE_END`
* `RUN_OUTSIDE_SCHEDULE`
 
