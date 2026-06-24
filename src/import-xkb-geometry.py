#!/usr/bin/env python3
"""Import one XKB geometry into a canonical kbdlayout model."""

import argparse
import json
from pathlib import Path

from kbdlayout.importers.xkb_geometry import XkbGeometryError, import_xkb_geometry


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an XKB geometry using evdev keycodes.")
    parser.add_argument("geometry", help="Name of the xkb_geometry block to import.")
    parser.add_argument("output", type=Path, help="Output canonical model JSON.")
    parser.add_argument("--model-id", required=True, help="Canonical model identifier.")
    parser.add_argument("--name", help="Human-readable model name.")
    parser.add_argument("--geometry-file", type=Path, default=Path("external/xkeyboard-config/geometry/pc"))
    parser.add_argument("--keycodes-file", type=Path, default=Path("external/xkeyboard-config/keycodes/evdev"))
    parser.add_argument("--fallback-keycodes-file", type=Path, action="append", default=[Path("external/xkeyboard-config/keycodes/xfree86")])
    args = parser.parse_args()
    try:
        model = import_xkb_geometry(
            args.geometry_file,
            args.keycodes_file,
            args.geometry,
            model_id=args.model_id,
            name=args.name,
            fallback_keycodes_paths=tuple(args.fallback_keycodes_file),
        )
    except (OSError, XkbGeometryError) as error:
        parser.error(str(error))
    args.output.write_text(f"{json.dumps(model, indent=2)}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
