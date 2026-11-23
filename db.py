"""Работа с базой данных SQLite: схема, начальное заполнение, запросы."""
import csv
import os
import sqlite3

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (          -- объекты инфраструктуры
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    type      TEXT NOT NULL,                  -- станция / мост / переезд / участок
    region    TEXT,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL,
    rasp_code TEXT                            -- код станции в Яндекс Расписаниях
);
CREATE TABLE IF NOT EXISTS observations (     -- история наблюдений
    id           INTEGER PRIMARY KEY,
    object_id    INTEGER NOT NULL REFERENCES objects(id),
    ts           TEXT NOT NULL,
    source       TEXT NOT NULL,
    temp         REAL,
    wind         REAL,
    gust         REAL,
    precip       REAL,
    condition    TEXT,
    trains_today INTEGER,
    status       TEXT NOT NULL,               -- norm / weather / repair / closed
    label        TEXT,                        -- подпись состояния: «ремонт», «сильный ветер» и т. п.
    reasons      TEXT
);
CREATE TABLE IF NOT EXISTS restrictions (     -- ремонтные работы и ограничения
    id          INTEGER PRIMARY KEY,
    object_id   INTEGER NOT NULL REFERENCES objects(id),
    kind        TEXT NOT NULL,                -- ремонт / ограничение скорости / закрытие
    description TEXT,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    source      TEXT
);
CREATE TABLE IF NOT EXISTS collector_log (    -- журнал работы сборщиков
    id        INTEGER PRIMARY KEY,
    ts        TEXT NOT NULL,
    collector TEXT NOT NULL,
    ok        INTEGER NOT NULL,
    message   TEXT
);
"""


def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _read_csv(name):
    with open(os.path.join(config.DATA_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        columns = [r["name"] for r in conn.execute("PRAGMA table_info(observations)")]
        if "label" not in columns:  # обновление базы, созданной старой версией
            conn.execute("ALTER TABLE observations ADD COLUMN label TEXT")
        if conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == 0:
            for r in _read_csv("objects.csv"):
                conn.execute(
                    "INSERT INTO objects(name, type, region, lat, lon, rasp_code) VALUES (?,?,?,?,?,?)",
                    (r["name"], r["type"], r["region"], float(r["lat"]), float(r["lon"]), r["rasp_code"] or None),
                )
            import_restrictions_csv(conn, os.path.join(config.DATA_DIR, "restrictions.csv"))


def import_restrictions_csv(conn, path):
    """Импорт ограничений из CSV (колонки: object_name,kind,description,start_date,end_date,source)."""
    count = 0
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            obj = conn.execute("SELECT id FROM objects WHERE name = ?", (r["object_name"],)).fetchone()
            if obj:
                conn.execute(
                    "INSERT INTO restrictions(object_id, kind, description, start_date, end_date, source) VALUES (?,?,?,?,?,?)",
                    (obj["id"], r["kind"], r["description"], r["start_date"], r["end_date"], r["source"]),
                )
                count += 1
    return count


def active_restrictions(conn, object_id, day):
    return conn.execute(
        "SELECT * FROM restrictions WHERE object_id = ? AND start_date <= ? AND end_date >= ?",
        (object_id, day, day),
    ).fetchall()


def latest_observations(conn):
    """Последнее наблюдение по каждому объекту."""
    return conn.execute(
        """SELECT o.*, ob.ts, ob.source, ob.temp, ob.wind, ob.gust, ob.precip, ob.condition,
                  ob.trains_today, ob.status, ob.label, ob.reasons
           FROM objects o
           LEFT JOIN observations ob ON ob.id = (
               SELECT id FROM observations WHERE object_id = o.id ORDER BY ts DESC LIMIT 1)
           ORDER BY o.id"""
    ).fetchall()
