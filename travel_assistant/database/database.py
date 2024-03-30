from typing import List, Tuple

import numpy as np

from travel_assistant.common.types import ProductID, Product
from travel_assistant.database.similarity_model import SimilarityModel


class ProductDatabase:
    def __init__(self):
        self.encoder = SimilarityModel()

    def retrieve_similar(self, query_emb: np.ndarray) -> List[ProductID]:
        ...

    def search_offers(self, query: str, n_groups: int) -> List[Tuple[str, List[Product]]]:
        query_emb = self.encoder.encode(query)