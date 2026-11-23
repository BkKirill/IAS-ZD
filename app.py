"""Информационно-аналитическая система мониторинга состояния
железнодорожной инфраструктуры. Веб-сервер (Flask)."""
import csv
import datetime
import io
import os
import tempfile
import threading
import time

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

import collectors
import config
import db

app = Flask(__name__)


# ---------- Страницы ----------

@app.route("/")
def index():
    return render_template("index.html", maps_key=config.YANDEX_MAPS_KEY)


@app.route("/history")
def history():
    with db.connect() as conn:
        objects = conn.execute("SELECT id, name FROM objects ORDER BY id").fetchall()
    return render_template("history.html", objects=objects)


@app.route("/restrictions", methods=["GET", "POST"])
def restrictions():
    with db.connect() as conn:
        if request.method == "POST":
            if request.files.get("csv_file") and request.files["csv_file"].filename:
                # Импорт из CSV-файла
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                tmp.close()
                request.files["csv_file"].save(tmp.name)
                db.import_restrictions_csv(conn, tmp.name)
                os.remove(tmp.name)
            else:
                f = request.form
                conn.execute(
                    "INSERT INTO restrictions(object_id, kind, description, start_date, end_date, source) VALUES (?,?,?,?,?,?)",
                    (f["object_id"], f["kind"], f["description"], f["start_date"], f["end_date"], f["source"]),
                )
            return redirect(url_for("restrictions"))
        rows = conn.execute(
            "SELECT r.*, o.name AS object_name FROM restrictions r JOIN objects o ON o.id = r.object_id ORDER BY r.start_date DESC"
        ).fetchall()
        objects = conn.execute("SELECT id, name FROM objects ORDER BY id").fetchall()
    return render_template("restrictions.html", rows=rows, objects=objects,
                           today=datetime.date.today().isoformat())


@app.route("/report")
def report():
    date_from, date_to, rows = _report_data()
    return render_template("report.html", rows=rows, date_from=date_from, date_to=date_to)


@app.route("/report.csv")
def report_csv():
    date_from, date_to, rows = _report_data()
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["Объект", "Тип", "Наблюдений", "Мин. t, °C", "Макс. t, °C", "Макс. ветер, м/с",
                "Неблагоприятная погода", "Ремонт", "Закрыто", "Записей о ремонтах"])
    for r in rows:
        w.writerow([r["name"], r["type"], r["n"], r["tmin"], r["tmax"], r["wmax"],
                    r["weather"] or 0, r["repair"] or 0, r["closed"] or 0, r["restr"]])
    return Response("﻿" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=report_{date_from}_{date_to}.csv"})


@app.route("/log")
def log():
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM collector_log ORDER BY id DESC LIMIT 100").fetchall()
    return render_template("log.html", rows=rows, collectors=collectors.COLLECTORS)


# ---------- API для карты и графиков ----------

@app.route("/api/state")
def api_state():
    today = datetime.date.today().isoformat()
    with db.connect() as conn:
        result = []
        for r in db.latest_observations(conn):
            item = dict(r)
            item["restrictions"] = [dict(x) for x in db.active_restrictions(conn, r["id"], today)]
            result.append(item)
    return jsonify(result)


@app.route("/api/history/<int:object_id>")
def api_history(object_id):
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM observations WHERE object_id = ? ORDER BY ts DESC LIMIT 200", (object_id,)
        ).fetchall()
    return jsonify([dict(r) for r in reversed(rows)])


@app.route("/api/collect", methods=["POST"])
def api_collect():
    n = collectors.run_all()
    return jsonify({"objects": n})


# ---------- Вспомогательное ----------

def _report_data():
    today = datetime.date.today()
    date_from = request.args.get("from") or (today - datetime.timedelta(days=7)).isoformat()
    date_to = request.args.get("to") or today.isoformat()
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT o.name, o.type,
                      COUNT(ob.id) AS n,
                      MIN(ob.temp) AS tmin, MAX(ob.temp) AS tmax,
                      MAX(MAX(COALESCE(ob.wind, 0), COALESCE(ob.gust, 0))) AS wmax,
                      SUM(ob.status = 'weather') AS weather,
                      SUM(ob.status = 'repair') AS repair,
                      SUM(ob.status = 'closed') AS closed,
                      (SELECT COUNT(*) FROM restrictions r WHERE r.object_id = o.id
                         AND r.start_date <= :to AND r.end_date >= :from) AS restr
               FROM objects o
               LEFT JOIN observations ob ON ob.object_id = o.id
                    AND substr(ob.ts, 1, 10) BETWEEN :from AND :to
               GROUP BY o.id ORDER BY closed DESC, repair DESC, weather DESC, o.name""",
            {"from": date_from, "to": date_to},
        ).fetchall()
    return date_from, date_to, rows


def scheduler():
    """Фоновый автоматический сбор данных с заданным интервалом."""
    while True:
        try:
            collectors.run_all()
        except Exception as e:
            print("Ошибка сбора данных:", e)
        time.sleep(config.COLLECT_INTERVAL_MIN * 60)


if __name__ == "__main__":
    os.environ["FLASK_SKIP_DOTENV"] = "1"  # .env читает config.py, подсказка Flask про python-dotenv не нужна
    db.init_db()
    threading.Thread(target=scheduler, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
