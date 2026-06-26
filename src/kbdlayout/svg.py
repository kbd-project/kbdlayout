"""Static SVG rendering for physical keyboard models."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from .model import Bounds, Doodad, Key, Model


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
XKB_COLORS = {
    "black": ("#111", "#eee"),
    "blue": ("#4f7ec8", "#fff"),
    "grey": ("#d8d8d8", "#555"),
    "grey10": ("#1a1a1a", "#eee"),
    "grey20": ("#555", "#eee"),
    "grey30": ("#777", "#fff"),
    "grey40": ("#999", "#222"),
    "grey60": ("#c4c4c4", "#555"),
    "grey70": ("#d6d6d6", "#555"),
    "grey80": ("#e6e6e6", "#555"),
    "red": ("#c94f4f", "#fff"),
    "white": ("#f6f6f6", "#555"),
}


def render_svg(model: Model, *, scale: float = 60, padding: float = 0.1) -> str:
    """Render a physical model as a standalone, geometry-only SVG."""
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if padding < 0:
        raise ValueError("padding must not be negative")

    bounds = model.bounds()
    view_x = bounds.x - padding
    view_y = bounds.y - padding
    view_w = bounds.w + 2 * padding
    view_h = bounds.h + 2 * padding
    svg = ET.Element(
        _tag("svg"),
        {
            "width": _number(view_w * scale),
            "height": _number(view_h * scale),
            "viewBox": " ".join(map(_number, (view_x, view_y, view_w, view_h))),
        },
    )

    style = ET.SubElement(svg, _tag("style"))
    style.text = (
        ".keyboard-frame { fill: var(--doodad-fill, #ddd); stroke: #aaa; stroke-width: 0.03; }"
        ".key { fill: var(--key-fill, #eee); stroke: #777; stroke-width: 0.03; }"
        ".key-id { fill: var(--key-id-fill, #555); font: 0.16px sans-serif; pointer-events: none; }"
    )

    geometry = ET.SubElement(svg, _tag("g"), {"id": "keyboard-geometry"})
    decorations = ET.SubElement(geometry, _tag("g"), {"id": "keyboard-decorations"})
    _render_decorations(decorations, model)
    keys = ET.SubElement(geometry, _tag("g"), {"id": "keys"})
    for key in model.keys:
        _render_key(keys, key)

    factory_legends = ET.SubElement(svg, _tag("g"), {"id": "factory-legends"})
    for key in model.keys:
        _render_key_id(factory_legends, key)
    ET.SubElement(svg, _tag("g"), {"id": "overlay-legends"})
    return ET.tostring(svg, encoding="unicode", xml_declaration=True)


def _render_decorations(parent: ET.Element, model: Model) -> None:
    if model.doodads:
        for doodad in model.doodads:
            _render_doodad(parent, doodad)
    elif model.bounds_hint is not None:
        _render_frame(parent, model.bounds_hint)


def _render_doodad(parent: ET.Element, doodad: Doodad) -> None:
    if doodad.outline is None:
        attributes = {
            "class": "keyboard-frame",
            "id": f"doodad-{doodad.id}",
            "x": _number(doodad.x),
            "y": _number(doodad.y),
            "width": _number(doodad.w),
            "height": _number(doodad.h),
        }
        if doodad.corner_radius is not None:
            radius = _number(min(doodad.corner_radius, doodad.w / 2, doodad.h / 2))
            attributes["rx"] = radius
            attributes["ry"] = radius
        attributes.update(_doodad_style(doodad))
        ET.SubElement(parent, _tag("rect"), attributes)
        return

    points = " ".join(f"{_number(x)},{_number(y)}" for x, y in doodad.points())
    attributes = {"class": "keyboard-frame", "id": f"doodad-{doodad.id}", "points": points}
    attributes.update(_doodad_style(doodad))
    ET.SubElement(parent, _tag("polygon"), attributes)


def _render_frame(parent: ET.Element, bounds: Bounds) -> None:
    ET.SubElement(
        parent,
        _tag("rect"),
        {
            "class": "keyboard-frame",
            "x": _number(bounds.x),
            "y": _number(bounds.y),
            "width": _number(bounds.w),
            "height": _number(bounds.h),
        },
    )


def _render_key(parent: ET.Element, key: Key) -> None:
    key_group = ET.SubElement(
        parent,
        _tag("g"),
        {
            "id": f"key-{key.id}",
            "data-key-id": key.id,
            "data-kbd-keycode": "" if key.kbd_keycode is None else str(key.kbd_keycode),
        },
    )
    title = ET.SubElement(key_group, _tag("title"))
    title.text = f"{key.id}\nkbd_keycode: {'null' if key.kbd_keycode is None else key.kbd_keycode}"
    if key.outline is None and key.rotation is None:
        attributes = {
            "class": "key",
            "x": _number(key.x),
            "y": _number(key.y),
            "width": _number(key.w),
            "height": _number(key.h),
        }
        if key.corner_radius is not None:
            radius = _number(min(key.corner_radius, key.w / 2, key.h / 2))
            attributes["rx"] = radius
            attributes["ry"] = radius
        attributes.update(_key_style(key))
        ET.SubElement(
            key_group,
            _tag("rect"),
            attributes,
        )
        return

    points = " ".join(f"{_number(x)},{_number(y)}" for x, y in key.points())
    attributes = {"class": "key", "points": points}
    attributes.update(_key_style(key))
    ET.SubElement(key_group, _tag("polygon"), attributes)


def _render_key_id(parent: ET.Element, key: Key) -> None:
    attributes = {
        "class": "key-id",
        "x": _number(key.x + key.w - 0.08),
        "y": _number(key.y + 0.06),
        "text-anchor": "end",
        "dominant-baseline": "hanging",
    }
    attributes.update(_key_id_style(key))
    if key.rotation is not None:
        angle = _number(key.rotation.angle)
        origin_x = _number(key.rotation.origin[0])
        origin_y = _number(key.rotation.origin[1])
        attributes["transform"] = f"rotate({angle} {origin_x} {origin_y})"

    label = ET.SubElement(parent, _tag("text"), attributes)
    label.text = key.id


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _key_style(key: Key) -> dict[str, str]:
    if key.color is None:
        return {}
    colors = XKB_COLORS.get(key.color)
    if colors is None:
        return {}
    return {"style": f"--key-fill: {colors[0]}"}


def _key_id_style(key: Key) -> dict[str, str]:
    if key.color is None:
        return {}
    colors = XKB_COLORS.get(key.color)
    if colors is None:
        return {}
    return {"style": f"--key-id-fill: {colors[1]}"}


def _doodad_style(doodad: Doodad) -> dict[str, str]:
    if doodad.color is None:
        return {}
    colors = XKB_COLORS.get(doodad.color)
    if colors is None:
        return {}
    return {"style": f"--doodad-fill: {colors[0]}"}


def _number(value: float) -> str:
    if abs(value) < 1e-12:
        return "0"
    return format(value, ".12g")
