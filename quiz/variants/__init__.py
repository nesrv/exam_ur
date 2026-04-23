from __future__ import annotations

from .v1 import V1
from .v2 import V2
from .v3 import V3

VARIANTS: dict[str, dict] = {
    "v1": V1,
    "v2": V2,
    "v3": V3,
}
VARIANT_IDS: tuple[str, ...] = tuple(VARIANTS.keys())


def get_variant(variant_id: str) -> dict:
    return VARIANTS[variant_id]
