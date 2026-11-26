"""Reusable helpers for a Qubot edge. Not an edge itself."""

from pathlib import Path


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


__all__ = ["require_filled_env"]
