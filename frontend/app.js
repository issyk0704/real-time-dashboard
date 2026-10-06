// Yahoo symbols: CME futures (=F), DXY, FX pairs (=X), 10-year note futures and bitcoin
const DEFAULT_WATCHLIST = ["NQ=F", "ES=F", "YM=F", "DX-Y.NYB", "EURUSD=X", "GBPUSD=X", "ZN=F", "BTC-USD"];
const STORAGE_KEY = "watchlist-v2";
const LEVEL_NAMES = ["PDH", "PDL", "PWH", "PWL", "PMH", "PML"];
const NEWS_WINDOW_MINUTES = 15;
const MINUTES_PER_DAY = 24 * 60;

let watchlist = loadWatchlist();
let latestSnapshot = null;
let eventSource = null;
let chart = null;

const nyFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: "America/New_York",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

// ---------- Storage ----------

function loadWatchlist() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(saved)) return saved;
  } catch {
    // Storage unavailable or corrupt: fall back to defaults
  }
  return [...DEFAULT_WATCHLIST];
}

function saveWatchlist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist));
  } catch {
    // Storage unavailable: the watchlist just won't persist
  }
}

// ---------- Formatting ----------

function priceDigits(value) {
  const size = Math.abs(value);
  if (size < 10) return 5; // FX pairs
  if (size < 1000) return 3; // DXY, ZN
  return 2;
}

