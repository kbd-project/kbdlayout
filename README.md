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

`make render` prints the default fixture SVG to standard output. Select another
model with `make render MODEL=models/fixtures/pc-105-iso.json`.

The PC fixtures are imported from the `pc104` and `pc105` XKB geometries in
the local `xkeyboard-config` checkout. Key names are mapped through its evdev
keycode table, using the documented XKB-to-kernel offset of 8:

```sh
make models
```

The directories `external/kbd`, `external/libxkbcommon`,
`external/keyboard-layout-editor`, and `external/xkbprint-kle` are local
reference source checkouts and are intentionally not tracked by this project.
