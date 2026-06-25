"""Import normalized Linux kbd keymaps from loadkeys dumps."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable


KEYCODE_RE = re.compile(r"^keycode\s+(\d+)\s+=\s+(.*)$")


@dataclass(frozen=True)
class KeymapDump:
    """One symbolic or numeric loadkeys dump."""

    keymaps: tuple[int, ...]
    keys: dict[int, tuple[str, ...]]


def import_kbd_keymap(
    keymap_path: str | Path,
    *,
    loadkeys_path: str | Path = "external/kbd/src/loadkeys",
    keymaps_root: str | Path = "external/kbd/data/keymaps",
    tkeymap: int = 4,
) -> dict[str, Any]:
    """Compile one kbd keymap with loadkeys and return normalized JSON data."""
    keymap = Path(keymap_path)
    symbolic = parse_keymap_dump(_run_loadkeys(loadkeys_path, keymap, tkeymap=tkeymap, numeric=False))
    numeric = parse_keymap_dump(_run_loadkeys(loadkeys_path, keymap, tkeymap=tkeymap, numeric=True))
    return keymap_data(
        symbolic,
        numeric,
        keymap_id=_keymap_id(keymap, Path(keymaps_root)),
        source=_source_path(keymap, Path(keymaps_root)),
    )


def keymap_data(symbolic: KeymapDump, numeric: KeymapDump, *, keymap_id: str, source: str) -> dict[str, Any]:
    """Pair symbolic and numeric dumps into the public keymap document."""
    if symbolic.keymaps != numeric.keymaps:
        raise ValueError(f"keymap headers differ: {symbolic.keymaps!r} != {numeric.keymaps!r}")
    if symbolic.keys.keys() != numeric.keys.keys():
        raise ValueError("symbolic and numeric dumps contain different keycodes")

    keys = []
    for kbd_keycode in sorted(symbolic.keys):
        symbols = symbolic.keys[kbd_keycode]
        numeric_tokens = numeric.keys[kbd_keycode]
        if len(symbols) != len(symbolic.keymaps):
            raise ValueError(f"keycode {kbd_keycode}: symbolic dump has wrong entry count")
        if len(numeric_tokens) != len(symbolic.keymaps):
            raise ValueError(f"keycode {kbd_keycode}: numeric dump has wrong entry count")
        keys.append(
            {
                "kbd_keycode": kbd_keycode,
                "entries": [
                    _entry(keymap, symbol, numeric_token)
                    for keymap, symbol, numeric_token in zip(symbolic.keymaps, symbols, numeric_tokens, strict=True)
                ],
            }
        )

    return {
        "version": 1,
        "id": keymap_id,
        "source": source,
        "keymaps": list(symbolic.keymaps),
        "keys": keys,
    }


def parse_keymap_dump(text: str) -> KeymapDump:
    """Parse the keycode table produced by loadkeys --tkeymap."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty loadkeys dump")
    if not lines[0].startswith("keymaps "):
        raise ValueError("loadkeys dump does not start with a keymaps header")

    keymaps = _expand_keymaps(lines[0].removeprefix("keymaps "))
    keys: dict[int, tuple[str, ...]] = {}
    for line in lines[1:]:
        match = KEYCODE_RE.match(line)
        if match is None:
            continue
        kbd_keycode = int(match.group(1))
        values = tuple(match.group(2).split())
        if len(values) != len(keymaps):
            raise ValueError(
                f"keycode {kbd_keycode}: expected {len(keymaps)} entries, got {len(values)}"
            )
        if kbd_keycode in keys:
            raise ValueError(f"duplicate keycode {kbd_keycode}")
        keys[kbd_keycode] = values

    if not keys:
        raise ValueError("loadkeys dump does not contain keycode entries")
    return KeymapDump(keymaps=keymaps, keys=keys)


