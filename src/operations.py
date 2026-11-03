"""
Автоматизируемые операции процесса «Приём и обработка заказа через Telegram-бота».

Названия функций соответствуют таблице операций в отчёте. Все функции принимают
базу данных db (обычный dict, структура которого повторяет логическую модель данных)
первым параметром и возвращают результат в виде словаря {"ok": True/False, ...}.
Классов и глобальных изменяемых переменных нет.
"""

from datetime import datetime

from algorithms import calculate_order_total, estimate_ready_minutes
from config import (
    STATUS_NEW,
    STATUS_COOKING,
    STATUS_ON_THE_WAY,
    STATUS_DELIVERED,
    STATUS_CANCELLED,
    STATUS_TRANSITIONS,
    ACTIVE_KITCHEN_STATUSES,
    KITCHEN_STATIONS,
    DELIVERY_MINUTES,
    MAX_QUANTITY_PER_LINE,
    DATETIME_FORMAT,
)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def parse_dt(text):
    """Строка 'ГГГГ-ММ-ДД ЧЧ:ММ' -> datetime."""
    return datetime.strptime(text, DATETIME_FORMAT)


def format_dt(moment):
    """datetime -> строка 'ГГГГ-ММ-ДД ЧЧ:ММ'."""
    return moment.strftime(DATETIME_FORMAT)


def next_id(table):
    """Следующий свободный числовой идентификатор для таблицы-словаря."""
    if not table:
        return 1
    return max(table) + 1


def find_client_by_telegram_id(db, telegram_id):
    """Линейный поиск клиента по telegram_id; None, если клиента нет."""
    for client in db["clients"].values():
        if client["telegram_id"] == telegram_id:
            return client
    return None


def status_title(db, status_id):
    return db["order_statuses"][status_id]["title"]


# ---------------------------------------------------------------------------
# Операция «Зарегистрировать клиента»
# ---------------------------------------------------------------------------

def register_client(db, telegram_id, name, phone, now):
    """Проверяет имя и телефон, создаёт клиента или обновляет данные существующего."""
    name = name.strip()
    digits = "".join(ch for ch in phone if ch.isdigit())
    errors = []
    if not name:
        errors.append("имя не может быть пустым")
    if len(name) > 50:
        errors.append("имя длиннее 50 символов")
    if not 10 <= len(digits) <= 15:
        errors.append("в телефоне должно быть от 10 до 15 цифр")
    if errors:
        return {"ok": False, "errors": errors}

    client = find_client_by_telegram_id(db, telegram_id)
    if client is not None:
        client["name"] = name
        client["phone"] = phone.strip()
        return {"ok": True, "created": False, "client": client}

    client_id = next_id(db["clients"])
    client = {
        "client_id": client_id,
        "telegram_id": telegram_id,
        "name": name,
        "phone": phone.strip(),
        "registered_at": format_dt(now),
    }
    db["clients"][client_id] = client
    return {"ok": True, "created": True, "client": client}


# ---------------------------------------------------------------------------
# Операция «Проверить состав заказа»
# ---------------------------------------------------------------------------

def validate_order_lines(db, raw_lines):
    """
    Проверяет строки заказа: позиция есть в меню и доступна, количество — целое
    число от 1 до MAX_QUANTITY_PER_LINE. Одинаковые позиции объединяются.
    """
    errors = []
    merged = {}
    for raw in raw_lines:
        item_id = raw.get("item_id")
        quantity = raw.get("quantity")
        item = db["menu_items"].get(item_id)
        if item is None:
            errors.append(f"позиции №{item_id} нет в меню")
            continue
        if not item["is_available"]:
            errors.append(f"позиция «{item['name']}» сейчас недоступна")
            continue
        if not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY_PER_LINE:
            errors.append(
                f"количество «{item['name']}» должно быть целым от 1 до {MAX_QUANTITY_PER_LINE}"
            )
            continue
        merged[item_id] = merged.get(item_id, 0) + quantity

    if not merged and not errors:
        errors.append("заказ пуст")
    if errors:
        return {"ok": False, "errors": errors}

    lines = [{"item_id": item_id, "quantity": q} for item_id, q in merged.items()]
    return {"ok": True, "lines": lines}


# ---------------------------------------------------------------------------
# Операции «Рассчитать стоимость заказа» и «Рассчитать время доставки»
# ---------------------------------------------------------------------------

def units_for_lines(db, lines):
    """Список времён приготовления отдельных порций: позиция × количество."""
    units = []
    for line in lines:
        cooking = db["menu_items"][line["item_id"]]["cooking_minutes"]
        units.extend([cooking] * line["quantity"])
    return units


def build_kitchen_queue(db):
    """Очередь кухни: порции всех заказов в активных статусах (в порядке поступления)."""
    lines_by_order = {}
    for line in db["order_lines"]:
        lines_by_order.setdefault(line["order_id"], []).append(line)
    queue = []
    for order_id, order in db["orders"].items():
        if order["status_id"] in ACTIVE_KITCHEN_STATUSES:
            queue.append(units_for_lines(db, lines_by_order.get(order_id, [])))
    return queue


