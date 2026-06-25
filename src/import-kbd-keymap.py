#!/usr/bin/env python3
"""Import one Linux kbd keymap into normalized JSON."""

import argparse

from kbdlayout.keymap import write_keymap_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Import one Linux kbd keymap.")
    parser.add_argument("keymap", help="Path to the source .map file.")
    parser.add_argument("output", help="Path to the generated keymap JSON file.")
    parser.add_argument(
        "--loadkeys",
        default="external/kbd/src/loadkeys",
        help="Path to the kbd loadkeys binary (default: external/kbd/src/loadkeys).",
    )
    parser.add_argument(
        "--keymaps-root",
        default="external/kbd/data/keymaps",
        help="Root used for generated keymap ids (default: external/kbd/data/keymaps).",
    )
    parser.add_argument(
        "--tkeymap",
        type=int,
        default=4,
        help="loadkeys --tkeymap value (default: 4).",
    )
    args = parser.parse_args()

    try:
        write_keymap_json(
            args.keymap,
            args.output,
            loadkeys_path=args.loadkeys,
            keymaps_root=args.keymaps_root,
            tkeymap=args.tkeymap,
        )
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
