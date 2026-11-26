"""Copy a user-supplied .env into one site edge directory.

The example file stays placeholders. The copy is local and must stay gitignored.
This does not start an edge.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def copy_env(edge: Path, source: Path) -> Path:
    edge = edge.resolve()
    source = source.resolve()
    if not edge.is_dir():
        raise SystemExit(f"missing edge directory {edge}")
    if not source.is_file():
        raise SystemExit(f"missing env file {source}")
    if source.name == ".env.example":
        raise SystemExit("refusing to copy .env.example")
    destination = edge / ".env"
    shutil.copyfile(source, destination)
    destination.chmod(0o600)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edge", type=Path, help="Site edge directory")
    parser.add_argument("env_file", type=Path)
    args = parser.parse_args()
    destination = copy_env(args.edge, args.env_file)
    print(f"copied env to {destination}")


if __name__ == "__main__":
    main()