def estimate_delivery_minutes(db, lines):
    """Время доставки = готовность с учётом очереди на кухне + время в пути курьера."""
    queue = build_kitchen_queue(db)
    new_units = units_for_lines(db, lines)
    ready = estimate_ready_minutes(queue, new_units, KITCHEN_STATIONS)
    return ready + DELIVERY_MINUTES


# ---------------------------------------------------------------------------
# Операция «Оформить заказ»
# ---------------------------------------------------------------------------

def create_order(db, telegram_id, raw_lines, now):
    """
    Оформляет заказ: проверяет регистрацию и состав, считает стоимость и время,
    присваивает номер и статус «Новый», сохраняет заказ и его строки.
    """
    client = find_client_by_telegram_id(db, telegram_id)
    if client is None:
        return {"ok": False, "errors": ["клиент не зарегистрирован — сначала нужна регистрация"]}

    checked = validate_order_lines(db, raw_lines)
    if not checked["ok"]:
        return checked

    lines = checked["lines"]
    totals = calculate_order_total(db, client["client_id"], lines)
    minutes = estimate_delivery_minutes(db, lines)

    order_id = next_id(db["orders"])
    order = {
        "order_id": order_id,
        "client_id": client["client_id"],
        "status_id": STATUS_NEW,
        "courier_id": None,
        "created_at": format_dt(now),
        "total_price": totals["total"],
        "estimated_minutes": minutes,
    }
    db["orders"][order_id] = order
    for line in lines:
        db["order_lines"].append({
            "order_id": order_id,
            "item_id": line["item_id"],
            "quantity": line["quantity"],
            "unit_price": db["menu_items"][line["item_id"]]["price"],
        })
    return {"ok": True, "order": order, "totals": totals, "lines": lines}


# ---------------------------------------------------------------------------
# Операция «Назначить курьера»
# ---------------------------------------------------------------------------

def assign_courier(db, order_id):
    """Назначает заказу первого свободного курьера (заказ должен быть в статусе «Готовится»)."""
    order = db["orders"].get(order_id)
    if order is None:
        return {"ok": False, "errors": [f"заказа №{order_id} нет"]}
    if order["status_id"] != STATUS_COOKING:
        return {"ok": False, "errors": ["курьера назначают заказу в статусе «Готовится»"]}
    if order["courier_id"] is not None:
        return {"ok": False, "errors": ["курьер уже назначен"]}
    for courier in db["couriers"].values():
        if courier["is_free"]:
            courier["is_free"] = False
            order["courier_id"] = courier["courier_id"]
            return {"ok": True, "courier": courier}
    return {"ok": False, "errors": ["нет свободных курьеров"]}


# ---------------------------------------------------------------------------
# Операция «Обновить статус заказа»
# ---------------------------------------------------------------------------

def update_order_status(db, order_id, new_status_id):
    """Меняет статус, если переход допустим; при завершении заказа освобождает курьера."""
    order = db["orders"].get(order_id)
    if order is None:
        return {"ok": False, "errors": [f"заказа №{order_id} нет"]}
    old_status_id = order["status_id"]
    if (old_status_id, new_status_id) not in STATUS_TRANSITIONS:
        return {
            "ok": False,
            "errors": [
                f"переход «{status_title(db, old_status_id)}» → "
                f"«{status_title(db, new_status_id)}» недопустим"
            ],
        }
    if new_status_id == STATUS_ON_THE_WAY and order["courier_id"] is None:
        return {"ok": False, "errors": ["нельзя передать заказ курьеру: курьер не назначен"]}

    order["status_id"] = new_status_id
    if new_status_id in (STATUS_DELIVERED, STATUS_CANCELLED) and order["courier_id"] is not None:
        db["couriers"][order["courier_id"]]["is_free"] = True
    return {"ok": True, "order": order, "old_status_id": old_status_id}


# ---------------------------------------------------------------------------
# Операция «Сообщить статус заказа клиенту»
# ---------------------------------------------------------------------------

def get_order_status(db, order_id, now):
    """Возвращает статус заказа и оставшееся до доставки время (не меньше нуля)."""
    order = db["orders"].get(order_id)
    if order is None:
        return {"ok": False, "errors": [f"заказа №{order_id} нет"]}
    elapsed = int((now - parse_dt(order["created_at"])).total_seconds() // 60)
    remaining = max(order["estimated_minutes"] - elapsed, 0)
    if order["status_id"] in (STATUS_DELIVERED, STATUS_CANCELLED):
        remaining = 0
    return {
        "ok": True,
        "order_id": order_id,
        "status": status_title(db, order["status_id"]),
        "remaining_minutes": remaining,
        "total_price": order["total_price"],
    }
