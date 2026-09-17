# Запуск Text2SQL в VS Code

## Вариант 1 — самая простая кнопка

1. Откройте VS Code.
2. В верхнем меню выберите **File → Open Workspace from File…**.
3. Выберите:

   `/Users/pmapmapm/Documents/large larping machine/Text2SQL/Text2SQL.code-workspace`

4. Выберите **Terminal → Run Task…**.
5. Нажмите **Text2SQL: открыть обычное окно**.

После подготовки Docker откроется отдельное окно Text2SQL. Браузер не нужен.

## Вариант 2 — горячая клавиша

После открытия workspace нажмите `Cmd+Shift+B`.

## Вариант 3 — Run and Debug

1. Слева нажмите значок **Run and Debug**: треугольник с жуком.
2. Сверху выберите **Text2SQL: открыть окно**.
3. Нажмите зелёный треугольник ▶.

## Если открыта родительская папка LARGE LARPING MACHINE

Задачи проекта могут быть не видны, потому что `.vscode` находится внутри `Text2SQL`. Откройте именно `Text2SQL.code-workspace`, как описано выше.

## Ручная команда во встроенном Terminal

```bash
cd "/Users/pmapmapm/Documents/large larping machine/Text2SQL"
./start_desktop.sh
```
