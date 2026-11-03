"""
Быстрая проверка алгоритмов и операций (процедурно, на assert):  python selftest.py
"""

import os
from datetime import datetime

from algorithms import calculate_order_total, estimate_ready_minutes
from operations import (
    register_client,
    validate_order_lines,
    create_order,
    assign_courier,
    update_order_status,
    get_order_status,
)
from config import STATUS_CONFIRMED, STATUS_COOKING, STATUS_ON_THE_WAY, STATUS_DELIVERED
from storage import load_db


def fresh_db():
    here = os.path.dirname(os.path.abspath(__file__))
    return load_db(os.path.join(here, "data", "seed.json"))


def check_algorithm_2():
    # пустая очередь, две станции: [8, 8, 5] -> 8 | 8, затем 5 на первую станцию
    assert estimate_ready_minutes([], [8, 8, 5], 2) == 13
    # одна станция — времена просто складываются
    assert estimate_ready_minutes([], [3, 4, 5], 1) == 12
    # очередь задерживает новый заказ
    assert estimate_ready_minutes([[10]], [1], 1) == 11
    # станций больше, чем порций — готовность равна самой долгой порции
    assert estimate_ready_minutes([], [7, 2], 5) == 7


def check_algorithm_1():
    db = fresh_db()
    # клиент 1 — постоянный (5 доставленных заказов): скидка 5 %
    lines = [{"item_id": 1, "quantity": 3}]
    result = calculate_order_total(db, 1, lines)
    assert result["subtotal"] == 747.0
    assert result["volume_discount"] == 74.7
    assert result["loyalty_discount"] == round((747.0 - 74.7) * 0.05, 2)
    # новый клиент (id 99): только скидка за количество
    result = calculate_order_total(db, 99, lines)
    assert result["loyalty_discount"] == 0.0
    assert result["total"] == round(747.0 - 74.7, 2)
    # меньше трёх штук — скидки за количество нет
    result = calculate_order_total(db, 99, [{"item_id": 1, "quantity": 2}])
    assert result["volume_discount"] == 0.0 and result["total"] == 498.0


def check_operations():
    db = fresh_db()
    now = datetime(2026, 11, 2, 12, 0)

    assert register_client(db, 1, "", "1", now)["ok"] is False
    assert register_client(db, 5005, "Анна", "+7 900 000-00-00", now)["created"] is True

    assert validate_order_lines(db, [{"item_id": 99, "quantity": 1}])["ok"] is False
    assert validate_order_lines(db, [{"item_id": 7, "quantity": 1}])["ok"] is False
    merged = validate_order_lines(db, [{"item_id": 1, "quantity": 1}, {"item_id": 1, "quantity": 2}])
    assert merged["lines"] == [{"item_id": 1, "quantity": 3}]

    assert create_order(db, 123456, [{"item_id": 1, "quantity": 1}], now)["ok"] is False
    created = create_order(db, 5005, [{"item_id": 1, "quantity": 1}], now)
    assert created["ok"] is True
    order_id = created["order"]["order_id"]

    assert update_order_status(db, order_id, STATUS_DELIVERED)["ok"] is False
    assert update_order_status(db, order_id, STATUS_COOKING)["ok"] is False     # сначала «Подтверждён»
    assert update_order_status(db, order_id, STATUS_CONFIRMED)["ok"] is True
    assert update_order_status(db, order_id, STATUS_COOKING)["ok"] is True
    assert update_order_status(db, order_id, STATUS_ON_THE_WAY)["ok"] is False   # курьера нет
    assert assign_courier(db, order_id)["ok"] is True
    assert update_order_status(db, order_id, STATUS_ON_THE_WAY)["ok"] is True
    assert update_order_status(db, order_id, STATUS_DELIVERED)["ok"] is True
    assert all(courier["is_free"] for courier in db["couriers"].values())

    later = datetime(2026, 11, 2, 12, 5)
    status = get_order_status(db, order_id, later)
    assert status["status"] == "Доставлен" and status["remaining_minutes"] == 0


def main():
    check_algorithm_1()
    check_algorithm_2()
    check_operations()
    print("Все проверки пройдены")


if __name__ == "__main__":
    main()
