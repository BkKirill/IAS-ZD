"""Настройки системы. Ключи API задаются через переменные окружения
или файл .env рядом с этим файлом (формат: КЛЮЧ=значение)."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_env_file():
    path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if not os.environ.get(key):  # пустая переменная окружения не перекрывает .env
                    os.environ[key] = value.strip()


_load_env_file()

DB_PATH = os.path.join(BASE_DIR, "railmon.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Российские сервисы
YANDEX_WEATHER_KEY = os.environ.get("YANDEX_WEATHER_KEY", "")  # Яндекс Погода
YANDEX_RASP_KEY = os.environ.get("YANDEX_RASP_KEY", "")        # Яндекс Расписания
YANDEX_MAPS_KEY = os.environ.get("YANDEX_MAPS_KEY", "")        # Яндекс Карты (JS API)

# Период автоматического опроса источников, минут
COLLECT_INTERVAL_MIN = int(os.environ.get("COLLECT_INTERVAL_MIN", "60"))

# Как часто запрашивать погоду по одному объекту, минут (у API Погоды есть лимит запросов)
WEATHER_CACHE_MIN = int(os.environ.get("WEATHER_CACHE_MIN", "180"))

# Если ключа нет — коллектор выдаёт тестовые данные (помечаются source=demo)
DEMO_IF_NO_KEY = os.environ.get("DEMO_IF_NO_KEY", "0") == "1"
