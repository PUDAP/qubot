"""Labware catalog and deck layout.

    from qubot.labware import Deck, StandardLabware

Bundled definitions live in ``qubot/labware/definitions/``. An edge adds its own
labware by passing folders of ``<name>.json`` files (``search_paths`` /
``labware_paths``), or a definition dict via ``StandardLabware.from_definition``.
"""

from .deck import Deck, slot_names
from .labware import BUNDLED_DIR, StandardLabware, find_definition, get_available_labware

__all__ = ["BUNDLED_DIR", "Deck", "StandardLabware", "find_definition", "get_available_labware", "slot_names"]
