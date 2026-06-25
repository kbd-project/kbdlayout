"""Static SVG rendering for physical keyboard models."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from .model import Key, Model


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


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
        ".key { fill: #eee; stroke: #777; stroke-width: 0.03; }"
        ".key-id { fill: #555; font: 0.16px sans-serif; pointer-events: none; }"
    )

    geometry = ET.SubElement(svg, _tag("g"), {"id": "keyboard-geometry"})
    keys = ET.SubElement(geometry, _tag("g"), {"id": "keys"})
    for key in model.keys:
        _render_key(keys, key)

    factory_legends = ET.SubElement(svg, _tag("g"), {"id": "factory-legends"})
    for key in model.keys:
        _render_key_id(factory_legends, key)
    ET.SubElement(svg, _tag("g"), {"id": "overlay-legends"})
    return ET.tostring(svg, encoding="unicode", xml_declaration=True)


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
        ET.SubElement(
            key_group,
            _tag("rect"),
            {
                "class": "key",
                "x": _number(key.x),
                "y": _number(key.y),
                "width": _number(key.w),
                "height": _number(key.h),
            },
        )
        return

    points = " ".join(f"{_number(x)},{_number(y)}" for x, y in key.points())
    ET.SubElement(key_group, _tag("polygon"), {"class": "key", "points": points})


def _render_key_id(parent: ET.Element, key: Key) -> None:
    attributes = {
        "class": "key-id",
        "x": _number(key.x + key.w - 0.08),
        "y": _number(key.y + 0.06),
        "text-anchor": "end",
        "dominant-baseline": "hanging",
    }
    if key.rotation is not None:
        angle = _number(key.rotation.angle)
        origin_x = _number(key.rotation.origin[0])
        origin_y = _number(key.rotation.origin[1])
        attributes["transform"] = f"rotate({angle} {origin_x} {origin_y})"

    label = ET.SubElement(parent, _tag("text"), attributes)
    label.text = key.id


def _tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def _number(value: float) -> str:
    if abs(value) < 1e-12:
        return "0"
    return format(value, ".12g")
