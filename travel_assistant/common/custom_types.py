import base64
import dataclasses
from dataclasses import dataclass
from typing import Literal, List, Optional, Tuple

import numpy as np

ProductID = str


@dataclass
class Product:
    id: ProductID
    title: str
    description: str
    cities: List[str]
    regions: List[str]
    tags: List[str]
    full_text: str
    emb: Optional[str] = None

    @staticmethod
    def _encode_emb(emb: np.ndarray):
        return base64.b64encode(emb.astype(np.float32).data).decode()

    @staticmethod
    def _decode_emb(emb: bytes):
        return np.frombuffer(base64.b64decode(emb), np.float32)

    def serialize(self):
        data = dataclasses.asdict(self)
        data["emb"] = self._encode_emb(data["emb"])
        return data

    @classmethod
    def deserialize(cls, data):
        if "emb" in data:
            data["emb"] = cls._decode_emb(data["emb"])
        return cls(**data)


@dataclass
class CompositeQuery:
    action_kind: Literal["active", "beach", "adventure"]
    city: str


class ClientContext:
    interests: str = ""
    messages: List[Tuple[str, str]]

    def __init__(self, messages: Optional[List[Tuple[str, str]]] = None, interests: str = ""):
        if messages is None:
            self.messages = []
        else:
            self.messages = messages
        self.interests = interests
