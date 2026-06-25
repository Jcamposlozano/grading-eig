from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Universidad:
    """Tenant raíz. ``id`` es el slug: westfield | eig | esic | uide."""

    id: str
    nombre: str
