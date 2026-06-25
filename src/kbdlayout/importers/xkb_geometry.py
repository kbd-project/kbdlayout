"""Import legacy XKB geometry definitions using the evdev keycode set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any

from ..model import NR_KEYS


EVDEV_OFFSET = 8
STANDARD_KEY_WIDTH = 18.0
_TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|<[A-Za-z0-9_]+>|[A-Za-z_][A-Za-z0-9_]*|[-+]?(?:\d+\.\d*|\.\d+|\d+)|[{}\[\]=;,.]', re.DOTALL)


class XkbGeometryError(ValueError):
    """Raised when an XKB geometry cannot be imported."""


@dataclass(frozen=True)
class Shape:
    x: float
    y: float
    width: float
    height: float
    outline: tuple[tuple[float, float], ...] | None


def import_xkb_geometry(
    geometry_path: str | Path,
    keycodes_path: str | Path,
    geometry_name: str,
    *,
    model_id: str,
    name: str | None = None,
    fallback_keycodes_paths: tuple[str | Path, ...] = (),
) -> dict[str, Any]:
    """Convert one XKB geometry and evdev keycode map into canonical JSON."""
    geometry_path = Path(geometry_path)
    keycodes_path = Path(keycodes_path)
    geometry = _parse_geometry(geometry_path, geometry_name)
    keycodes = _parse_xkb_keycodes(keycodes_path.read_text(encoding="utf-8"))
    for fallback_path in fallback_keycodes_paths:
        fallback = _parse_xkb_keycodes(Path(fallback_path).read_text(encoding="utf-8"))
        keycodes = {**fallback, **keycodes}
    keys, groups = _keys_from_geometry(geometry, keycodes)
    return {
        "version": 1,
        "id": model_id,
        "name": name or geometry_name,
        "unit": "u",
        "keys": keys,
        "groups": groups,
        "extensions": {
            "xkb": {
                "geometry": geometry_name,
                "geometry_file": geometry_path.name,
                "keycodes_file": keycodes_path.name,
                "evdev_offset": EVDEV_OFFSET,
            }
        },
    }


def _parse_geometry(path: Path, name: str, stack: set[tuple[Path, str]] | None = None) -> dict[str, Any]:
    path = path.resolve()
    stack = set() if stack is None else stack
    identity = (path, name)
    if identity in stack:
        raise XkbGeometryError(f"cyclic geometry include: {path}({name})")
    stack.add(identity)
    tokens = _tokens(path.read_text(encoding="utf-8"))
    for index in range(len(tokens) - 2):
        if tokens[index] == "xkb_geometry" and _string(tokens[index + 1]) == name and tokens[index + 2] == "{":
            body, _ = _block(tokens, index + 2)
            try:
                return _parse_geometry_body(body, path.parent, stack)
            finally:
                stack.remove(identity)
    stack.remove(identity)
    raise XkbGeometryError(f"geometry {name!r} not found")


def _parse_geometry_body(tokens: list[str], geometry_dir: Path, stack: set[tuple[Path, str]]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "section.left": 0.0,
        "row.left": 0.0,
        "key.shape": None,
        "key.gap": 0.0,
        "key.color": None,
    }
    shapes: dict[str, Shape] = {}
    sections: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "shape" and index + 2 < len(tokens) and tokens[index + 2] == "{":
            shape_name = _string(tokens[index + 1])
            body, index = _block(tokens, index + 2)
            shapes[shape_name] = _parse_shape(body)
        elif token == "section" and index + 2 < len(tokens) and tokens[index + 2] == "{":
            section_name = _string(tokens[index + 1])
            body, index = _block(tokens, index + 2)
            sections.append(_parse_section(section_name, body, defaults))
        elif token == "include" and index + 1 < len(tokens):
            included_path, included_name = _include_target(_string(tokens[index + 1]), geometry_dir)
            included = _parse_geometry(included_path, included_name, stack)
            defaults.update(included["defaults"])
            shapes.update(included["shapes"])
            sections.extend(included["sections"])
            index += 2
        else:
            statement, index = _statement(tokens, index)
            assignment = _assignment(statement)
            if assignment and assignment[0] in defaults:
                defaults[assignment[0]] = assignment[1]
    return {"defaults": defaults, "shapes": shapes, "sections": sections}


def _parse_shape(tokens: list[str]) -> Shape:
    index = 0
    while index < len(tokens):
        if tokens[index] == "{":
            outline, _ = _block(tokens, index)
            points = _points(outline)
            if not points:
                raise XkbGeometryError("shape has no outline points")
            if len(points) == 1:
                width, height = points[0]
                return Shape(x=0.0, y=0.0, width=width, height=height, outline=None)
            min_x = min(x for x, _ in points)
            min_y = min(y for _, y in points)
            max_x = max(x for x, _ in points)
            max_y = max(y for _, y in points)
            normalized = tuple((x - min_x, y - min_y) for x, y in points)
            return Shape(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y, outline=normalized)
        index += 1
    raise XkbGeometryError("shape has no outline")


def _parse_section(name: str, tokens: list[str], defaults: dict[str, Any]) -> dict[str, Any]:
    values = dict(defaults)
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        if tokens[index:index + 2] == ["row", "{"]:
            body, index = _block(tokens, index + 1)
            rows.append(_parse_row(body, values))
        else:
            statement, index = _statement(tokens, index)
            assignment = _assignment(statement)
            if assignment:
                values[assignment[0]] = assignment[1]
    return {"name": name, "left": values.get("left", values["section.left"]), "top": values.get("top", 0.0), "rows": rows}


def _parse_row(tokens: list[str], section_defaults: dict[str, Any]) -> dict[str, Any]:
    values = {
        "left": section_defaults["row.left"],
        "top": 0.0,
        "key.shape": section_defaults["key.shape"],
        "key.gap": section_defaults["key.gap"],
        "key.color": section_defaults.get("key.color"),
    }
    keys: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        if tokens[index:index + 2] == ["keys", "{"]:
            body, index = _block(tokens, index + 1)
            keys = _parse_keys(body, values)
        else:
            statement, index = _statement(tokens, index)
            assignment = _assignment(statement)
            if assignment:
                values[assignment[0]] = assignment[1]
    return {"left": values["left"], "top": values["top"], "keys": keys}


def _parse_keys(tokens: list[str], defaults: dict[str, Any]) -> list[dict[str, Any]]:
    keys: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("<"):
            keys.append(
                {
                    "name": token[1:-1],
                    "shape": defaults["key.shape"],
                    "gap": defaults["key.gap"],
                    "color": defaults.get("key.color"),
                }
            )
            index += 1
        elif token == "{":
            body, index = _block(tokens, index)
            key = _parse_key_entry(body, defaults)
            if key is not None:
                keys.append(key)
        else:
            index += 1
    return keys


def _parse_key_entry(tokens: list[str], defaults: dict[str, Any]) -> dict[str, Any] | None:
    key_index = next((index for index, token in enumerate(tokens) if token.startswith("<")), None)
    if key_index is None:
        return None
    name = tokens[key_index][1:-1]
    shape = defaults["key.shape"]
    gap = defaults["key.gap"]
    color = defaults.get("key.color")
    index = key_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token == "shape" and index + 2 < len(tokens) and tokens[index + 1] == "=":
            shape = _string(tokens[index + 2])
            index += 3
            continue
        if tokens[index:index + 4] == ["key", ".", "shape", "="] and index + 4 < len(tokens):
            shape = _string(tokens[index + 4])
            index += 5
            continue
        if token == "gap" and index + 2 < len(tokens) and tokens[index + 1] == "=":
            gap = float(tokens[index + 2])
            index += 3
            continue
        if tokens[index:index + 4] == ["key", ".", "gap", "="] and index + 4 < len(tokens):
            gap = float(tokens[index + 4])
            index += 5
            continue
        if token == "color" and index + 2 < len(tokens) and tokens[index + 1] == "=":
            color = _string(tokens[index + 2])
            index += 3
            continue
        if tokens[index:index + 4] == ["key", ".", "color", "="] and index + 4 < len(tokens):
            color = _string(tokens[index + 4])
            index += 5
            continue
        if token == "=":
            index += 2
            continue
        if token.startswith('"'):
            shape = _string(token)
        elif _is_number(token):
            gap = float(token)
        index += 1
    return {"name": name, "shape": shape, "gap": gap, "color": color}


def _keys_from_geometry(geometry: dict[str, Any], keycodes: dict[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shapes: dict[str, Shape] = geometry["shapes"]
    keys: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for section in geometry["sections"]:
        offset_y = float(section["top"])
        group_keys: list[str] = []
        for row in section["rows"]:
            offset_x = float(section["left"]) + float(row["left"])
            for entry in row["keys"]:
                shape_name = entry["shape"]
                if shape_name not in shapes:
                    raise XkbGeometryError(f"key {entry['name']!r} refers to unknown shape {shape_name!r}")
                shape = shapes[shape_name]
                offset_x += float(entry["gap"])
                key_name = entry["name"]
                kbd_keycode = keycodes.get(key_name)
                if kbd_keycode is None:
                    print(f"warning: {key_name}: no kernel keycode mapping; kbd legends will be unavailable", file=sys.stderr)
                elif kbd_keycode >= NR_KEYS:
                    print(f"warning: {key_name}: kernel keycode {kbd_keycode} is outside NR_KEYS={NR_KEYS}; kbd legends will be unavailable", file=sys.stderr)
                key = {
                    "id": key_name,
                    "kbd_keycode": kbd_keycode,
                    "x": _units(offset_x + shape.x),
                    "y": _units(offset_y + float(row["top"]) + shape.y),
                    "w": _units(shape.width),
                    "h": _units(shape.height),
                }
                if entry["color"] is not None:
                    key["color"] = entry["color"]
                if shape.outline is not None:
                    key["outline"] = [[_units(x), _units(y)] for x, y in shape.outline]
                keys.append(key)
                group_keys.append(key_name)
                offset_x += shape.width
        groups.append({"id": _group_id(section["name"]), "key_ids": group_keys})
    return keys, groups


def _parse_xkb_keycodes(source: str) -> dict[str, int]:
    values: dict[str, int | str] = {}
    for name, value in re.findall(r"<([A-Za-z0-9_]+)>\s*=\s*(-?\d+)\s*;", source):
        values[name] = int(value)
    for name, target in re.findall(r"alias\s+<([A-Za-z0-9_]+)>\s*=\s*<([A-Za-z0-9_]+)>\s*;", source):
        values[name] = target

    def resolve(name: str, seen: set[str] | None = None) -> int:
        value = values.get(name)
        if isinstance(value, int):
            return value
        if not isinstance(value, str):
            raise XkbGeometryError(f"evdev keycode for {name!r} not found")
        seen = set() if seen is None else seen
        if name in seen:
            raise XkbGeometryError(f"cyclic evdev alias for {name!r}")
        seen.add(name)
        return resolve(value, seen)

    return {name: resolve(name) - EVDEV_OFFSET for name in values}


def _tokens(source: str) -> list[str]:
    return [match.group(0) for match in _TOKEN.finditer(source) if not match.group(0).startswith(("//", "/*"))]


def _block(tokens: list[str], start: int) -> tuple[list[str], int]:
    if tokens[start] != "{":
        raise XkbGeometryError("expected block")
    depth = 1
    index = start + 1
    while index < len(tokens) and depth:
        if tokens[index] == "{":
            depth += 1
        elif tokens[index] == "}":
            depth -= 1
        index += 1
    if depth:
        raise XkbGeometryError("unterminated block")
    return tokens[start + 1:index - 1], index


def _statement(tokens: list[str], start: int) -> tuple[list[str], int]:
    index = start
    while index < len(tokens) and tokens[index] != ";":
        if tokens[index] == "{":
            _, index = _block(tokens, index)
        else:
            index += 1
    return tokens[start:index], index + 1


def _assignment(tokens: list[str]) -> tuple[str, Any] | None:
    if "=" not in tokens:
        return None
    equal = tokens.index("=")
    name = "".join(tokens[:equal])
    value = tokens[equal + 1] if equal + 1 < len(tokens) else None
    if value is None:
        return None
    if _is_number(value):
        return name, float(value)
    return name, _string(value)


def _points(tokens: list[str]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    index = 0
    while index < len(tokens):
        if tokens[index] == "[" and index + 4 < len(tokens) and tokens[index + 2] == "," and tokens[index + 4] == "]":
            points.append((float(tokens[index + 1]), float(tokens[index + 3])))
            index += 5
        else:
            index += 1
    return points


def _is_number(value: str) -> bool:
    return bool(re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)", value))


def _string(value: str) -> str:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def _units(value: float) -> float:
    return value / STANDARD_KEY_WIDTH


def _group_id(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", name).lower()


def _include_target(value: str, geometry_dir: Path) -> tuple[Path, str]:
    match = re.fullmatch(r"([A-Za-z0-9_./-]+)\(([A-Za-z0-9_.-]+)\)", value)
    if match is None:
        raise XkbGeometryError(f"unsupported geometry include {value!r}")
    filename, geometry_name = match.groups()
    return geometry_dir / filename, geometry_name
