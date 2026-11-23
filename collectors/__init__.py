"""Реестр сборщиков данных и запуск цикла сбора."""
import datetime

import db
import analysis
from .yandex_weather import YandexWeatherCollector
from .yandex_rasp import YandexRaspCollector

# Новые источники данных добавляются в этот список
COLLECTORS = [
    YandexWeatherCollector(),
    YandexRaspCollector(),
]


def run_all():
    """Один цикл: опросить все источники по всем объектам, проанализировать, сохранить."""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    day = now[:10]
    with db.connect() as conn:
        objects = conn.execute("SELECT * FROM objects").fetchall()
        results = {o["id"]: {} for o in objects}
        sources = {o["id"]: [] for o in objects}

        for collector in COLLECTORS:
            errors = 0
            for obj in objects:
                try:
                    data = collector.collect(obj, day)
                except Exception as e:  # источник недоступен — пишем в журнал и продолжаем
                    errors += 1
                    last_error = str(e)
                    continue
                if data:
                    is_demo = data.pop("demo", False)
                    results[obj["id"]].update(data)
                    sources[obj["id"]].append(collector.name + (":demo" if is_demo else ""))
            msg = "OK" if errors == 0 else f"ошибок: {errors}, последняя: {last_error}"
            conn.execute("INSERT INTO collector_log(ts, collector, ok, message) VALUES (?,?,?,?)",
                         (now, collector.name, int(errors == 0), msg))

        for obj in objects:
            data = results[obj["id"]]
            restrictions = db.active_restrictions(conn, obj["id"], day)
            status, label, reasons = analysis.evaluate(data, restrictions)
            conn.execute(
                """INSERT INTO observations(object_id, ts, source, temp, wind, gust, precip,
                                            condition, trains_today, status, label, reasons)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (obj["id"], now, ",".join(sources[obj["id"]]) or "-", data.get("temp"), data.get("wind"),
                 data.get("gust"), data.get("precip"), data.get("condition"), data.get("trains_today"),
                 status, label, "; ".join(reasons)),
            )
    return len(objects)
