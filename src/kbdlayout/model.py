"""Loading, validation, and geometry operations for physical models."""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import cos, radians, sin
from pathlib import Path
from typing import Any, Iterable, Mapping


class ModelError(ValueError):
    """Raised when a physical model cannot be loaded or is invalid."""


Point = tuple[float, float]


@dataclass(frozen=True)
class Bounds:
    """An axis-aligned bounding box in keyboard units."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Rotation:
    """A clockwise SVG rotation around an absolute point."""

    angle: float
    origin: Point


@dataclass(frozen=True)
class Key:
    """One physical key and its mapping to a Linux console keycode."""

    id: str
    linux_keycode: int
    x: float
    y: float
    w: float
    h: float
    outline: tuple[Point, ...] | None = None
    rotation: Rotation | None = None

    def points(self) -> tuple[Point, ...]:
        """Return the key outline in global coordinates after rotation."""
        local_points = self.outline or (
            (0.0, 0.0),
            (self.w, 0.0),
            (self.w, self.h),
            (0.0, self.h),
        )
        points = tuple((self.x + x, self.y + y) for x, y in local_points)
        if self.rotation is None:
            return points

        angle = radians(self.rotation.angle)
        cosine = cos(angle)
        sine = sin(angle)
        origin_x, origin_y = self.rotation.origin
        return tuple(
            (
                origin_x + cosine * (x - origin_x) - sine * (y - origin_y),
                origin_y + sine * (x - origin_x) + cosine * (y - origin_y),
            )
            for x, y in points
        )

    def bounds(self) -> Bounds:
        """Return the bounds of the rotated key outline."""
        points = self.points()
        xs, ys = zip(*points, strict=True)
        x = min(xs)
        y = min(ys)
        return Bounds(x=x, y=y, w=max(xs) - x, h=max(ys) - y)


@dataclass(frozen=True)
class Group:
    """A named, non-geometric collection of physical keys."""

    id: str
    key_ids: tuple[str, ...]


@dataclass(frozen=True)
class Model:
    """A validated physical keyboard model."""

    id: str
    keys: tuple[Key, ...]
    name: str | None = None
    groups: tuple[Group, ...] = ()

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> Model:
        """Build a model from decoded canonical physical-model JSON."""
        _expect_object(data, "model")
        _reject_unknown(data, {"version", "id", "name", "unit", "keys", "groups", "extensions"}, "model")
        if data.get("version") != 1:
            raise ModelError("model.version must be 1")
        if data.get("unit") != "u":
            raise ModelError('model.unit must be "u"')

        model_id = _id(data.get("id"), "model.id")
        name = data.get("name")
        if name is not None and (not isinstance(name, str) or not name):
            raise ModelError("model.name must be a non-empty string")

        raw_keys = _list(data.get("keys"), "model.keys")
        if not raw_keys:
            raise ModelError("model.keys must not be empty")
        keys = tuple(_key(raw_key, f"model.keys[{index}]") for index, raw_key in enumerate(raw_keys))
        _unique((key.id for key in keys), "key ID")
        _unique((key.linux_keycode for key in keys), "Linux keycode")

        raw_groups = _list(data.get("groups", []), "model.groups")
        groups = tuple(_group(raw_group, f"model.groups[{index}]") for index, raw_group in enumerate(raw_groups))
        _unique((group.id for group in groups), "group ID")
        key_ids = {key.id for key in keys}
        for group in groups:
            unknown = set(group.key_ids) - key_ids
            if unknown:
                raise ModelError(f"group {group.id!r} references unknown keys: {sorted(unknown)!r}")

        return cls(id=model_id, name=name, keys=keys, groups=groups)

    def key(self, key_id: str) -> Key:
        """Look up a physical key by its stable identifier."""
        for key in self.keys:
            if key.id == key_id:
                return key
        raise KeyError(key_id)

    def keycode(self, linux_keycode: int) -> Key:
        """Look up a physical key by its Linux console keycode."""
        for key in self.keys:
            if key.linux_keycode == linux_keycode:
                return key
        raise KeyError(linux_keycode)

    def bounds(self) -> Bounds:
        """Return the bounding box that encloses all physical keys."""
        key_bounds = tuple(key.bounds() for key in self.keys)
        x = min(bounds.x for bounds in key_bounds)
        y = min(bounds.y for bounds in key_bounds)
        right = max(bounds.x + bounds.w for bounds in key_bounds)
        bottom = max(bounds.y + bounds.h for bounds in key_bounds)
        return Bounds(x=x, y=y, w=right - x, h=bottom - y)


def load_model(path: str | Path) -> Model:
    """Load and validate a canonical physical-model JSON file."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ModelError(f"cannot read model {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ModelError(f"cannot parse model {path}: {error}") from error
    return Model.from_data(data)


def _key(value: Any, path: str) -> Key:
    _expect_object(value, path)
    _reject_unknown(value, {"id", "linux_keycode", "x", "y", "w", "h", "rotation", "outline", "extensions"}, path)
    key = Key(
        id=_id(value.get("id"), f"{path}.id"),
        linux_keycode=_integer(value.get("linux_keycode"), f"{path}.linux_keycode", minimum=1, maximum=255),
        x=_number(value.get("x"), f"{path}.x"),
        y=_number(value.get("y"), f"{path}.y"),
        w=_number(value.get("w"), f"{path}.w"),
        h=_number(value.get("h"), f"{path}.h"),
        outline=_outline(value.get("outline"), path) if "outline" in value else None,
        rotation=_rotation(value.get("rotation"), path) if "rotation" in value else None,
    )
    if key.w <= 0 or key.h <= 0:
        raise ModelError(f"{path}.w and {path}.h must be greater than zero")
    if key.outline is not None:
        for x, y in key.outline:
            if not 0 <= x <= key.w or not 0 <= y <= key.h:
                raise ModelError(f"{path}.outline point ({x}, {y}) is outside the key bounds")
    return key


def _group(value: Any, path: str) -> Group:
    _expect_object(value, path)
    _reject_unknown(value, {"id", "key_ids"}, path)
    key_ids = tuple(_id(item, f"{path}.key_ids") for item in _list(value.get("key_ids"), f"{path}.key_ids"))
    if not key_ids:
        raise ModelError(f"{path}.key_ids must not be empty")
    _unique(key_ids, f"{path} key ID")
    return Group(id=_id(value.get("id"), f"{path}.id"), key_ids=key_ids)


def _rotation(value: Any, path: str) -> Rotation:
    _expect_object(value, f"{path}.rotation")
    _reject_unknown(value, {"angle", "origin"}, f"{path}.rotation")
    origin = _point(value.get("origin"), f"{path}.rotation.origin")
    return Rotation(angle=_number(value.get("angle"), f"{path}.rotation.angle"), origin=origin)


def _outline(value: Any, path: str) -> tuple[Point, ...]:
    outline = tuple(_point(point, f"{path}.outline") for point in _list(value, f"{path}.outline"))
    if len(outline) < 3:
        raise ModelError(f"{path}.outline must have at least three points")
    return outline


def _point(value: Any, path: str) -> Point:
    values = _list(value, path)
    if len(values) != 2:
        raise ModelError(f"{path} must contain exactly two coordinates")
    return (_number(values[0], f"{path}[0]"), _number(values[1], f"{path}[1]"))


def _id(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value or not value[0].isalpha() or not all(character.isalnum() or character in "_-" for character in value):
        raise ModelError(f"{path} must start with a letter and contain only letters, numbers, underscores, or hyphens")
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelError(f"{path} must be a number")
    return float(value)


def _integer(value: Any, path: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ModelError(f"{path} must be an integer between {minimum} and {maximum}")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ModelError(f"{path} must be an array")
    return value


def _expect_object(value: Any, path: str) -> None:
    if not isinstance(value, Mapping):
        raise ModelError(f"{path} must be an object")


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], path: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ModelError(f"{path} contains unknown fields: {sorted(unknown)!r}")


def _unique(values: Iterable[str | int], description: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise ModelError(f"duplicate {description}")
