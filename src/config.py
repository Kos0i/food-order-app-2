"""
Константы процедурной версии (КТ2).

Здесь только неизменяемые значения (числа и кортежи): никакого изменяемого
глобального состояния в программе нет, все данные передаются через параметры функций.
"""

# Идентификаторы статусов заказа (совпадают с таблицей order_statuses в data/seed.json)
STATUS_NEW = 1          # Новый
STATUS_CONFIRMED = 2    # Подтверждён
STATUS_COOKING = 3      # Готовится
STATUS_ON_THE_WAY = 4   # Передан курьеру
STATUS_DELIVERED = 5    # Доставлен
STATUS_CANCELLED = 6    # Отменён

# Допустимые переходы между статусами: (откуда, куда)
STATUS_TRANSITIONS = (
    (STATUS_NEW, STATUS_CONFIRMED),
    (STATUS_CONFIRMED, STATUS_COOKING),
    (STATUS_COOKING, STATUS_ON_THE_WAY),
    (STATUS_ON_THE_WAY, STATUS_DELIVERED),
    (STATUS_NEW, STATUS_CANCELLED),
    (STATUS_CONFIRMED, STATUS_CANCELLED),
)

# Заказы в этих статусах занимают станции кухни и формируют очередь
ACTIVE_KITCHEN_STATUSES = (STATUS_NEW, STATUS_CONFIRMED, STATUS_COOKING)

# Правила скидок (алгоритм 1)
VOLUME_MIN_QUANTITY = 3      # от скольких штук одной позиции действует скидка за количество
VOLUME_DISCOUNT = 0.10       # скидка за количество, доля от суммы позиции
LOYALTY_MIN_ORDERS = 5       # сколько доставленных заказов нужно для скидки постоянного клиента
LOYALTY_DISCOUNT = 0.05      # скидка постоянного клиента, доля от суммы заказа

# Параметры кухни и доставки (алгоритм 2)
KITCHEN_STATIONS = 2         # число станций кухни, работающих параллельно
DELIVERY_MINUTES = 15        # время в пути курьера, минут

# Ограничения проверки заказа
MAX_QUANTITY_PER_LINE = 20

# Формат даты и времени в данных
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
