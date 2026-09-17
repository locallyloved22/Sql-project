# Delivery manifest

## Главные точки входа

- `START_TEXT2SQL.command` — запуск обычного desktop-окна двойным кликом на macOS.
- `start_desktop.sh` — desktop-запуск из Terminal или VS Code.
- `START_IN_BROWSER.command` / `start_app.sh` — дополнительный браузерный вариант.
- `Text2SQL.code-workspace` и `.vscode/` — готовые кнопки запуска VS Code.
- `prepare_for_vscode.sh` — автоматическая подготовка Docker и баз перед запуском.
- `solution/web_app.py` — русскоязычный браузерный интерфейс.
- `run.sh` / `solution/app.py` — CLI.
- `solution/evaluate.py` — public evaluation и FinalScore.
- `solution/create_submission.py` — CSV submission.
- `setup.sh` — воспроизводимая подготовка окружения и пяти PostgreSQL-баз.

## Документация

- `КАК_ИСПОЛЬЗОВАТЬ.md` — инструкция для пользователя.
- `FINAL_REPORT.md` — краткий отчёт для сдачи.
- `solution/README.md` — техническая документация.
- `REPOSITORY_AUDIT.md` — аудит исходного задания и утечек.

## Проверено перед упаковкой

- 5 PostgreSQL 16 контейнеров healthy;
- 100 таблиц и 566 671 строк;
- 18/18 unit tests;
- 15/15 execution smoke tests;
- браузерный сценарий «пример → запрос → ответ → таблица»;
- evaluator smoke: полный знаменатель EX, VSR и FinalScore.

Архив не содержит `.venv`, API-ключей, `solution/.env`, cache-файлов и скомпрометированного private split.
