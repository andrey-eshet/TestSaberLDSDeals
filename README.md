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
  .env.example
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

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

Установите Allure CLI отдельно:

```bash
npm install -g allure-commandline
```

Создайте файл окружения:

```bash
cp .env.example .env
```

## Локальный запуск

```bash
python scripts/run_local.py
```

Скрипт:
1. Запускает `pytest`.
2. Генерирует `allure-report`.
3. Создает `artifacts/allure-report.zip`.
4. Отправляет HTML письмо, если SMTP переменные заполнены.
5. В письмо добавляются ссылки и inline скриншоты.
6. ZIP отчеты в письмо не отправляются.

## CI запуск с учетом рабочего окна

```bash
python scripts/run_ci.py
```

Поведение:
- Внутри рабочего окна запускает тесты и отправляет письмо.
- Вне окна:
- при `RUN_OUTSIDE_SCHEDULE=false` завершает работу с `exit 0` без тестов и без письма.
- при `RUN_OUTSIDE_SCHEDULE=true` запускает тесты, но письмо не отправляет.

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
