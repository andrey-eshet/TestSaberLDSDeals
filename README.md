# autoTestEshet

Репозиторий автотеста для мониторинга закрытых пакетов по направлению Батуми.

Стек:
- Python
- Playwright
- pytest
- Allure

Что проверяется:
1. В TourGW находится окно дат, где есть закрытые пакеты от двух поставщиков.
2. Поставщики в источнике истины:
- SabreLDS
- Odyssea
3. Из TourGW выбирается по одному отелю от каждого поставщика.
4. На Эшет подтверждается приход двух выбранных отелей по названию.

## Структура

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

## Подготовка локально

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

Установите Allure CLI отдельно:

```bash
npm install -g allure-commandline
```

Создайте или обновите файл `.env`.

Минимально для локального запуска:

```env
HEADLESS=true
```

## Команды проекта

Все команды ниже выполняются из корня проекта.

### Запуск теста напрямую через pytest

Обычный запуск:

```powershell
python -m pytest -s -vv tests/test_closed_packages_batumi.py
```

Запуск с видимым браузером:

```powershell
$env:HEADLESS="false"
python -m pytest -s -vv tests/test_closed_packages_batumi.py
```

Одной строкой:

```powershell
$env:HEADLESS="false"; python -m pytest -s -vv tests/test_closed_packages_batumi.py
```

Явно записать результаты для Allure:

```powershell
python -m pytest -s -vv --alluredir=allure-results tests/test_closed_packages_batumi.py
```

### Локальный запуск полным скриптом

```powershell
python scripts/run_local.py
```

С видимым браузером:

```powershell
$env:HEADLESS="false"; python scripts/run_local.py
```

Скрипт:
1. Запускает `pytest`.
2. Генерирует `allure-report`.
3. Отправляет HTML письмо, если SMTP переменные заполнены.
4. В письмо добавляются ссылки и inline скриншоты.

### CI запуск с учетом рабочего окна

```powershell
python scripts/run_ci.py
```

Поведение:
- Внутри рабочего окна запускает тесты и отправляет письмо.
- Вне окна:
- при `RUN_OUTSIDE_SCHEDULE=false` завершает работу с `exit 0` без тестов и без письма.
- при `RUN_OUTSIDE_SCHEDULE=true` запускает тесты, но письмо не отправляет.

### Allure

Сгенерировать отчет из существующих результатов:

```powershell
allure generate allure-results -o allure-report --clean
```

Открыть уже сгенерированный отчет:

```powershell
allure open allure-report
```

Сгенерировать и сразу открыть временный отчет:

```powershell
allure serve allure-results
```

### Полезные команды

Запустить все тесты:

```powershell
python -m pytest
```

Запустить все тесты с видимым браузером:

```powershell
$env:HEADLESS="false"; python -m pytest
```

## Переменные окружения

Обязательные для отправки письма:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `MAIL_TO`

Опциональные:
- `MAIL_CC`
- `SCHEDULE_TZ` (по умолчанию `Asia/Jerusalem`)
- `SCHEDULE_DAYS` (по умолчанию `Sun,Mon,Tue,Wed,Thu,Fri`)
- `SCHEDULE_START` (по умолчанию `08:00`)
- `SCHEDULE_END` (по умолчанию `17:00`)
- `RUN_OUTSIDE_SCHEDULE` (по умолчанию `false`)
- `HEADLESS` (по умолчанию `true`)

## GitHub Actions

Workflow: `.github/workflows/hourly.yml`

Cron:
- каждый час, по UTC.

Секреты в GitHub:
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `MAIL_TO`
- `MAIL_CC`

GitHub Variables:
- `SCHEDULE_TZ`
- `SCHEDULE_DAYS`
- `SCHEDULE_START`
- `SCHEDULE_END`
- `RUN_OUTSIDE_SCHEDULE`
