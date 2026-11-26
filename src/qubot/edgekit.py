"""Reusable helpers for a Qubot edge. Not an edge itself."""

import os
import tomllib
from pathlib import Path


def load_contract(edge_dir: Path) -> dict:
    """Load contracts/<version>.toml. CONTRACT_VERSION selects the file; otherwise the highest number."""
    directory = edge_dir / "contracts"
    version = os.environ.get("CONTRACT_VERSION")
    if version:
        path = directory / f"{version}.toml"
    else:
        paths = list(directory.glob("*.toml"))
        if not paths:
            raise FileNotFoundError(directory)
        path = max(paths, key=lambda item: int(item.stem))
    if not path.is_file():
        raise FileNotFoundError(path)
    data = tomllib.loads(path.read_text())
    if str(data.get("version")) != path.stem:
        raise ValueError(f"{path} version {data.get('version')} does not match its file name")
    return data


def require_filled_env(env_path: Path, values: dict[str, str]) -> None:
    """Raise if the local env file is missing or a required value is still blank."""
    if not env_path.is_file():
        raise FileNotFoundError(
            f"Refusing to start. Copy {env_path.parent / '.env.example'} to {env_path} and fill every placeholder."
        )
    empty = [name for name, value in values.items() if not str(value).strip()]
    if empty:
        raise ValueError(
            f"Refusing to start. Fill {', '.join(empty)} in {env_path}. Placeholders are not a running configuration."
        )


__all__ = ["load_contract", "require_filled_env"]
