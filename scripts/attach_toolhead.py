"""Attach a toolhead by writing the next contract and refreshing vendor/.

Older contracts stay in place. This does not build an image, remove an image,
or start a container. Rebuild the site edge separately, and do not point this
at an edge that is running.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def contract_paths(edge: Path) -> list[Path]:
    directory = edge / "contracts"
    return sorted(directory.glob("*.toml"), key=lambda item: int(item.stem))


def parse_set(item: str):
    key, separator, raw = item.partition("=")
    if not separator or not key:
        raise SystemExit(f"--set expects key=value, got {item}")
    if raw in ("true", "false"):
        value = raw
    else:
        try:
            number = float(raw) if "." in raw else int(raw)
            value = str(number) if isinstance(number, float) else str(number)
        except ValueError:
            value = f'"{raw}"'
    return key, value


def rewrite(text: str, version: str, effectors: list[str], sets: dict[str, str]) -> str:
    text = re.sub(r'(?m)^version = .*$', f'version = "{version}"', text, count=1)
    rendered = "effectors = [" + ", ".join(f'"{item}"' for item in effectors) + "]"
    text = re.sub(r'(?m)^effectors = .*$', rendered, text, count=1)
    for key, value in sets.items():
        pattern = rf'(?m)^{re.escape(key)} = .*$'
        replacement = f"{key} = {value}"
        text, count = re.subn(pattern, replacement, text, count=1)
        if count == 0:
            text = text.rstrip() + f"\n{replacement}\n"
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edge", type=Path, help="Site edge directory")
    parser.add_argument("effector", help="End-effector package name, for example a-axis-capper")
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        help="Extra contract field, key=value. Repeat for more than one.",
    )
    parser.add_argument(
        "--env",
        type=Path,
        help="User-supplied .env to copy into the edge. Omit it and the edge will not start.",
    )
    args = parser.parse_args()
    edge = args.edge.resolve()
    effector_dir = ROOT / "end-effectors" / args.effector
    if not effector_dir.is_dir():
        raise SystemExit(f"unknown effector {args.effector}")
    existing = contract_paths(edge)
    if not existing:
        raise SystemExit(f"{edge} has no contracts")
    current = existing[-1]
    data = tomllib.loads(current.read_text())
    effectors = list(data.get("effectors", []))
    if args.effector in effectors:
        raise SystemExit(f"{args.effector} is already on contract {current.stem}")
    effectors.append(args.effector)
    new_version = str(int(current.stem) + 1)
    sets = dict(parse_set(item) for item in args.set)
    if args.effector == "autosampler-syringe" and "syringe_length_mm" not in sets:
        raise SystemExit("autosampler-syringe requires --set syringe_length_mm=<millimetres>")
    destination = current.parent / f"{new_version}.toml"
    destination.write_text(rewrite(current.read_text(), new_version, effectors, sets))
    print(f"wrote {destination}")
    if args.env is not None:
        from accept_host_env import copy_env

        copy_env(edge, args.env)
    from vendor_edge import vendor

    vendor(destination, edge)
    print(f"vendored contract {new_version}; image rebuild was not run")


if __name__ == "__main__":
    main()
