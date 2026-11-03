"""
Алгоритмы процедурной версии (КТ2). Только функции и стандартные структуры данных.

Алгоритм 1 — calculate_order_total: расчёт стоимости заказа со скидками.
Алгоритм 2 — estimate_ready_minutes: оценка времени готовности заказа
             с учётом очереди на кухне (жадное распределение по станциям).
"""

from config import (
    STATUS_DELIVERED,
    VOLUME_MIN_QUANTITY,
    VOLUME_DISCOUNT,
    LOYALTY_MIN_ORDERS,
    LOYALTY_DISCOUNT,
)


def calculate_order_total(db, client_id, lines):
    """
    Алгоритм 1. Рассчитывает стоимость заказа.

    lines — уже проверенные строки заказа: [{"item_id": 1, "quantity": 2}, ...].
    Скидка за количество: если позиции взято от VOLUME_MIN_QUANTITY штук,
    на сумму этой позиции действует скидка VOLUME_DISCOUNT.
    Скидка постоянного клиента: если у клиента от LOYALTY_MIN_ORDERS доставленных
    заказов, на итог действует скидка LOYALTY_DISCOUNT.

    Сложность по времени: O(n + p), n — число строк заказа, p — число заказов в системе.
    """
    subtotal = 0.0
    volume_discount = 0.0
    for line in lines:
        item = db["menu_items"][line["item_id"]]
        line_sum = item["price"] * line["quantity"]
        if line["quantity"] >= VOLUME_MIN_QUANTITY:
            volume_discount += line_sum * VOLUME_DISCOUNT
        subtotal += line_sum

    delivered = 0
    for order in db["orders"].values():
        if (order["client_id"] == client_id
                and order["status_id"] == STATUS_DELIVERED):
            delivered += 1

    total = subtotal - volume_discount
    loyalty_discount = 0.0
    if delivered >= LOYALTY_MIN_ORDERS:
        loyalty_discount = total * LOYALTY_DISCOUNT
    total = total - loyalty_discount

    return {
        "subtotal": round(subtotal, 2),
        "volume_discount": round(volume_discount, 2),
        "loyalty_discount": round(loyalty_discount, 2),
        "total": round(total, 2),
    }


def estimate_ready_minutes(queue, new_units, stations):
    """
    Алгоритм 2. Оценивает, через сколько минут будет готов новый заказ.

    queue     — очередь заказов на кухне; каждый заказ — список времён приготовления
                отдельных порций (в минутах), порядок списка = порядок поступления;
    new_units — такой же список для нового заказа;
    stations  — число станций кухни, работающих параллельно.

    Заказы обрабатываются по очереди; внутри заказа самые долгие порции ставятся
    первыми на наименее загруженную станцию (жадная стратегия LPT).
    Возвращает момент готовности последней порции нового заказа.

    Сложность по времени: O(U log U + U * m), U — число порций в очереди и в новом заказе,
    m — число станций.
    """
    loads = [0] * stations
    ready = 0
    for unit_times in queue + [new_units]:
        times = sorted(unit_times, reverse=True)
        ready = 0
        for t in times:
            best = 0
            for s in range(1, stations):
                if loads[s] < loads[best]:
                    best = s
            loads[best] += t
            if loads[best] > ready:
                ready = loads[best]
    return ready
