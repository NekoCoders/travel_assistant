from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class SimilarityModel:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2')

    def encode(self, sentences: str | List[str]) -> np.ndarray:
        embeddings = self.model.encode(sentences)
        return embeddings
