"use strict";

const catalogUrl = "../models/fixtures/catalog.json";

const state = {
  catalog: null,
  keys: new Map(),
  selected: null,
};

const elements = {
  select: document.querySelector("#model-select"),
  status: document.querySelector("#status"),
  keyboard: document.querySelector("#keyboard"),
  keyId: document.querySelector("#key-id"),
  keycode: document.querySelector("#keycode"),
  keyPosition: document.querySelector("#key-position"),
  keySize: document.querySelector("#key-size"),
};

async function main() {
  state.catalog = await fetchJson(catalogUrl);
  for (const model of state.catalog.models) {
    const option = document.createElement("option");
    option.value = model.id;
    option.textContent = model.name;
    elements.select.append(option);
  }
  elements.select.addEventListener("change", () => loadModel(elements.select.value));
  await loadModel(state.catalog.models[0].id);
}

async function loadModel(modelId) {
  clearSelection();
  const entry = state.catalog.models.find((model) => model.id === modelId);
  if (!entry) {
    throw new Error(`unknown model: ${modelId}`);
  }

  elements.select.value = modelId;
  elements.status.textContent = "Loading...";

  const base = new URL(catalogUrl, window.location.href);
  const [model, svg] = await Promise.all([
    fetchJson(new URL(entry.json, base)),
    fetchText(new URL(entry.svg, base)),
  ]);

  state.keys = new Map(model.keys.map((key) => [key.id, key]));
  elements.keyboard.innerHTML = svg;
  elements.keyboard.querySelectorAll("g[data-key-id]").forEach((node) => {
    node.addEventListener("click", () => selectKey(node.dataset.keyId));
  });
  elements.status.textContent = `${entry.name}: ${model.keys.length} keys`;
}

function selectKey(keyId) {
  clearSelection();

  const node = elements.keyboard.querySelector(`g[data-key-id="${CSS.escape(keyId)}"]`);
  const key = state.keys.get(keyId);
  if (!node || !key) {
    return;
  }

  state.selected = node;
  node.classList.add("selected");
  elements.keyId.textContent = key.id;
  elements.keycode.textContent = key.kbd_keycode ?? "null";
  elements.keyPosition.textContent = `${formatNumber(key.x)}, ${formatNumber(key.y)}`;
  elements.keySize.textContent = `${formatNumber(key.w)} x ${formatNumber(key.h)}`;
}

function clearSelection() {
  if (state.selected) {
    state.selected.classList.remove("selected");
  }
  state.selected = null;
  elements.keyId.textContent = "-";
  elements.keycode.textContent = "-";
  elements.keyPosition.textContent = "-";
  elements.keySize.textContent = "-";
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url}: ${response.status}`);
  }
  return response.json();
}

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url}: ${response.status}`);
  }
  return response.text();
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-US", { maximumFractionDigits: 3 });
}

main().catch((error) => {
  elements.status.textContent = error.message;
  console.error(error);
});
