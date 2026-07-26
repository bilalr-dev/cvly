from __future__ import annotations

import math
from typing import List

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:

    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must have the same length")

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        raise ValueError("Cannot calculate cosine similarity of a zero vector")

    return dot_product / (norm_a * norm_b)
