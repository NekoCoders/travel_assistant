from typing import List

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


class SimilarityModel:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v2', device=self.device)

    def encode(self, sentences: str | List[str]) -> np.ndarray:
        embeddings = self.model.encode(sentences, device=self.device)
        return embeddings
