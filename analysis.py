"""Модуль анализа: определение состояния объекта по собранным данным.

Каждое правило — функция, которая получает данные и список активных
ограничений и возвращает (категория, подпись, причина) или None.
Новые правила добавляются в список RULES.

Категории (по убыванию важности):
  closed  — движение закрыто
  repair  — ремонт или ограничение скорости
  weather — неблагоприятная погода
  norm    — норма
"""

PRIORITY = {"norm": 0, "weather": 1, "repair": 2, "closed": 3}


def rule_temperature(data, restrictions):
    t = data.get("temp")
    if t is None:
        return None
    if t <= -25:
        return "weather", "сильный мороз", f"температура {t} °C (риск деформации пути)"
    if t >= 30:
        return "weather", "жара", f"температура {t} °C (риск выброса пути)"
    return None


def rule_wind(data, restrictions):
    w = max(data.get("wind") or 0, data.get("gust") or 0)
    if w >= 15:
        return "weather", "сильный ветер", f"ветер, порывы до {w} м/с"
    return None


def rule_precipitation(data, restrictions):
    p = data.get("precip")
    if p is not None and p >= 0.75:
        return "weather", "сильные осадки", "сильные осадки (снегопад/ливень)"
    return None


def rule_restrictions(data, restrictions):
    worst = None
    for r in restrictions:
        if r["kind"] == "закрытие":
            res = ("closed", "движение закрыто", f"закрытие: {r['description']}")
        elif r["kind"] == "ограничение скорости":
            res = ("repair", "ограничение скорости", f"ограничение скорости: {r['description']}")
        else:
            res = ("repair", "ремонт", f"ремонт: {r['description']}")
        if worst is None or PRIORITY[res[0]] > PRIORITY[worst[0]]:
            worst = res
    return worst


RULES = [rule_temperature, rule_wind, rule_precipitation, rule_restrictions]


def evaluate(data, restrictions):
    """Возвращает (категория, подпись, список причин)."""
    status, label, reasons = "norm", "норма", []
    for rule in RULES:
        res = rule(data, restrictions)
        if res:
            category, rule_label, reason = res
            reasons.append(reason)
            if PRIORITY[category] > PRIORITY[status]:
                status, label = category, rule_label
    return status, label, reasons
