# kbdlayout

`kbdlayout` is a browser-oriented tool for creating physical keyboard models
and rendering them as SVG. A physical model is independent of any keyboard
layout; later, separate legend layers will map Linux `kbd` keycodes to values
from one or more keymaps.

The planned data flow is:

```text
physical model JSON -> SVG geometry layer
kbd keymap -> keycode -> SVG legends layer
```

The canonical physical-model JSON will use absolute keyboard-unit coordinates,
stable key identifiers, and an explicit Linux keycode per key. Keyboard Layout
Editor (KLE) JSON and XKB geometry will be import/export adapters, rather than
the canonical representation.

## SVG renderer

Render a model to SVG with:

```sh
python3 src/kbd-layout.py web/data/models/pc-104-ansi.json > keyboard.svg
```

`make render` regenerates every catalog model and writes SVG next to each JSON
file under `web/data/models/`.
`make models` also writes `web/data/models/catalog.json`, which is the public
static catalog consumed by the browser viewer.

The PC fixtures are imported from the `pc104` and `pc105` XKB geometries in
the local `xkeyboard-config` checkout. Key names are mapped through its evdev
keycode table, using the documented XKB-to-kernel offset of 8:

```sh
make models
```

Generated JSON and SVG files in `web/data/models/` are not tracked. The model
catalog in `models/catalog.tsv` defines every geometry imported by `make models`
and rendered by `make render`.

## Browser viewer

The `web/` directory is a static read-only viewer for generated keyboard
models and keymaps. It reads `web/data/models/catalog.json` and
`web/data/keymaps/catalog.json`, then loads the selected model JSON/SVG and
selected keymap JSON. The active keymap symbols are overlaid on the physical
model. Hovering a key shows its stable key ID and `kbd_keycode`.

Generate the static data before opening the viewer:

```sh
make render
make keymaps
```

The viewer does not require a project backend. `web/` is self-contained after
generation and can be copied to any static server. For a local preview from the
project root:

```sh
make server
```

Then open `http://localhost:8000/`.

Click modifier keys such as Shift, Control, Alt, AltGr, ShiftL, ShiftR, CtrlL,
CtrlR, or CapsShift to toggle them as held. The viewer sums the held kbd
modifier weights to select the matching keymap column and falls back to column
0 when that exact column is not present.

## kbd keymaps

Import one Linux `kbd` keymap through the local `loadkeys` binary:

```sh
python3 src/import-kbd-keymap.py \
  external/kbd/data/keymaps/i386/qwerty/us.map \
  /tmp/us.json
```

The importer runs `loadkeys -u --tkeymap=4` twice: once for symbolic output and
once with `LK_DUMP_NUMERIC=1` for numeric output. The generated JSON preserves
both representations for every `kbd_keycode` and keymap column. `make keymaps`
imports every `.map` below `external/kbd/data/keymaps/i386`, excluding
`include` directories, and writes the static keymap data under
`web/data/keymaps/`.

The directories `external/kbd`, `external/libxkbcommon`,
`external/keyboard-layout-editor`, and `external/xkbprint-kle` are local
reference source checkouts and are intentionally not tracked by this project.
