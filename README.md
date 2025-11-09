# Визуализация графа зависимостей — Этапы 1-4

Минимальное CLI‑приложение для работы с графами зависимостей пакетов NuGet. Поддерживает конфигурирование, получение прямых зависимостей, построение полного графа транзитивных зависимостей с обнаружением циклов, и поиск обратных зависимостей.

## 1. Общее описание

Приложение решает следующие задачи:
- **Этап 1**: Чтение и валидация INI‑конфигурации с выводом параметров.
- **Этап 2**: Получение прямых зависимостей пакета из GitHub‑репозитория (парсинг `.csproj`, `.nuspec`, `packages.config`).
- **Этап 3**: Построение полного графа транзитивных зависимостей с использованием итеративного DFS (без рекурсии), обработка циклов, режим тестового репозитория.
- **Этап 4**: Поиск обратных зависимостей — нахождение всех пакетов, которые зависят от заданного пакета (прямо или транзитивно).

Ограничения: использование готовых менеджеров пакетов и библиотек для получения зависимостей запрещено.

## 2. Описание функций и настроек

### Параметры конфигурации (INI, секция `[app]`)

- `package_name` — имя анализируемого пакета. Допустимые символы: латинские буквы, цифры, `.`, `_`, `-`. Должно начинаться с буквы/цифры. Длина: 1..128.
- `repo_source` — источник репозитория:
  - если `test_repo_mode=local-path`, это путь к файлу тестового репозитория (см. формат ниже);
  - если `test_repo_mode=remote-url`, это валидный URL GitHub репозитория (схемы `http`, `https`, `git`).
- `test_repo_mode` — режим работы с репозиторием: одно из `local-path`, `remote-url`.
- `output_mode` — режим вывода: одно из `ascii-tree`, `list` (на Этапах 1-3 влияет только на валидацию).

Примеры конфигураций: см. `configs/config.example.ini`, `configs/test_simple.ini` и др.

### Формат тестового репозитория

Для режима `test_repo_mode=local-path` используется простой текстовый формат:
```
A: B C
B: D
C:
D:
```
Каждая строка: `ПАКЕТ: ЗАВ1 ЗАВ2 ...`. Имена пакетов — заглавные латинские буквы. Версии не указываются (подразумевается `*`).

### Режимы работы (`--action`)

- `print-config` — Этап 1: вывести параметры конфигурации (по умолчанию).
- `show-deps` — Этап 2: загрузить репозиторий (GitHub), извлечь и вывести прямые зависимости.
- `build-graph` — Этап 3: построить полный граф транзитивных зависимостей через итеративный DFS, вывести статистику (узлы, рёбра, циклы).
- `reverse-deps` — Этап 4: найти все пакеты, которые зависят от `--target` пакета (прямо или транзитивно). Требует указать `--target`.

### Дополнительные параметры

- `--target` — имя пакета для поиска обратных зависимостей (используется с `--action=reverse-deps`).

### Обработка ошибок

- Отсутствие файла конфигурации.
- Отсутствие секции `[app]` или обязательных ключей.
- Недопустимые значения параметров (несоответствие формату имени, несуществующий путь, неверный URL, недопустимый режим и т. п.).
- Сообщения агрегируются — выводится сразу список всех проблемных полей.

## 3. Команды для сборки проекта и запуска тестов

Сборка проекта не требуется (это обычный Python‑скрипт). Запуск осуществляется напрямую интерпретатором.

### Запуск приложения (PowerShell)

```powershell
# Использовать конфиг по умолчанию ./configs/config.ini
python .\main.py

# Использовать конкретный файл конфигурации
python .\main.py --config .\configs\config.example.ini

# Этап 2: вывод прямых зависимостей (используется URL репозитория)
# Ограничение прототипа: поддерживается только GitHub URL вида https://github.com/<owner>/<repo>
python .\main.py --config .\configs\config.files.ini --action show-deps

# Этап 3: построение полного графа зависимостей
# Для тестового репозитория (local-path):
python .\main.py --config .\configs\test_simple.ini --action build-graph
python .\main.py --config .\configs\test_cycle.ini --action build-graph
python .\main.py --config .\configs\test_diamond.ini --action build-graph

# Для реального GitHub репозитория (remote-url):
python .\main.py --config .\configs\config.files.ini --action build-graph

# Этап 4: поиск обратных зависимостей (кто зависит от целевого пакета)
python .\main.py --config .\configs\test_simple.ini --action reverse-deps --target C
python .\main.py --config .\configs\test_diamond.ini --action reverse-deps --target D
python .\main.py --config .\configs\test_complex.ini --action reverse-deps --target F
```

### Запуск тестов

```powershell
# Явный поиск тестов в каталоге tests
python -m unittest discover -s tests -p "test_*.py" -v
```

## 4. Примеры использования

### Этап 1 — печать параметров

Успешный запуск с примером конфига:

```powershell
python .\main.py --config .\configs\config.example.ini
```

Пример вывода:

```
package_name=sample-package
repo_source=C:\\MyFiles\\python-projects\\EDU\\cli-graph-visualization-practice
test_repo_mode=local-path
output_mode=ascii-tree
```

Демонстрация ошибок валидации (намеренно неверный конфиг `configs/config.invalid.ini`):

```powershell
python .\main.py --config .\configs\config.invalid.ini
```

Возможный вывод ошибок:

