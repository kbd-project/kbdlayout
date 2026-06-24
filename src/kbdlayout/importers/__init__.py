"""Adapters that import external keyboard descriptions into canonical models."""

from .xkb_geometry import EVDEV_OFFSET, import_xkb_geometry

__all__ = ["EVDEV_OFFSET", "import_xkb_geometry"]
