#!/usr/bin/env python3
"""Render a kbdlayout physical model as SVG."""

import argparse

from kbdlayout import ModelError, load_model
from kbdlayout.svg import render_svg


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a physical keyboard model as SVG.")
    parser.add_argument("model", help="Path to a physical-model JSON file.")
    parser.add_argument("--scale", type=float, default=60, help="Pixels per keyboard unit (default: 60).")
    parser.add_argument("--padding", type=float, default=0.1, help="Outer padding in keyboard units (default: 0.1).")
    args = parser.parse_args()

    try:
        model = load_model(args.model)
        print(render_svg(model, scale=args.scale, padding=args.padding))
    except (ModelError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
