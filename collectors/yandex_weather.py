"""Сборщик погодных данных из API Яндекс Погоды.
Документация: https://yandex.ru/dev/weather/"""
import random
import time

import config
from .base import BaseCollector

API_URL = "https://api.weather.yandex.ru/v2/forecast"


class YandexWeatherCollector(BaseCollector):
    name = "yandex_weather"
    title = "Яндекс Погода"

    def __init__(self):
        self._cache = {}  # object_id -> (время запроса, данные)

    def collect(self, obj, day):
        if not config.YANDEX_WEATHER_KEY:
            return self._demo(obj) if config.DEMO_IF_NO_KEY else {}

        # У API есть лимит запросов, поэтому по каждому объекту запрашиваем
        # не чаще WEATHER_CACHE_MIN минут, а при ошибке берём последнее значение
        cached = self._cache.get(obj["id"])
        if cached and time.time() - cached[0] < config.WEATHER_CACHE_MIN * 60:
            return dict(cached[1])
        time.sleep(1)  # пауза между запросами, чтобы не превышать ограничение API
        try:
            data = self.get_json(
                API_URL,
                params={"lat": obj["lat"], "lon": obj["lon"], "lang": "ru_RU", "limit": 1},
                headers={"X-Yandex-Weather-Key": config.YANDEX_WEATHER_KEY},
            )
        except Exception:
            if cached:
                return dict(cached[1])
            raise
        fact = data.get("fact", {})
        result = {
            "temp": fact.get("temp"),
            "wind": fact.get("wind_speed"),
            "gust": fact.get("wind_gust"),
            "precip": fact.get("prec_strength"),  # 0..1: от «без осадков» до «очень сильные»
            "condition": fact.get("condition"),
        }
        self._cache[obj["id"]] = (time.time(), result)
        return dict(result)

    @staticmethod
    def _demo(obj):
        """Тестовые значения для работы без ключа API."""
        rnd = random.Random()
        return {
            "temp": round(rnd.uniform(-32, 5), 1),
            "wind": round(rnd.uniform(0, 22), 1),
            "gust": round(rnd.uniform(5, 30), 1),
            "precip": rnd.choice([0, 0, 0.25, 0.5, 0.75, 1]),
            "condition": rnd.choice(["clear", "cloudy", "snow", "light-snow", "snowfall"]),
            "demo": True,
        }
