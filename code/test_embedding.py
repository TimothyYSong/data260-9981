from llama_index.embeddings.huggingface import HuggingFaceEmbedding

embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

embedding = embed_model.get_text_embedding(
    "Restaurant inspections help protect public health."
)

print("Embedding dimension:", len(embedding))
print("First 8 values:", embedding[:8])