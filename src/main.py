"""
Консольная процедурная версия системы приёма и обработки заказов (КТ2).

Запуск:  python main.py
         python main.py --data data/seed.json --scenario data/scenario.json --save result.json

Программа читает начальные данные (data/seed.json), выполняет шаги сценария
(data/scenario.json) и печатает результат каждого шага.
"""

import argparse
import json
import os

from config import (
    STATUS_NEW,
    STATUS_CONFIRMED,
    STATUS_COOKING,
    STATUS_ON_THE_WAY,
    STATUS_DELIVERED,
    STATUS_CANCELLED,
)
from operations import (
    parse_dt,
    register_client,
    create_order,
    assign_courier,
    update_order_status,
    get_order_status,
    status_title,
)
from storage import load_db, save_db

STATUS_CODES = (
    ("NEW", STATUS_NEW),
    ("CONFIRMED", STATUS_CONFIRMED),
    ("COOKING", STATUS_COOKING),
    ("ON_THE_WAY", STATUS_ON_THE_WAY),
    ("DELIVERED", STATUS_DELIVERED),
    ("CANCELLED", STATUS_CANCELLED),
)


def status_id_by_code(code):
    """Код статуса из сценария ('COOKING') -> идентификатор статуса."""
    for known_code, status_id in STATUS_CODES:
        if known_code == code:
            return status_id
    return None


def print_errors(result):
    for message in result["errors"]:
        print(f"  ОШИБКА: {message}")


def run_register(db, step, now):
    print(f"Зарегистрировать клиента (telegram_id={step['telegram_id']})")
    result = register_client(db, step["telegram_id"], step["name"], step["phone"], now)
    if not result["ok"]:
        print_errors(result)
        return
    client = result["client"]
    action = "создан" if result["created"] else "обновлён"
    print(f"  OK: клиент №{client['client_id']} «{client['name']}» {action}")


def run_create_order(db, step, now):
    print(f"Оформить заказ (telegram_id={step['telegram_id']})")
    result = create_order(db, step["telegram_id"], step["lines"], now)
    if not result["ok"]:
        print_errors(result)
        return
    order = result["order"]
    totals = result["totals"]
    print(f"  OK: заказ №{order['order_id']}, статус «{status_title(db, order['status_id'])}»")
    print(
        f"  Сумма: {totals['subtotal']:.2f} − скидка за количество {totals['volume_discount']:.2f}"
        f" − скидка постоянного клиента {totals['loyalty_discount']:.2f} = {totals['total']:.2f} ₽"
    )
    print(f"  Ориентировочное время доставки: {order['estimated_minutes']} мин.")


def run_assign_courier(db, step):
    print(f"Назначить курьера (заказ №{step['order_id']})")
    result = assign_courier(db, step["order_id"])
    if not result["ok"]:
        print_errors(result)
        return
    print(f"  OK: курьер «{result['courier']['name']}»")


def run_update_status(db, step):
    code = step["status"]
    print(f"Обновить статус заказа №{step['order_id']} -> {code}")
    result = update_order_status(db, step["order_id"], status_id_by_code(code))
    if not result["ok"]:
        print_errors(result)
        return
    print(f"  OK: «{status_title(db, result['old_status_id'])}» → «{status_title(db, result['order']['status_id'])}»")


def run_get_status(db, step, now):
    print(f"Сообщить статус заказа клиенту (заказ №{step['order_id']}, {step['at']})")
    result = get_order_status(db, step["order_id"], now)
    if not result["ok"]:
        print_errors(result)
        return
    print(f"  Статус: «{result['status']}», осталось примерно {result['remaining_minutes']} мин., сумма {result['total_price']:.2f} ₽")


def print_summary(db):
    print("Итоговое состояние заказов:")
    for order_id, order in db["orders"].items():
        client = db["clients"][order["client_id"]]
        print(
            f"  №{order_id}: {client['name']}, «{status_title(db, order['status_id'])}», "
            f"{order['total_price']:.2f} ₽, курьер: {order['courier_id'] or '—'}"
        )


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Процедурная версия: приём и обработка заказа")
    parser.add_argument("--data", default=os.path.join(here, "data", "seed.json"))
    parser.add_argument("--scenario", default=os.path.join(here, "data", "scenario.json"))
    parser.add_argument("--save", default=None, help="куда сохранить итоговое состояние базы (JSON)")
    args = parser.parse_args()

    db = load_db(args.data)
    with open(args.scenario, encoding="utf-8") as source:
        steps = json.load(source)

    for number, step in enumerate(steps, start=1):
        print(f"[{number}] ", end="")
        now = parse_dt(step["at"])
        op = step["op"]
        if op == "register_client":
            run_register(db, step, now)
        elif op == "create_order":
            run_create_order(db, step, now)
        elif op == "assign_courier":
            run_assign_courier(db, step)
        elif op == "update_status":
            run_update_status(db, step)
        elif op == "get_status":
            run_get_status(db, step, now)
        else:
            print(f"неизвестная операция «{op}»")
        print()

    print_summary(db)
    if args.save:
        save_db(db, args.save)
        print(f"База сохранена: {args.save}")


if __name__ == "__main__":
    main()