def write_keymap_json(
    keymap_path: str | Path,
    output_path: str | Path,
    *,
    loadkeys_path: str | Path = "external/kbd/src/loadkeys",
    keymaps_root: str | Path = "external/kbd/data/keymaps",
    tkeymap: int = 4,
) -> None:
    """Import one kbd keymap and write normalized JSON."""
    data = import_kbd_keymap(
        keymap_path,
        loadkeys_path=loadkeys_path,
        keymaps_root=keymaps_root,
        tkeymap=tkeymap,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{json.dumps(data, indent=2, ensure_ascii=False)}\n", encoding="utf-8")


def discover_keymaps(source_root: str | Path) -> tuple[Path, ...]:
    """Return importable .map files under source_root, excluding include directories."""
    root = Path(source_root)
    return tuple(
        sorted(
            path
            for path in root.rglob("*.map")
            if "include" not in path.relative_to(root).parts
        )
    )


def import_keymap_tree(
    source_root: str | Path,
    output_root: str | Path,
    *,
    loadkeys_path: str | Path = "external/kbd/src/loadkeys",
    keymaps_root: str | Path = "external/kbd/data/keymaps",
    tkeymap: int = 4,
) -> None:
    """Import all discovered keymaps and write a generated catalog."""
    source = Path(source_root)
    output = Path(output_root)
    keymaps_base = Path(keymaps_root)
    output.mkdir(parents=True, exist_ok=True)
    for generated in output.rglob("*.json"):
        generated.unlink()

    entries: list[dict[str, str]] = []
    errors: list[str] = []
    for keymap in discover_keymaps(source):
        keymap_id = _keymap_id(keymap, keymaps_base)
        relative_output = Path(f"{keymap_id}.json")
        output_path = output / relative_output
        try:
            write_keymap_json(
                keymap,
                output_path,
                loadkeys_path=loadkeys_path,
                keymaps_root=keymaps_base,
                tkeymap=tkeymap,
            )
        except ValueError as error:
            errors.append(f"{keymap}: {error}")
            continue

        entries.append(
            {
                "id": keymap_id,
                "name": keymap_id,
                "group": _keymap_group(keymap_id),
                "source": _source_path(keymap, keymaps_base),
                "json": relative_output.as_posix(),
            }
        )

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        raise ValueError(f"failed to import {len(errors)} keymap(s)")

    _write_keymap_catalog(output / "catalog.json", entries)


def keymap_catalog_data(entries: Iterable[dict[str, str]]) -> dict[str, Any]:
    """Return the public generated keymap catalog document."""
    return {
        "version": 1,
        "keymaps": list(entries),
    }


def _run_loadkeys(loadkeys_path: str | Path, keymap_path: Path, *, tkeymap: int, numeric: bool) -> str:
    environment = os.environ.copy()
    if numeric:
        environment["LK_DUMP_NUMERIC"] = "1"
    else:
        environment.pop("LK_DUMP_NUMERIC", None)

    result = subprocess.run(
        [str(loadkeys_path), "-u", f"--tkeymap={tkeymap}", str(keymap_path)],
        check=False,
        capture_output=True,
        env=environment,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode != 0:
        kind = "numeric" if numeric else "symbolic"
        raise ValueError(f"loadkeys {kind} dump failed for {keymap_path}: {stderr.strip()}")
    return stdout


def _entry(keymap: int, symbol: str, numeric_token: str) -> dict[str, Any]:
    return {
        "keymap": keymap,
        "symbol": symbol,
        "numeric": numeric_token,
        "numeric_value": _numeric_value(numeric_token),
        "has_plus_prefix": symbol.startswith("+") or numeric_token.startswith("+"),
    }


def _numeric_value(token: str) -> int:
    token = token.removeprefix("+")
    if token.startswith("U+"):
        return int(token[2:], 16)
    return int(token, 0)


def _expand_keymaps(value: str) -> tuple[int, ...]:
    keymaps: list[int] = []
    for item in value.split(","):
        if "-" in item:
            start, end = item.split("-", 1)
            keymaps.extend(range(int(start), int(end) + 1))
        else:
            keymaps.append(int(item))
    if not keymaps:
        raise ValueError("keymaps header is empty")
    return tuple(keymaps)


def _keymap_id(path: Path, root: Path) -> str:
    relative = _relative_path(path, root)
    if relative.endswith(".map"):
        relative = relative.removesuffix(".map")
    return relative


def _source_path(path: Path, root: Path) -> str:
    return _relative_path(path, root)


def _keymap_group(keymap_id: str) -> str:
    parts = keymap_id.split("/")
    if len(parts) >= 3:
        return parts[1]
    return "Other"


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        try:
            return path.absolute().relative_to(root.absolute()).as_posix()
        except ValueError:
            return path.as_posix()


def _write_keymap_catalog(path: Path, entries: list[dict[str, str]]) -> None:
    data = keymap_catalog_data(entries)
    path.write_text(f"{json.dumps(data, indent=2, ensure_ascii=False)}\n", encoding="utf-8")
