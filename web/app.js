"use strict";

const catalogUrl = "../models/fixtures/catalog.json";
const keymapUrl = "../keymaps/fixtures/us.json";

const modifierWeights = new Map([
  ["Shift", 1],
  ["AltGr", 2],
  ["Control", 4],
  ["Alt", 8],
  ["ShiftL", 16],
  ["ShiftR", 32],
  ["CtrlL", 64],
  ["CtrlR", 128],
  ["CapsShift", 256],
]);

const symbolAliases = new Map([
  ["space", "␠"],
  ["Tab", "Tab"],
  ["Escape", "Esc"],
  ["Delete", "Del"],
  ["BackSpace", "Bksp"],
  ["Return", "Ret"],
  ["Linefeed", "Lf"],
  ["one", "1"],
  ["two", "2"],
  ["three", "3"],
  ["four", "4"],
  ["five", "5"],
  ["six", "6"],
  ["seven", "7"],
  ["eight", "8"],
  ["nine", "9"],
  ["zero", "0"],
  ["exclam", "!"],
  ["at", "@"],
  ["numbersign", "#"],
  ["dollar", "$"],
  ["percent", "%"],
  ["asciicircum", "^"],
  ["ampersand", "&"],
  ["asterisk", "*"],
  ["parenleft", "("],
  ["parenright", ")"],
  ["minus", "-"],
  ["underscore", "_"],
  ["equal", "="],
  ["plus", "+"],
  ["bracketleft", "["],
  ["bracketright", "]"],
  ["braceleft", "{"],
  ["braceright", "}"],
  ["backslash", "\\"],
  ["bar", "|"],
  ["semicolon", ";"],
  ["colon", ":"],
  ["apostrophe", "'"],
  ["quotedbl", "\""],
  ["grave", "`"],
  ["asciitilde", "~"],
  ["comma", ","],
  ["less", "<"],
  ["period", "."],
  ["greater", ">"],
  ["slash", "/"],
  ["question", "?"],
]);

const symbolPrefixes = [
  ["Meta_", "M-"],
  ["Control_", "C-"],
];

const state = {
  catalog: null,
  keymap: null,
  keymapByKeycode: new Map(),
  keys: new Map(),
  selected: null,
  heldModifiers: new Map(),
};

const elements = {
  select: document.querySelector("#model-select"),
  status: document.querySelector("#status"),
  keymapStatus: document.querySelector("#keymap-status"),
  modifierStatus: document.querySelector("#modifier-status"),
  keyboard: document.querySelector("#keyboard"),
  keyId: document.querySelector("#key-id"),
  keycode: document.querySelector("#keycode"),
  legend: document.querySelector("#legend"),
  keyPosition: document.querySelector("#key-position"),
  keySize: document.querySelector("#key-size"),
};

async function main() {
  const [catalog, keymap] = await Promise.all([
    fetchJson(catalogUrl),
    fetchJson(keymapUrl),
  ]);
  state.catalog = catalog;
  state.keymap = keymap;
  state.keymapByKeycode = new Map(keymap.keys.map((key) => [key.kbd_keycode, key]));
  elements.keymapStatus.textContent = `Keymap: ${keymap.id}`;
  updateModifierStatus();

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
    node.addEventListener("click", () => pressKey(node.dataset.keyId));
  });
  renderKeymapLegends();
  renderHeldModifiers();
  elements.status.textContent = `${entry.name}: ${model.keys.length} keys`;
}

function pressKey(keyId) {
  const key = state.keys.get(keyId);
  const modifier = key ? modifierForKey(key) : null;
  if (modifier) {
    toggleModifier(key, modifier);
  }
  selectKey(keyId);
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
  elements.legend.textContent = legendForKey(key)?.symbol ?? "-";
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
  elements.legend.textContent = "-";
  elements.keyPosition.textContent = "-";
  elements.keySize.textContent = "-";
}

function toggleModifier(key, modifier) {
  if (state.heldModifiers.has(key.id)) {
    state.heldModifiers.delete(key.id);
  } else {
    state.heldModifiers.set(key.id, modifier);
  }
  renderHeldModifiers();
  renderKeymapLegends();
  updateModifierStatus();
}

