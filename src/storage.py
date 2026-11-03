"""
Хранение данных в JSON-файле. Структура файла повторяет логическую модель данных:
каждая таблица — это сущность из ER-диаграммы, каждая запись — словарь с теми же
атрибутами. Таблицы с первичным ключом из одного поля хранятся как словари
«идентификатор -> запись», таблица order_lines (составной ключ) — как список.
"""

import json

KEYED_TABLES = (
    "clients",
    "menu_categories",
    "menu_items",
    "order_statuses",
    "couriers",
    "orders",
)


def load_db(path):
    """Читает JSON и приводит ключи таблиц к целым числам."""
    with open(path, encoding="utf-8") as source:
        raw = json.load(source)
    db = {}
    for table in KEYED_TABLES:
        db[table] = {int(key): row for key, row in raw[table].items()}
    db["order_lines"] = list(raw["order_lines"])
    return db


def save_db(db, path):
    """Записывает базу в JSON (для проверки результата работы сценария)."""
    raw = {}
    for table in KEYED_TABLES:
        raw[table] = {str(key): row for key, row in db[table].items()}
    raw["order_lines"] = db["order_lines"]
    with open(path, "w", encoding="utf-8") as target:
        json.dump(raw, target, ensure_ascii=False, indent=2)
