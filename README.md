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

## Legacy renderer

`external/kbd-layout.py` is the original standalone prototype. It renders a
fixed ANSI or ISO PC keyboard from Linux console keymap files and is retained as
reference while the new model-based renderer is built. `src/kbd-layout.py` is
the new command-line entry point.

Render a model to SVG with:

```sh
python3 src/kbd-layout.py models/fixtures/pc-104-ansi.json > keyboard.svg
```

`make render` regenerates every catalog model and writes SVG next to each JSON
file under `models/fixtures/`.
`make models` also writes `models/fixtures/catalog.json`, which is the public
static catalog consumed by the browser viewer.

The PC fixtures are imported from the `pc104` and `pc105` XKB geometries in
the local `xkeyboard-config` checkout. Key names are mapped through its evdev
keycode table, using the documented XKB-to-kernel offset of 8:

```sh
make models
```

Generated JSON and SVG files in `models/fixtures/` are not tracked. The model
catalog in `models/catalog.tsv` defines every geometry imported by `make models`
and rendered by `make render`.

## Browser viewer

The `web/` directory is a static read-only viewer for generated keyboard
models. It reads `models/fixtures/catalog.json`, then loads the selected model
JSON and SVG. It also loads `keymaps/fixtures/us.json` and overlays the active
keymap symbols on the physical model. Clicking a key shows its stable key ID,
`kbd_keycode`, active legend, position, and size.

Generate the static data before opening the viewer:

```sh
make render
make keymaps
```

The viewer does not require a project backend. Use any static file server for
local preview or publishing. For a local preview from the project root:

```sh
make server
```

Then open `http://localhost:8000/web/index.html`.

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
both representations for every `kbd_keycode` and keymap column.

The directories `external/kbd`, `external/libxkbcommon`,
`external/keyboard-layout-editor`, and `external/xkbprint-kle` are local
reference source checkouts and are intentionally not tracked by this project.
