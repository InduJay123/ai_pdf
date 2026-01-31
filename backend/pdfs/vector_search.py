import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def search_similar_chunks(question_embedding, chunk_embeddings, top_k=5):
    question_vec = np.array(question_embedding).reshape(1, -1)
    chunk_vecs = np.array(chunk_embeddings)

    similarities = cosine_similarity(question_vec, chunk_vecs)[0]
    top_indices = similarities.argsort()[-top_k:][::-1]

    return top_indices, similarities[top_indices]
