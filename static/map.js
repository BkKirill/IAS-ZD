// Главная страница: интерактивная карта (Яндекс Карты) и таблица состояния объектов
const COLORS = { norm: "#2e9e44", weather: "#2b6cb0", repair: "#e6a100", closed: "#d63a2f", none: "#8a8f98" };
const LABELS = { norm: "норма", weather: "погода", repair: "ремонт", closed: "закрыто", none: "нет данных" };

// Подпись состояния: конкретная («ремонт», «сильный ветер») или общая по категории
function label(o) {
  return o.label || LABELS[o.status || "none"];
}

let map = null;

function fmt(v, suffix = "") {
  return v === null || v === undefined ? "—" : v + suffix;
}

// Тестовые значения (источник без ключа API) помечаем, чтобы их не путали с реальными
function trains(o) {
  if (o.trains_today === null || o.trains_today === undefined) return "—";
  return (o.source || "").includes("yandex_rasp:demo")
    ? `<span class="demo" title="Тестовое значение: не задан ключ API Яндекс Расписаний">${o.trains_today}*</span>`
    : o.trains_today;
}

function balloon(o) {
  const restr = o.restrictions.map(r => `<li><b>${r.kind}</b> (${r.start_date} — ${r.end_date}): ${r.description}</li>`).join("");
  return `<b>${o.name}</b> <span class="muted">(${o.type}, ${o.region})</span><br>
    Состояние: <b style="color:${COLORS[o.status || "none"]}">${label(o)}</b><br>
    ${o.reasons ? "Причины: " + o.reasons + "<br>" : ""}
    Температура: ${fmt(o.temp, " °C")}, ветер: ${fmt(o.wind, " м/с")}, порывы: ${fmt(o.gust, " м/с")}<br>
    ${o.trains_today !== null && o.trains_today !== undefined ? "Поездов сегодня: " + trains(o) + ((o.source || "").includes("yandex_rasp:demo") ? " <span class='muted'>(тестовое значение)</span>" : "") + "<br>" : ""}
    ${restr ? "Действующие ограничения:<ul>" + restr + "</ul>" : ""}
    <span class="muted">Обновлено: ${fmt(o.ts)}, источники: ${fmt(o.source)}</span><br>
    <a href="/history?object=${o.id}">История наблюдений →</a>`;
}

async function load() {
  const data = await (await fetch("/api/state")).json();

  const tbody = document.querySelector("#objects tbody");
  tbody.innerHTML = "";
  data.forEach(o => {
    const st = o.status || "none";
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${o.name}<div class="muted">${o.type}</div></td><td>${fmt(o.temp)}</td>
      <td>${fmt(o.wind)}</td><td>${trains(o)}</td>
      <td><i class="dot ${st}"></i>${label(o)}</td>`;
    tr.title = o.reasons || "";
    tr.onclick = () => map && map.setCenter([o.lat, o.lon], 12);
    tbody.appendChild(tr);
  });

  const demo = data.some(o => (o.source || "").includes("demo"));
  document.getElementById("status-text").textContent =
    demo ? "* — тестовые значения: не задан ключ API Яндекс Расписаний" : "";

  if (!map) return;
  map.geoObjects.removeAll();
  data.forEach(o => {
    map.geoObjects.add(new ymaps.Placemark([o.lat, o.lon],
      { hintContent: `${o.name} — ${label(o)}`, balloonContent: balloon(o) },
      { preset: o.type === "станция" ? "islands#circleDotIcon" : "islands#circleIcon",
        iconColor: COLORS[o.status || "none"] }));
  });
}

document.getElementById("btn-collect").onclick = async e => {
  e.target.disabled = true;
  e.target.textContent = "Сбор данных…";
  await fetch("/api/collect", { method: "POST" });
  e.target.disabled = false;
  e.target.textContent = "Обновить данные сейчас";
  load();
};

if (window.ymaps) {
  ymaps.ready(() => {
    map = new ymaps.Map("map", { center: [53.3, 50.2], zoom: 8, controls: ["zoomControl", "typeSelector", "fullscreenControl"] });
    load();
  });
} else {
  document.getElementById("map").innerHTML = "<p class='muted'>Не удалось загрузить Яндекс Карты. Проверьте подключение к интернету и ключ YANDEX_MAPS_KEY.</p>";
  load();
}
setInterval(load, 60000);
