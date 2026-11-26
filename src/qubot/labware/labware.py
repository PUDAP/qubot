"""Labware definitions: plates, tip racks, and bins with well positions.

Definitions are Opentrons-style JSON files (``wells``, ``ordering``,
``dimensions``, plus qubot's ``insert_depth``). qubot bundles a few in
``qubot/labware/definitions/``. An edge adds its own by passing folders that
hold more ``<name>.json`` files, or by passing a definition dict directly::

    from qubot.labware import StandardLabware

    plate = StandardLabware("my_plate", search_paths=[EDGE_DIR / "labware"])
    custom = StandardLabware.from_definition("my_plate", definition_dict)

Search order: ``search_paths`` in the order given, then the folder of a
``StandardLabware`` subclass's module (when subclassed), then the bundled
definitions. An edge definition with the same name as a bundled one wins.
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from ..geometry import Position

BUNDLED_DIR = Path(__file__).resolve().parent / "definitions"

PathLike = Union[str, Path]


def _definition_dirs(search_paths: Iterable[PathLike] = (), owner: Optional[type] = None) -> list[Path]:
    dirs = [Path(path) for path in search_paths]
    if owner is not None and owner is not StandardLabware:
        dirs.append(Path(inspect.getfile(owner)).resolve().parent)
    dirs.append(BUNDLED_DIR)
    return dirs


def find_definition(name: str, search_paths: Iterable[PathLike] = ()) -> Path:
    """Path of ``<name>.json`` in the first folder that has it.

    Raises:
        FileNotFoundError: If no folder holds that definition.
    """
    dirs = _definition_dirs(search_paths)
    for directory in dirs:
        candidate = directory / f"{name}.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Labware definition '{name}.json' not found in {[str(d) for d in dirs]}")


def _rows_and_cols(definition: Dict[str, Any]) -> Dict[str, List[str]]:
    rows: set[str] = set()
    cols: set[str] = set()
    for column in definition.get("ordering", []):
        for well_id in column:
            match = re.match(r"([A-Z]+)(\d+)", well_id)
            if match:
                rows.add(match.group(1))
                cols.add(match.group(2))
    return {"rows": sorted(rows), "cols": sorted(cols, key=int)}


def get_available_labware(search_paths: Sequence[PathLike] = ()) -> Dict[str, Dict[str, List[str]]]:
    """Labware names with their row and column labels, from every search folder.

    The bundled definitions are always included. A name found in an earlier
    folder hides the same name in a later one.
    """
    result: Dict[str, Dict[str, List[str]]] = {}
    for directory in _definition_dirs(search_paths):
        if not directory.is_dir():
            continue
        for json_file in sorted(directory.glob("*.json")):
            if json_file.stem in result:
                continue
            try:
                definition = json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            result[json_file.stem] = _rows_and_cols(definition)
    return dict(sorted(result.items()))


class StandardLabware:
    """One piece of labware and its well positions, relative to the labware origin."""

    def __init__(
        self,
        labware_name: str,
        *,
        search_paths: Sequence[PathLike] = (),
        definition: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            labware_name: Definition name, the JSON file name without ``.json``.
            search_paths: Edge folders searched before the bundled definitions.
            definition: A definition dict to use instead of searching for a file.

        Raises:
            FileNotFoundError: If no folder holds the definition.
        """
        self.name = labware_name
        if definition is None:
            definition = self.load_definition(labware_name, search_paths=search_paths)
        self._definition = definition
        self.display_name = definition.get("metadata", {}).get("displayName", "displayName not found")
        self._wells = definition.get("wells", {})

    @classmethod
    def from_definition(cls, labware_name: str, definition: Dict[str, Any]) -> "StandardLabware":
        """Labware from a definition dict the edge built or loaded itself."""
        return cls(labware_name, definition=definition)

    @classmethod
    def from_file(cls, path: PathLike) -> "StandardLabware":
        """Labware from one JSON file. The name is the file name without ``.json``."""
        path = Path(path)
        return cls(path.stem, definition=json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def get_available_labware(search_paths: Sequence[PathLike] = ()) -> Dict[str, Dict[str, List[str]]]:
        """See :func:`qubot.labware.get_available_labware`."""
        return get_available_labware(search_paths)

    def load_definition(self, labware_name: str, *, search_paths: Sequence[PathLike] = ()) -> Dict[str, Any]:
        """Load ``<labware_name>.json`` from the search folders.

        Raises:
            FileNotFoundError: If no folder holds the definition.
        """
        dirs = _definition_dirs(search_paths, owner=type(self))
        for directory in dirs:
            candidate = directory / f"{labware_name}.json"
            if candidate.is_file():
                return json.loads(candidate.read_text(encoding="utf-8"))
        raise FileNotFoundError(
            f"Labware definition '{labware_name}.json' not found in {[str(d) for d in dirs]}"
        )

    @property
    def definition(self) -> Dict[str, Any]:
        """The raw definition dict."""
        return self._definition

    def __str__(self):
        lines = [
            f"Labware name: {self.name}",
            f"Height in mm: {self.get_height()}",
            "Distances away from origin (0,0) for each well in mm",
        ]
        for well_id, well_data in self._wells.items():
            x, y, z = well_data.get("x"), well_data.get("y"), well_data.get("z")
            if x is None or y is None or z is None:
                raise KeyError(f"Well '{well_id}' has missing coordinates in labware definition")
            lines.append(f"Well {well_id}: x:{x}, y:{y}, z:{z}")
        return "\n".join(lines)

    @property
    def wells(self) -> List[str]:
        """Well IDs, for example ``["A1", "A2", "B1", ...]``."""
        return list(self._wells.keys())

    def get_well_position(self, well_id: str) -> Position:
        """Center of a well, relative to the labware origin.

        Raises:
            KeyError: If the well is not in this labware.
        """
        well_data = self._wells.get(well_id.upper())
        if well_data is None:
            raise KeyError(f"Well '{well_id}' not found in labware '{self.name}'")
        return Position(
            x=well_data.get("x", 0.0),
            y=well_data.get("y", 0.0),
            z=well_data.get("z", 0.0),
        )

    def get_height(self, well_name: Optional[str] = None) -> float:
        """Labware height (``zDimension``), or one well's ``z`` when ``well_name`` is given.

        Raises:
            KeyError: If the dimensions, ``zDimension``, or the well is missing.
        """
        dimensions = self._definition.get("dimensions")
        if dimensions is None:
            raise KeyError("'dimensions' not found in labware definition")
        if well_name:
            well_data = self._wells.get(well_name.upper())
            if well_data is None:
                raise KeyError(f"Well '{well_name}' not found in labware '{self.name}'")
            return well_data.get("z")
        if "zDimension" not in dimensions:
            raise KeyError("'zDimension' not found in labware dimensions")
        return dimensions["zDimension"]

    def get_insert_depth(self) -> float:
        """Maximum internal Z clearance: top of the opening to the floor of the well.

        Raises:
            KeyError: If ``insert_depth`` is not in the definition.
        """
        if "insert_depth" not in self._definition:
            raise KeyError("'insert_depth' not found in labware definition")
        return self._definition["insert_depth"]


__all__ = ["BUNDLED_DIR", "StandardLabware", "find_definition", "get_available_labware"]
