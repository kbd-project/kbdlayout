# Physical model, version 1

A physical model describes only a keyboard's physical keys. It does not contain
layout-dependent legends, `kbd` keysyms, modifier tables, or KLE formatting.
Its schema is [physical-model.schema.json](../schemas/physical-model.schema.json).

## Coordinate system

All dimensions use keyboard units (`"unit": "u"`). One unit is the width and
height of a standard alphanumeric key. `x` and `y` are absolute coordinates of
the key's top-left corner in a canvas whose origin is top-left; positive `y`
points down.

`w` and `h` specify the key's bounding rectangle. An omitted `outline` means
that rectangle is the key shape. When `outline` is present, it is a closed
polygon expressed in coordinates local to the bounding rectangle. Every point
must be within `0 <= x <= w` and `0 <= y <= h`; this cross-field rule is
validated by the model library, not JSON Schema alone.

`rotation.angle` is in degrees around `rotation.origin`, also expressed in
global keyboard units. With the SVG coordinate system used here, a positive
angle rotates visually clockwise.

## Identity and keycodes

Each `keys[]` item has two independent identifiers:

- `id` is a stable physical-key identifier. XKB names such as `AE01`, `LFSH`
  and `RTRN` are suitable values.
- `linux_keycode` is the Linux console keycode used to attach a `kbd` legend
  layer later. It is explicit; consumers must not infer it from `id`.

Key IDs and Linux keycodes must each be unique within a model. `groups` are
optional named collections of existing key IDs. They aid editing and rendering
of blocks such as the main section, navigation cluster, or numpad; they do not
change key coordinates.

## Compatibility

The canonical format is intentionally absolute and geometry-only. KLE JSON and
XKB geometry will be implemented as adapters. KLE's stateful row encoding,
legends, styles, and keycap profile are not part of this model. Adapter-specific
data may be retained under `extensions`.
