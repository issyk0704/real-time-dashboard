// Default watchlists: SPY/QQQ/DIA stand in for ES/NQ/YM, which the free stock API does not cover
const DEFAULT_WATCHLISTS = {
  stocks: ["SPY", "QQQ", "DIA"],
  crypto: ["BTC", "ETH", "SOL"],
};
const STORAGE_KEY = "watchlists";
const CRYPTO_REFRESH_MS = 60 * 1000;
// Alpha Vantage allows at most 1 request per second on the free tier
const STOCK_REQUEST_GAP_MS = 1100;

const watchlists = loadWatchlists();
const tileTemplate = document.getElementById("tile-template");

function loadWatchlists() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && Array.isArray(saved.stocks) && Array.isArray(saved.crypto)) {
      return saved;
    }
  } catch {
    // Storage unavailable or corrupt: fall back to defaults
  }
  return structuredClone(DEFAULT_WATCHLISTS);
}

function saveWatchlists() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlists));
  } catch {
    // Storage unavailable: the watchlist just won't persist
  }
}

function formatPrice(price) {
  const value = Number(price);
  const digits = value >= 1 ? 2 : 6; // small-cap coins need more decimals
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  });
}

function formatDelta(changePercent) {
  if (changePercent == null) {
    return { text: "", direction: "" };
  }
  const rounded = changePercent.toFixed(2);
  if (Number(rounded) > 0) return { text: `▲ +${rounded}%`, direction: "up" };
  if (Number(rounded) < 0) return { text: `▼ ${rounded}%`, direction: "down" };
  return { text: "0.00%", direction: "" };
}

function sectionFor(kind) {
  return document.getElementById(kind);
}

function createTile(kind, symbol) {
  const tile = tileTemplate.content.firstElementChild.cloneNode(true);
  tile.dataset.symbol = symbol;
  tile.querySelector(".tile-label").textContent = symbol;
  tile.querySelector(".remove").setAttribute("aria-label", `Remove ${symbol}`);
  tile.querySelector(".remove").addEventListener("click", () => removeSymbol(kind, symbol));
  return tile;
}

function renderTiles(kind) {
  const container = sectionFor(kind).querySelector(".tiles");
  container.replaceChildren(...watchlists[kind].map((symbol) => createTile(kind, symbol)));
}

function updateTile(tile, data) {
  const value = tile.querySelector(".tile-value");
  const delta = tile.querySelector(".tile-delta");
  tile.classList.remove("loading", "error");

  if (data.error) {
    tile.classList.add("error");
    value.textContent = "–";
    delta.textContent = data.error;
    delta.className = "tile-delta";
    return;
  }

  value.textContent = formatPrice(data.price);
  const { text, direction } = formatDelta(data.change_percent);
  delta.textContent = text;
  delta.className = `tile-delta ${direction}`;
}

async function fetchQuote(kind, symbol) {
  try {
    const response = await fetch(`/${kind}/${encodeURIComponent(symbol)}`);
    return await response.json();
  } catch {
    return { error: "Server unreachable" };
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setStatus(kind, text) {
  sectionFor(kind).querySelector(".status").textContent = text;
}

async function refresh(kind) {
  const tiles = [...sectionFor(kind).querySelectorAll(".tile")];
  setStatus(kind, "Updating…");
  tiles.forEach((tile) => tile.classList.add("loading"));

  if (kind === "stocks") {
    // Sequential with a gap, to stay under the 1 request/second limit
    for (const [index, tile] of tiles.entries()) {
      if (index > 0) await wait(STOCK_REQUEST_GAP_MS);
      updateTile(tile, await fetchQuote(kind, tile.dataset.symbol));
    }
  } else {
    const results = await Promise.all(tiles.map((tile) => fetchQuote(kind, tile.dataset.symbol)));
    tiles.forEach((tile, index) => updateTile(tile, results[index]));
  }

  setStatus(kind, `Updated ${new Date().toLocaleTimeString()}`);
}

function addSymbol(kind, symbol) {
  const clean = symbol.trim().toUpperCase();
  if (!clean || watchlists[kind].includes(clean)) return;
  watchlists[kind].push(clean);
  saveWatchlists();

  const tile = createTile(kind, clean);
  tile.classList.add("loading");
  sectionFor(kind).querySelector(".tiles").append(tile);
  fetchQuote(kind, clean).then((data) => updateTile(tile, data));
}

function removeSymbol(kind, symbol) {
  watchlists[kind] = watchlists[kind].filter((item) => item !== symbol);
  saveWatchlists();
  sectionFor(kind).querySelector(`.tile[data-symbol="${CSS.escape(symbol)}"]`)?.remove();
}

function wireSection(kind) {
  const section = sectionFor(kind);
  const form = section.querySelector(".add-symbol");
  const input = form.querySelector("input");

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    addSymbol(kind, input.value);
    input.value = "";
  });
  section.querySelector(".refresh").addEventListener("click", () => refresh(kind));

  renderTiles(kind);
  refresh(kind);
}

wireSection("stocks");
wireSection("crypto");
setInterval(() => refresh("crypto"), CRYPTO_REFRESH_MS);
