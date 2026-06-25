#!/usr/bin/env python3
"""Generate normalized JSON for a tree of Linux kbd keymaps."""

import argparse

from kbdlayout.keymap import import_keymap_tree


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate JSON fixtures for Linux kbd keymaps.")
    parser.add_argument("source_root", help="Root directory to scan for .map files.")
    parser.add_argument("output_root", help="Directory for generated keymap JSON files.")
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
        import_keymap_tree(
            args.source_root,
            args.output_root,
            loadkeys_path=args.loadkeys,
            keymaps_root=args.keymaps_root,
            tkeymap=args.tkeymap,
        )
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