```
Configuration validation failed:
 - package_name is invalid. Allowed: letters, numbers, '.', '_', '-'; must start with alnum; length 1..128.
 - test_repo_mode must be one of ['local-path', 'remote-url']; got 'remote'
 - output_mode must be one of ['ascii-tree', 'list']; got 'ascii'
 - repo_source is not a valid URL (test_repo_mode=remote-url): example
```

### Этап 2 — вывод прямых зависимостей

Пример вывода прямых зависимостей реального репозитория Files:

```powershell
python .\main.py --config .\configs\config.files.ini --action show-deps
```

Вывод (по одной зависимости в строке):

```
ByteSize *
ColorCode.WinUI *
CommunityToolkit.Labs.WinUI.Controls.MarkdownTextBlock *
...
Microsoft.Windows.CsWinRT *
```

### Этап 3 — построение графа зависимостей

#### Простая линейная цепочка (A → B → C)

```powershell
python .\main.py --config .\configs\test_simple.ini --action build-graph
```

Вывод:
```
Nodes: 3
Edges: 2
No cycles detected
```

#### Обнаружение циклов (D → A → B → C → A)

```powershell
python .\main.py --config .\configs\test_cycle.ini --action build-graph
```

Вывод:
```
Nodes: 4
Edges: 4
Cycles detected: 1
  Cycle: A -> B -> C -> A
```

#### Ромбовидная структура (A зависит от B и C, оба зависят от D)

```powershell
python .\main.py --config .\configs\test_diamond.ini --action build-graph
```

Вывод:
```
Nodes: 4
Edges: 4
No cycles detected
```

#### Сложный многоуровневый граф

```powershell
python .\main.py --config .\configs\test_complex.ini --action build-graph
```

Вывод:
```
Nodes: 6
Edges: 6
No cycles detected
```

### Этап 4 — обратные зависимости

Обратные зависимости — это пакеты, которые зависят от заданного (прямо или транзитивно).

#### Простая цепочка: кто зависит от C

```powershell
python .\main.py --config .\configs\test_simple.ini --action reverse-deps --target C
```

Вывод:
```
Packages that depend on 'C':
  A
  B
```

Объяснение: A зависит от B, B зависит от C, поэтому оба A и B зависят от C (A транзитивно).

#### Ромб: кто зависит от D

```powershell
python .\main.py --config .\configs\test_diamond.ini --action reverse-deps --target D
```

Вывод:
```
Packages that depend on 'D':
  A
  B
  C
```

Объяснение: A зависит от B и C, оба зависят от D, поэтому все три пакета зависят от D.

#### Цикл: кто зависит от A

```powershell
python .\main.py --config .\configs\test_cycle.ini --action reverse-deps --target A
```

Вывод:
```
Packages that depend on 'A':
  B
  C
  D
```

Объяснение: В цикле A→B→C→A все узлы зависят друг от друга транзитивно. D зависит от A напрямую, поэтому также входит в цикл.

#### Сложный граф: кто зависит от F

```powershell
python .\main.py --config .\configs\test_complex.ini --action reverse-deps --target F
```

Вывод:
```
Packages that depend on 'F':
  A
  B
  C
  E
```

Объяснение: E→F напрямую, B→E и C→E, A→B и A→C, поэтому все зависят от F транзитивно.

#### Сложный граф: кто зависит от D

```powershell
python .\main.py --config .\configs\test_complex.ini --action reverse-deps --target D
```

Вывод:
```
Packages that depend on 'D':
  A
  B
```

Объяснение: B→D напрямую, A→B, поэтому только A и B зависят от D. C не зависит от D.

## Примечания

- **Этап 1**: Только чтение и валидация конфигурации.
- **Этап 2**: Добавлена загрузка репозитория по URL (ограничение: GitHub), поиск `.nuspec`/`.csproj` и извлечение прямых зависимостей. Менеджеры пакетов и сторонние библиотеки не используются.
- **Этап 3**: Реализовано построение полного графа транзитивных зависимостей с использованием **итеративного DFS (без рекурсии)**. Обрабатываются циклические зависимости. Поддерживается режим тестирования с локальными файлами (`test_repo_mode=local-path`).
- **Этап 4**: Добавлен поиск **обратных зависимостей** (reverse dependencies) — нахождение всех пакетов, которые зависят от заданного пакета (прямо или транзитивно). Использует итеративный обход графа для каждого узла.
- Следующие этапы: визуализация зависимостей (например, ASCII‑дерево) и расширение поддерживаемых источников.

## Структура проекта

```
.
├── configs/               # Конфигурационные файлы
│   ├── config.example.ini
│   ├── config.files.ini
│   ├── test_simple.ini
│   ├── test_cycle.ini
│   ├── test_diamond.ini
│   └── test_complex.ini
├── fixtures/              # Тестовые репозитории
│   ├── test_repo_simple.txt
│   ├── test_repo_cycle.txt
│   ├── test_repo_diamond.txt
│   └── test_repo_complex.txt
├── tests/                 # Юнит-тесты
│   ├── test_nuget_parser.py
│   └── test_dependency_graph.py
├── main.py                # Основной CLI-модуль
├── dependency_graph.py    # Построение графа через итеративный DFS
├── nuget_parser.py        # Парсинг .csproj/.nuspec/packages.config
├── repo_fetch.py          # Загрузка GitHub репозиториев
├── test_repo.py           # Работа с тестовыми репозиториями
└── README.md              # Документация
```
