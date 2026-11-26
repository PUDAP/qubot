"""Deck layout: which labware sits in which slot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Sequence, Union

from .labware import StandardLabware

PathLike = Union[str, Path]


def slot_names(rows: int, cols: int) -> list[str]:
    """Slot names row by row: ``A1, A2, ..., B1, ...``."""
    return [f"{chr(65 + row)}{col + 1}" for row in range(rows) for col in range(cols)]


class Deck:
    """Slots ``A1`` upward, each empty or holding one labware.

    ``labware_paths`` are the edge's own definition folders, searched before the
    bundled definitions whenever labware is loaded by name.
    """

    def __init__(self, rows: int, cols: int, *, labware_paths: Sequence[PathLike] = ()):
        if rows < 1 or cols < 1:
            raise ValueError(f"Deck needs at least one row and column, got {rows}x{cols}")
        self.labware_paths = tuple(Path(path) for path in labware_paths)
        self.slots: dict[str, Optional[StandardLabware]] = {slot: None for slot in slot_names(rows, cols)}

    @classmethod
    def from_frame(cls, frame, *, labware_paths: Sequence[PathLike] = ()) -> "Deck":
        """Deck with the frame's default grid."""
        return cls(frame.default_deck["rows"], frame.default_deck["cols"], labware_paths=labware_paths)

    def _slot(self, slot: str) -> str:
        key = slot.upper()
        if key not in self.slots:
            raise KeyError(f"Slot {slot} not found in deck")
        return key

    def load_labware(self, slot: str, labware: Union[str, StandardLabware]) -> StandardLabware:
        """Put labware in a slot, by definition name or as a ready object.

        Raises:
            KeyError: If the slot is not on this deck.
            FileNotFoundError: If a name has no definition in the search folders.
        """
        key = self._slot(slot)
        if isinstance(labware, str):
            labware = StandardLabware(labware, search_paths=self.labware_paths)
        self.slots[key] = labware
        return labware

    def empty_slot(self, slot: str) -> None:
        """Remove the labware from a slot.

        Raises:
            KeyError: If the slot is not on this deck.
        """
        self.slots[self._slot(slot)] = None

    def __str__(self):
        return "\n".join(f"{slot}: {labware.name}" for slot, labware in self.slots.items() if labware is not None)

    def __getitem__(self, key: str) -> Optional[StandardLabware]:
        """``deck["B4"]``"""
        return self.slots[self._slot(key)]

    def to_dict(self) -> dict:
        """Slot to labware name, ``None`` for empty slots."""
        return {slot: (labware.name if labware is not None else None) for slot, labware in self.slots.items()}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


__all__ = ["Deck", "slot_names"]
