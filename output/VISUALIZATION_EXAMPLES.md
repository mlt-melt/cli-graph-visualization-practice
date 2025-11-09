# Примеры визуализации зависимостей

## Пример 1: Простая линейная цепочка

**Граф:** A → B → C

**Конфигурация:** `configs/test_simple.ini`

**ASCII-дерево:**
```
└── A
    └── B
        └── C
```

**D2-диаграмма:** `output/example1_simple.d2`
```
# Dependency Graph
direction: down

A -> B
B -> C
```

---

## Пример 2: Граф с циклом

**Граф:** D → A → B → C → A (цикл)

**Конфигурация:** `configs/test_cycle.ini`

**ASCII-дерево:**
```
└── D
    └── A
        └── B
            └── C
                └── A [CIRCULAR]
```

**D2-диаграмма:** `output/example2_cycle.d2`
```
# Dependency Graph
direction: down

A -> B
B -> C
C -> A
D -> A

# Cycles detected:
# Cycle 1: A -> B -> C -> A
A -> B: {style.stroke: red; style.stroke-width: 3}
B -> C: {style.stroke: red; style.stroke-width: 3}
C -> A: {style.stroke: red; style.stroke-width: 3}
```

**Описание:** Цикл обнаружен и выделен красными стрелками в D2-диаграмме. В ASCII-дереве циклические ссылки помечены как `[CIRCULAR]`.

---

## Пример 3: Сложный многоуровневый граф

**Граф:**
- A зависит от B и C
- B зависит от D и E
- C зависит от E
- E зависит от F

**Конфигурация:** `configs/test_complex.ini`

**ASCII-дерево:**
```
└── A
    ├── B
    │   ├── D
    │   └── E
    │       └── F
    └── C
        └── E
            └── F
```

**D2-диаграмма:** `output/example3_complex.d2`
```
# Dependency Graph
direction: down

A -> B
A -> C
B -> D
B -> E
C -> E
E -> F
```

**Описание:** Пакет E является общей зависимостью для B и C (diamond pattern). В ASCII-дереве E и F отображаются дважды под разными ветками для наглядности иерархии.

---

## Как визуализировать свой граф

### ASCII-дерево
```powershell
python .\main.py --config <путь_к_конфигу> --action ascii-tree
```

### D2-диаграмма
```powershell
# Генерация D2-файла
python .\main.py --config <путь_к_конфигу> --action visualize --output my_graph.d2

# Если установлен d2 CLI (https://d2lang.com/), автоматически создастся PNG
```

### Установка D2 для рендеринга
```powershell
# Windows (через Chocolatey)
choco install d2

# Или скачайте с https://github.com/terrastruct/d2/releases
```
