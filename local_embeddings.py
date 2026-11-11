
import hashlib
import math
import re

DIMENSIONS = 1024


def generate_embedding(text):
    text = text.lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9+#.-]*", text)

    features = tokens + [
        tokens[i] + "_" + tokens[i + 1]
        for i in range(len(tokens) - 1)
    ]

    vector = [0.0] * DIMENSIONS

    for feature in features:
        digest = hashlib.blake2b(
            feature.encode("utf-8"),
            digest_size=8
        ).digest()

        bucket = int.from_bytes(digest[:4], "little") % DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0

        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))

    if norm:
        vector = [value / norm for value in vector]

    return vector


def generate_embeddings(texts):
    return [generate_embedding(text) for text in texts]