function renderHeldModifiers() {
  elements.keyboard.querySelectorAll("g[data-key-id].held").forEach((node) => {
    node.classList.remove("held");
  });
  for (const keyId of state.heldModifiers.keys()) {
    const node = elements.keyboard.querySelector(`g[data-key-id="${CSS.escape(keyId)}"]`);
    node?.classList.add("held");
  }
}

function renderKeymapLegends() {
  const overlay = elements.keyboard.querySelector("#overlay-legends");
  if (!overlay) {
    return;
  }

  overlay.replaceChildren();
  for (const key of state.keys.values()) {
    const entry = legendForKey(key);
    if (!entry || entry.symbol === "VoidSymbol") {
      continue;
    }

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.classList.add("keymap-legend");
    label.setAttribute("x", formatSvgNumber(key.x + key.w / 2));
    label.setAttribute("y", formatSvgNumber(key.y + key.h / 2));
    label.setAttribute("font-size", formatSvgNumber(legendFontSize(key, entry.symbol)));
    label.setAttribute("dominant-baseline", "middle");
    label.append(svgTitle(entry.symbol));
    label.append(document.createTextNode(compactSymbol(entry.symbol)));
    if (key.rotation) {
      const [originX, originY] = key.rotation.origin;
      label.setAttribute("transform", `rotate(${key.rotation.angle} ${originX} ${originY})`);
    }
    overlay.append(label);
  }
}

function legendForKey(key) {
  if (key.kbd_keycode === null) {
    return null;
  }
  const keymapKey = state.keymapByKeycode.get(key.kbd_keycode);
  if (!keymapKey) {
    return null;
  }

  const activeKeymap = activeKeymapColumn();
  return (
    keymapKey.entries.find((entry) => entry.keymap === activeKeymap)
    ?? keymapKey.entries.find((entry) => entry.keymap === 0)
    ?? null
  );
}

function modifierForKey(key) {
  const baseEntry = state.keymapByKeycode.get(key.kbd_keycode)?.entries.find((entry) => entry.keymap === 0);
  return baseEntry ? modifierWeights.get(baseEntry.symbol) : null;
}

function activeKeymapColumn() {
  const keymap = rawActiveKeymapColumn();
  return state.keymap.keymaps.includes(keymap) ? keymap : 0;
}

function rawActiveKeymapColumn() {
  return heldModifierWeights().reduce((keymap, weight) => keymap + weight, 0);
}

function updateModifierStatus() {
  const modifiers = heldModifierWeights();
  const held = modifiers.length ? modifierNames(modifiers).join("+") : "none";
  const raw = rawActiveKeymapColumn();
  const active = activeKeymapColumn();
  const fallback = raw === active ? "" : `, using ${active}`;
  elements.modifierStatus.textContent = `Held: ${held}; keymap ${raw}${fallback}`;
}

function heldModifierWeights() {
  return [...new Set(state.heldModifiers.values())];
}

function modifierNames(weights) {
  return weights.map((weight) => {
    for (const [name, value] of modifierWeights) {
      if (value === weight) {
        return name;
      }
    }
    return String(weight);
  });
}

function compactSymbol(symbol) {
  let value = symbol.startsWith("+") ? symbol.slice(1) : symbol;
  let prefix = "";
  let changed = true;
  while (changed) {
    changed = false;
    for (const [source, replacement] of symbolPrefixes) {
      if (value.startsWith(source)) {
        prefix += replacement;
        value = value.slice(source.length);
        changed = true;
      }
    }
  }
  return `${prefix}${symbolAliases.get(value) ?? value}`;
}

function legendFontSize(key, symbol) {
  const compact = compactSymbol(symbol);
  const maxSize = 0.28;
  const minSize = 0.12;
  const maxWidth = key.w * 0.8;
  const estimatedSize = maxWidth / Math.max(compact.length * 0.55, 1);
  return Math.max(minSize, Math.min(maxSize, estimatedSize));
}

function svgTitle(text) {
  const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
  title.textContent = text;
  return title;
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

function formatSvgNumber(value) {
  return Number(value).toFixed(3).replace(/\.?0+$/, "");
}

main().catch((error) => {
  elements.status.textContent = error.message;
  console.error(error);
});
