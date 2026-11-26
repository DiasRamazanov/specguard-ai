# SpecGuard AI

SpecGuard проверяет требования до разработки. Для каждого замечания он сохраняет цитату или область поиска пропуска. Отчёт содержит реестр требований, индивидуальные и общие проверки, сводку и вывод о готовности.

## Установка

Проверенная среда — Python 3.12 на macOS arm64. Разбор PDF поддерживается на macOS и Linux.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
```

## Запуск проверки

Локальная проверка Markdown, TXT или PDF выполняется без ключа. Семантическое покрытие в таком отчёте помечено как неполное.

```bash
python -m specguard validate --offline --input benchmarks/fixtures/placeholder.md --output report.md --json-output report.json
```

Для живого анализа получите API-ключ в [DeepSeek Platform](https://platform.deepseek.com/api_keys) и передайте его серверному процессу через переменную окружения `DEEPSEEK_API_KEY`. Образец переменных находится в `.env.example`. При разрешении на внешний анализ установите `SPECGUARD_LIVE=1` и передайте явное согласие на отправку текста. Платные запросы расходуют квоту владельца ключа.

```bash
python -m specguard validate --consent --input requirements.md --output report.md
```

Родительская папка выходного файла должна существовать. `--input` можно указать несколько раз. Код выхода 0 означает завершённый запуск выбранного режима, в том числе с найденными дефектами. Код 2 означает ошибку конфигурации или ввода. Код 3 означает, что записан неполный результат живой проверки. Имена моделей по умолчанию — `deepseek-flash` и `deepseek-v4-pro`. Провайдер проверяет доступ к модели перед отправкой текста. Параметры бюджета — `SPECGUARD_RUN_TOKENS`, `SPECGUARD_GLOBAL_TOKENS`, `SPECGUARD_RUN_CALLS`, `SPECGUARD_CONCURRENCY`, `SPECGUARD_RETRIES` и `SPECGUARD_TIMEOUT_SECONDS`. Общий журнал нескольких процессов настраивается через `SPECGUARD_BUDGET_DB`.

## HTTP API и тесты

```bash
python -m uvicorn specguard.api:app --host 127.0.0.1 --port 8000 --workers 1 --limit-concurrency 16
python -m pytest -q
python -m benchmarks.evaluate --output /tmp/specguard-evaluation.json
python -m scripts.export_contracts
```

Схема OpenAPI находится в [contracts/openapi.json](contracts/openapi.json). Интерактивная документация запущенного сервера доступна по пути `/docs`. Для подключения фронтенда используйте запросы к тому же origin через dev-прокси. [Архитектура](docs/architecture.md) · [Передача проекта](docs/handoffs/codex.md) · [Методика оценки](benchmarks/README.md)
