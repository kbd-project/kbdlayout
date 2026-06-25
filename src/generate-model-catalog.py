#!/usr/bin/env python3
"""Generate a public JSON model catalog from models/catalog.tsv."""

import argparse

from kbdlayout.catalog import write_catalog_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a JSON catalog for physical keyboard models.")
    parser.add_argument("catalog", help="Path to the source TSV model catalog.")
    parser.add_argument("output", help="Path to the generated JSON catalog.")
    args = parser.parse_args()

    try:
        write_catalog_json(args.catalog, args.output)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