function formatPrice(value) {
  if (value == null) return "–";
  const digits = priceDigits(value);
  return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function formatDelta(changePercent) {
  if (changePercent == null) return { text: "", direction: "" };
  const rounded = changePercent.toFixed(2);
  if (Number(rounded) > 0) return { text: `▲ +${rounded}%`, direction: "up" };
  if (Number(rounded) < 0) return { text: `▼ ${rounded}%`, direction: "down" };
  return { text: "0.00%", direction: "" };
}

function formatDuration(minutes) {
  const total = Math.max(1, Math.ceil(minutes));
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  return hours ? `${hours}h ${rest}m` : `${rest}m`;
}

function nyParts(date) {
  const parts = Object.fromEntries(nyFormatter.formatToParts(date).map((part) => [part.type, part.value]));
  return {
    weekday: parts.weekday,
    text: `${parts.hour}:${parts.minute}:${parts.second}`,
    minuteOfDay: Number(parts.hour) * 60 + Number(parts.minute) + Number(parts.second) / 60,
  };
}

function formatNyEventTime(isoTime) {
  const parts = nyParts(new Date(isoTime));
  return `${parts.weekday} ${parts.text.slice(0, 5)}`;
}

// ---------- DOM helpers ----------

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function sparkline(values) {
  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("class", "sparkline");
  svg.setAttribute("viewBox", "0 0 100 32");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  if (values.length < 2) return svg;

  const min = Math.min(...values);
  const range = Math.max(...values) - min || 1;
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * 100;
    const y = 31 - ((value - min) / range) * 30;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const line = document.createElementNS(svgNs, "polyline");
  line.setAttribute("points", points.join(" "));
  svg.append(line);
  return svg;
}

// ---------- Session clock ----------

function minutesOf(hhmm) {
  const [hours, minutes] = hhmm.split(":").map(Number);
  return hours * 60 + minutes;
}

function windowEnd(window) {
  return window.end === "00:00" ? MINUTES_PER_DAY : minutesOf(window.end);
}

function activeWindow(windows, minuteOfDay) {
  return windows.find((window) => minuteOfDay >= minutesOf(window.start) && minuteOfDay < windowEnd(window));
}

function nextWindow(windows, minuteOfDay) {
  const untilStart = (window) => (minutesOf(window.start) - minuteOfDay + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  return windows.reduce((best, window) => (untilStart(window) < untilStart(best) ? window : best));
}

function setPill(id, text, active) {
  const pill = document.getElementById(id);
  pill.textContent = text;
  pill.classList.toggle("active", Boolean(active));
}

function renderClock() {
  const now = new Date();
  const ny = nyParts(now);
  setPill("ny-clock", `${ny.weekday} ${ny.text} NY`);
  if (!latestSnapshot) return;

  const { killzones, macros } = latestSnapshot.sessions;
  const killzone = activeWindow(killzones, ny.minuteOfDay);
  if (killzone) {
    setPill("killzone-status", `${killzone.name} killzone · ${formatDuration(windowEnd(killzone) - ny.minuteOfDay)} left`, true);
  } else {
    const next = nextWindow(killzones, ny.minuteOfDay);
    const wait = (minutesOf(next.start) - ny.minuteOfDay + MINUTES_PER_DAY) % MINUTES_PER_DAY;
    setPill("killzone-status", `Next: ${next.name} in ${formatDuration(wait)}`, false);
  }

  const macro = activeWindow(macros, ny.minuteOfDay);
  if (macro) {
    setPill("macro-status", `Macro ${macro.start}–${macro.end} · ${formatDuration(windowEnd(macro) - ny.minuteOfDay)} left`, true);
  } else {
    const next = nextWindow(macros, ny.minuteOfDay);
    const wait = (minutesOf(next.start) - ny.minuteOfDay + MINUTES_PER_DAY) % MINUTES_PER_DAY;
    setPill("macro-status", `Next macro ${next.start} in ${formatDuration(wait)}`, false);
  }

  document.querySelectorAll("#killzone-table thead th[data-killzone]").forEach((th) => {
    th.classList.toggle("active", th.dataset.killzone === killzone?.name);
  });
  renderNewsBanner(now);
}

function renderNewsBanner(now) {
  const banner = document.getElementById("news-banner");
  const nearby = latestSnapshot.calendar
    .filter((event) => event.impact === "High")
    .map((event) => ({ ...event, minutesAway: (new Date(event.time) - now) / 60000 }))
    .filter((event) => Math.abs(event.minutesAway) <= NEWS_WINDOW_MINUTES)
    .sort((a, b) => Math.abs(a.minutesAway) - Math.abs(b.minutesAway))[0];

  banner.hidden = !nearby;
  if (!nearby) return;
  const when = nearby.minutesAway >= 0 ? `in ${formatDuration(nearby.minutesAway)}` : `${formatDuration(-nearby.minutesAway)} ago`;
  banner.textContent = `⚠ High-impact news: ${nearby.currency} ${nearby.title} ${when}`;
}

// ---------- Rendering ----------

function renderTiles(quotes) {
  const tiles = quotes.map((quote) => {
    const tile = el("div", quote.error ? "tile error" : "tile");
    tile.dataset.symbol = quote.symbol;

    const open = el("button", "tile-open");
    open.type = "button";
    open.setAttribute("aria-label", `Open ${quote.name} chart`);
    open.append(el("span", "tile-label", quote.name));
    if (quote.error) {
      open.disabled = true;
      open.append(el("span", "tile-value", "–"), el("span", "tile-delta", quote.error));
    } else {
      const { text, direction } = formatDelta(quote.change_percent);
      open.append(el("span", "tile-value", formatPrice(quote.price)), el("span", `tile-delta ${direction}`, text),
        sparkline(quote.sparkline));
      open.addEventListener("click", () => openChart(quote.symbol, quote.name));
    }

    const remove = el("button", "remove", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", `Remove ${quote.name}`);
    remove.addEventListener("click", () => removeSymbol(quote.symbol));

    tile.append(open, remove);
    return tile;
  });
  const container = document.getElementById("tiles");
  if (tiles.length) {
    container.replaceChildren(...tiles);
  } else {
    container.replaceChildren(el("p", "note", "Add a symbol to start."));
  }
}

function renderLevels(quotes) {
  const rows = quotes.map((quote) => {
    const row = el("tr");
    row.append(el("th", null, quote.name));
    row.firstChild.scope = "row";
    LEVEL_NAMES.forEach((name) => {
      const level = quote.levels?.[name];
      const cell = el("td", null, level ? formatPrice(level.price) : "–");
      // Every cell gets the same-width slot so the prices stay aligned in a column
      const slot = el("span", "tag-slot");
      if (level?.swept) slot.append(el("span", "tag", "swept"));
      cell.append(slot);
      row.append(cell);
    });
    return row;
  });
  document.querySelector("#levels-table tbody").replaceChildren(...rows);
}

function renderKillzones(quotes, killzones) {
  const headerRow = el("tr");
  headerRow.append(el("th", null, "Market"));
  killzones.forEach((killzone) => {
    const th = el("th", null, `${killzone.name} (${killzone.start}–${killzone.end})`);
    th.dataset.killzone = killzone.name;
    headerRow.append(th);
  });
  headerRow.querySelectorAll("th").forEach((th) => (th.scope = "col"));
  document.querySelector("#killzone-table thead").replaceChildren(headerRow);

  const rows = quotes.map((quote) => {
    const row = el("tr");
    row.append(el("th", null, quote.name));
    row.firstChild.scope = "row";
    killzones.forEach((killzone) => {
      const range = quote.killzones?.[killzone.name];
      const cell = el("td");
      if (range) {
        cell.append(el("span", "range-high", `H ${formatPrice(range.high)}`), el("span", "range-low", `L ${formatPrice(range.low)}`));
      } else {
        cell.append(el("span", "muted-text", "–"));
      }
      row.append(cell);
    });
    return row;
  });
  document.querySelector("#killzone-table tbody").replaceChildren(...rows);
}

function renderSmt(signals) {
  const list = document.getElementById("smt-list");
  if (!signals.length) {
    list.replaceChildren(el("li", "muted-text", "No divergence between the latest two killzones."));
    return;
  }
  list.replaceChildren(...signals.map((signal) => {
    const item = el("li");
    const pair = el("strong", null, signal.pair);
    const detail = ` · ${signal.killzone} vs ${signal.reference} ${signal.side}: ${signal.swept} swept, ${signal.failed} failed`;
    const bias = el("span", `smt-bias ${signal.bias === "bullish" ? "up" : "down"}`,
      `${signal.bias === "bullish" ? "▲ Bullish" : "▼ Bearish"} ${signal.bias_market}`);
    item.append(pair, detail, bias);
    return item;
  }));
}

function renderCalendar(events) {
  const now = new Date();
  const rows = events.map((event) => {
    const row = el("tr", new Date(event.time) < now ? "past" : "");
    row.append(
      el("td", null, formatNyEventTime(event.time)),
      el("td", null, event.currency),
      el("td", null, event.impact),
      el("td", null, event.title),
      el("td", null, event.forecast || "–"),
      el("td", null, event.previous || "–"),
    );
    return row;
  });
  const body = document.querySelector("#calendar-table tbody");
  if (rows.length) {
    body.replaceChildren(...rows);
  } else {
    const row = el("tr");
    const cell = el("td", "muted-text", "No upcoming events.");
    cell.colSpan = 6;
    row.append(cell);
    body.replaceChildren(row);
  }
}

function render(snapshot) {
  latestSnapshot = snapshot;
  renderTiles(snapshot.quotes);
  renderLevels(snapshot.quotes);
  renderKillzones(snapshot.quotes, snapshot.sessions.killzones);
  renderSmt(snapshot.smt);
  renderCalendar(snapshot.calendar);
  renderClock();
}

// ---------- Live updates (Server-Sent Events) ----------

function setConnection(text) {
  document.getElementById("connection-status").textContent = text;
}

function connect() {
  eventSource?.close();
  if (!watchlist.length) {
    renderTiles([]);
    setConnection("Idle");
    return;
  }
  setConnection("Connecting…");
  eventSource = new EventSource(`/api/stream?symbols=${encodeURIComponent(watchlist.join(","))}`);
  eventSource.onmessage = (message) => {
    render(JSON.parse(message.data));
    setConnection(`Live · updated ${nyParts(new Date()).text}`);
  };
  // EventSource reconnects by itself; just tell the viewer
  eventSource.onerror = () => setConnection("Reconnecting…");
}

function addSymbol(symbol) {
  const clean = symbol.trim().toUpperCase();
  if (!clean || watchlist.includes(clean)) return;
  watchlist.push(clean);
  saveWatchlist();
  connect();
}

function removeSymbol(symbol) {
  watchlist = watchlist.filter((item) => item !== symbol);
  saveWatchlist();
  document.querySelector(`.tile[data-symbol="${CSS.escape(symbol)}"]`)?.remove();
  connect();
}

// ---------- Chart dialog ----------

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

async function openChart(symbol, name) {
  const dialog = document.getElementById("chart-dialog");
  const container = document.getElementById("chart");
  document.getElementById("chart-title").textContent = name;
  container.replaceChildren(el("p", "note", "Loading…"));
  dialog.showModal();

  let history;
  try {
    history = await (await fetch(`/api/history/${encodeURIComponent(symbol)}`)).json();
  } catch {
    container.replaceChildren(el("p", "note", "Could not load chart data."));
    return;
  }
  if (!dialog.open) return;
  if (!window.LightweightCharts) {
    container.replaceChildren(el("p", "note", "Chart library failed to load."));
    return;
  }
  if (!history.candles?.length) {
    container.replaceChildren(el("p", "note", "No chart data for this symbol."));
    return;
  }

  container.replaceChildren();
  const charts = window.LightweightCharts;
  chart = charts.createChart(container, {
    autoSize: true,
    layout: { background: { color: cssVar("--surface") }, textColor: cssVar("--text-secondary") },
    grid: { vertLines: { color: cssVar("--gridline") }, horzLines: { color: cssVar("--gridline") } },
    timeScale: { timeVisible: true, secondsVisible: false },
  });
  const digits = priceDigits(history.candles.at(-1).close);
  const series = chart.addSeries(charts.CandlestickSeries, {
    upColor: cssVar("--delta-up"),
    downColor: cssVar("--delta-down"),
    wickUpColor: cssVar("--delta-up"),
    wickDownColor: cssVar("--delta-down"),
    borderVisible: false,
    priceFormat: { type: "price", precision: digits, minMove: 10 ** -digits },
  });
  series.setData(history.candles);
  Object.entries(history.levels).forEach(([levelName, level]) => {
    series.createPriceLine({
      price: level.price,
      color: cssVar("--text-muted"),
      lineWidth: 1,
      lineStyle: charts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: level.swept ? `${levelName} (swept)` : levelName,
    });
  });
  // Show roughly the last trading day of 5-minute candles
  const count = history.candles.length;
  chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, count - 280), to: count + 5 });
}

function closeChart() {
  chart?.remove();
  chart = null;
}

// ---------- Start-up ----------

document.getElementById("add-symbol").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.getElementById("symbol-input");
  addSymbol(input.value);
  input.value = "";
});
document.getElementById("chart-close").addEventListener("click", () => document.getElementById("chart-dialog").close());
document.getElementById("chart-dialog").addEventListener("close", closeChart);

connect();
renderClock();
setInterval(renderClock, 1000);
