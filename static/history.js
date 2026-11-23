// Страница истории: таблица наблюдений и простой график (SVG, без внешних библиотек)
const LABELS = { norm: "норма", weather: "погода", repair: "ремонт", closed: "закрыто" };
const select = document.getElementById("object");

function line(points, color) {
  return `<polyline fill="none" stroke="${color}" stroke-width="2" points="${points.join(" ")}"/>`;
}

function drawChart(rows) {
  const svg = document.getElementById("chart");
  const W = 900, H = 260, P = 30;
  const vals = rows.flatMap(r => [r.temp, r.wind]).filter(v => v !== null);
  if (rows.length < 2 || !vals.length) {
    svg.innerHTML = `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" fill="#888">Недостаточно данных для графика</text>`;
    return;
  }
  const min = Math.min(0, ...vals), max = Math.max(0, ...vals);
  const x = i => P + i * (W - 2 * P) / (rows.length - 1);
  const y = v => H - P - (v - min) * (H - 2 * P) / (max - min || 1);
  const pts = key => rows.map((r, i) => r[key] === null ? null : `${x(i)},${y(r[key])}`).filter(Boolean);
  svg.innerHTML =
    `<line x1="${P}" x2="${W - P}" y1="${y(0)}" y2="${y(0)}" stroke="#bbb" stroke-dasharray="4"/>
     <text x="2" y="${y(max) + 4}" font-size="11" fill="#888">${max}</text>
     <text x="2" y="${y(min) + 4}" font-size="11" fill="#888">${min}</text>
     <text x="2" y="${y(0) + 4}" font-size="11" fill="#888">0</text>` +
    line(pts("temp"), "#d63a2f") + line(pts("wind"), "#2b6cb0");
}

async function load() {
  const rows = await (await fetch(`/api/history/${select.value}`)).json();
  drawChart(rows);
  document.getElementById("rows").innerHTML = rows.slice().reverse().map(r => `
    <tr><td>${r.ts.replace("T", " ")}</td><td>${r.temp ?? "—"}</td><td>${r.wind ?? "—"}</td>
    <td>${r.gust ?? "—"}</td><td>${r.precip ?? "—"}</td><td>${r.trains_today ?? "—"}</td>
    <td><i class="dot ${r.status}"></i>${r.label || LABELS[r.status] || r.status}</td><td>${r.reasons || ""}</td>
    <td class="muted">${r.source}</td></tr>`).join("");
}

const param = new URLSearchParams(location.search).get("object");
if (param) select.value = param;
select.onchange = load;
load();
