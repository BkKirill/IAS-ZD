"""Базовый класс сборщика данных.

Чтобы подключить новый источник, достаточно создать класс-наследник
BaseCollector, реализовать метод collect() и добавить его в список
COLLECTORS в collectors/__init__.py."""
import json
import urllib.parse
import urllib.request


class BaseCollector:
    name = "base"      # машинное имя
    title = "Базовый"  # название для интерфейса

    def collect(self, obj, day):
        """Получить данные по объекту obj (строка таблицы objects) на дату day.
        Возвращает словарь с полями наблюдения (temp, wind, ...), может быть пустым."""
        raise NotImplementedError

    @staticmethod
    def get_json(url, params=None, headers=None, timeout=15):
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
