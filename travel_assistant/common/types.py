from dataclasses import dataclass
from typing import Literal


ProductID = str


@dataclass
class Product:
    id: ProductID
    description: str


@dataclass
class CompositeQuery:
    action_kind: Literal["active", "beach", "adventure"]
    city: str
