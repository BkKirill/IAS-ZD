"""Сборщик данных о движении поездов из API Яндекс Расписаний.
Документация: https://yandex.ru/dev/rasp/doc/ru/

Для станций получаем количество рейсов на сегодня. Резкое снижение
числа поездов относительно обычного может говорить об ограничениях движения."""
import random

import config
import db
from .base import BaseCollector

API = "https://api.rasp.yandex.net/v3.0"


class YandexRaspCollector(BaseCollector):
    name = "yandex_rasp"
    title = "Яндекс Расписания"

    def collect(self, obj, day):
        if obj["type"] != "станция":
            return {}
        if not config.YANDEX_RASP_KEY:
            return {"trains_today": random.randint(20, 120), "demo": True} if config.DEMO_IF_NO_KEY else {}

        code = obj["rasp_code"]
        if not code:
            code = self._find_code(obj)
            if not code:
                return {}
            with db.connect() as conn:  # запоминаем код, чтобы не искать его при каждом опросе
                conn.execute("UPDATE objects SET rasp_code = ? WHERE id = ?", (code, obj["id"]))
        data = self.get_json(
            f"{API}/schedule/",
            params={"apikey": config.YANDEX_RASP_KEY, "station": code, "date": day, "limit": 1},
        )
        return {"trains_today": data.get("pagination", {}).get("total")}

    def _find_code(self, obj):
        """Ищет код ближайшей ж/д станции по координатам объекта."""
        data = self.get_json(
            f"{API}/nearest_stations/",
            params={"apikey": config.YANDEX_RASP_KEY, "lat": obj["lat"], "lng": obj["lon"],
                    "distance": 2, "station_types": "train_station,station", "transport_types": "train"},
        )
        stations = data.get("stations", [])
        return stations[0]["code"] if stations else None
