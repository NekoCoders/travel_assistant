import json
from typing import List, Dict

import numpy as np
import tqdm
from sklearn.cluster import KMeans

from travel_assistant.common.custom_types import ProductID, Product
from travel_assistant.database.similarity_model import SimilarityModel


class ProductDatabase:
    products: Dict[ProductID, Product]
    product_embs: np.ndarray
    product_ids: List[ProductID]

    def __init__(self):
        self.encoder = SimilarityModel()

    def load(self, path: str = "products.json"):
        with open(path, "rt", encoding="utf-8") as f:
            products = json.load(f)
        products = [Product.deserialize(p) for p in products]

        for p in tqdm.tqdm(products, "Encoding descriptions ..."):
            if p.emb is None:
                p.emb = self.encoder.encode(p.full_text)

        self.products = {p.id: p for p in products}
        self.product_ids = [p.id for p in products]
        self.product_embs = np.stack([p.emb for p in products], axis=0)

    def save(self, path: str = "products.json"):
        data = [
            self.products[self.product_ids[i]].serialize()
            for i in range(len(self.product_ids))
        ]
        with open(path, "w+", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray, axis=-1) -> np.ndarray:
        return (a * b).sum(axis=axis) / (np.linalg.norm(a, axis=axis) * np.linalg.norm(b, axis=axis))

    def _get_clusters(self, scores, n_clusters: int, temperature=0.2):
        idxs = np.argsort(scores)[::-1]
        weights = np.exp((scores - scores.max()) / temperature)
        kmeans = KMeans(n_clusters=n_clusters).fit(self.product_embs, sample_weight=weights)
        tops = [[] for _ in range(n_clusters)]
        labels = kmeans.labels_[::-1]
        for i, label in zip(idxs, labels):
            tops[label].append(i)
        tops = [tops[i] for i in np.argsort([scores[t[0]] for t in tops])[::-1]]
        return tops

    def search_offers(self, query: str, n_groups: int = 8) -> List[List[Product]]:
        query_emb = self.encoder.encode(query)
        scores = self._cosine_sim(query_emb, self.product_embs)
        clusters = self._get_clusters(scores, n_groups)

        top_descs = [
            [
                self.products[self.product_ids[cli]]
                for cli in cl
            ]
            for cl in clusters
        ]
        return top_descs

    def search_best_offers(self, query: str, n_groups: int = 8) -> List[Product]:
        offers = self.search_offers(query, n_groups)
        return [p[0] for p in offers]
