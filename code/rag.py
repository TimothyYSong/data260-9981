from pathlib import Path

import chromadb
import requests
from pypdf import PdfReader


CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3

DOCS_DIR = Path(__file__).resolve().parent / "rag_docs"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"

EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen3:8b"

OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embed"
OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"


QUESTIONS = {
    "Q1": "What is gradient descent?",
    "Q2": (
        "According to the lectures, how does batch gradient descent compute "
        "its gradient using the training data, and what velocity and parameter "
        "update equations are used by momentum gradient descent?"
    ),
    "Q3": (
        "How is gradient descent described across the lecture documents?"
    ),
    "Q4": "What does momentum mean?",
    "Q5": "What is SJSU's address?",
    "Q6": "What is today's weather?",
}


def read_pdf(path):
    reader = PdfReader(path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n".join(pages)


def chunk_text(
    text,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
):
    chunks = []

    start = 0
    chunk_id = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": chunk,
                }
            )

            chunk_id += 1

        start += chunk_size - chunk_overlap

    return chunks


def embed_text(text):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "input": text,
        },
    )

    response.raise_for_status()

    return response.json()["embeddings"][0]


def call_llm(prompt):
    response = requests.post(
        OLLAMA_GENERATE_URL,
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
        },
    )

    response.raise_for_status()

    return response.json()["response"].strip()


def get_collection():
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    return client.get_collection(
        name="hw4_rag"
    )


def build_index():
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    try:
        client.delete_collection("hw4_rag")
    except Exception:
        pass

    collection = client.create_collection(
        name="hw4_rag"
    )

    documents = sorted(
        DOCS_DIR.glob("*.pdf")
    )

    if len(documents) < 5:
        raise ValueError(
            "At least 5 PDF documents are required in rag_docs/"
        )

    total_chunks = 0

    for document_path in documents:
        text = read_pdf(document_path)

        chunks = chunk_text(text)

        print(
            f"{document_path.name}: "
            f"{len(chunks)} chunks"
        )

        for chunk in chunks:
            source = document_path.name
            chunk_id = chunk["chunk_id"]
            chunk_text_value = chunk["text"]

            vector_id = (
                f"{source}_chunk_{chunk_id}"
            )

            embedding = embed_text(
                chunk_text_value
            )

            collection.add(
                ids=[vector_id],
                documents=[chunk_text_value],
                embeddings=[embedding],
                metadatas=[
                    {
                        "source": source,
                        "chunk_id": chunk_id,
                    }
                ],
            )

            total_chunks += 1

    print()
    print(f"Documents indexed: {len(documents)}")
    print(f"Total chunks indexed: {total_chunks}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Chunk overlap: {CHUNK_OVERLAP}")
    print(f"Embedding model: {EMBED_MODEL}")
    print("Vector store: Chroma")
    print(
        f"Collection count: {collection.count()}"
    )


def retrieve_chunks(
    question,
    top_k=TOP_K,
):
    collection = get_collection()

    question_embedding = embed_text(
        question
    )

    results = collection.query(
        query_embeddings=[
            question_embedding
        ],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    print()
    print(f"Question: {question}")
    print(f"Top-k: {top_k}")
    print()

    retrieved = []

    for i in range(top_k):
        document = (
            results["documents"][0][i]
        )

        metadata = (
            results["metadatas"][0][i]
        )

        distance = (
            results["distances"][0][i]
        )

        source = metadata["source"]
        chunk_id = metadata["chunk_id"]

        print(f"Result {i + 1}")
        print(f"Source: {source}")
        print(f"Chunk ID: {chunk_id}")
        print(
            f"Score/Distance: "
            f"{distance:.4f}"
        )
        print("Chunk:")
        print(document)
        print("-" * 80)

        retrieved.append(
            {
                "rank": i + 1,
                "source": source,
                "chunk_id": chunk_id,
                "distance": distance,
                "text": document,
            }
        )

    return retrieved


def answer_no_rag(question):
    prompt = f"""
Answer the following question.

Question:
{question}
"""

    answer = call_llm(prompt)

    print()
    print("=== CONFIGURATION A: NO RAG ===")
    print(answer)

    return answer


def answer_basic_rag(
    question,
    retrieved,
):
    context = "\n\n".join(
        chunk["text"]
        for chunk in retrieved
    )

    prompt = f"""
Use the following retrieved context to answer the question.

Context:
{context}

Question:
{question}
"""

    answer = call_llm(prompt)

    print()
    print("=== CONFIGURATION B: BASIC RAG ===")
    print(answer)

    return answer


def prepare_context_engineered_chunks(
    retrieved,
    max_distance=0.65,
):
    survivors = []
    seen_text = set()

    for chunk in retrieved:
        text = chunk["text"].strip()

        if chunk["distance"] > max_distance:
            continue

        if text in seen_text:
            continue

        seen_text.add(text)
        survivors.append(chunk)

    return survivors


def answer_context_rag(
    question,
    retrieved,
):
    survivors = prepare_context_engineered_chunks(
        retrieved
    )

    if not survivors:
        context = (
            "No relevant context was retrieved."
        )
    else:
        context_parts = []

        for i, chunk in enumerate(
            survivors,
            start=1,
        ):
            context_parts.append(
                f"[Source {i}] "
                f"{chunk['source']} "
                f"(chunk {chunk['chunk_id']})\n"
                f"{chunk['text']}"
            )

        context = "\n\n".join(
            context_parts
        )

    prompt = f"""
You are a grounded question-answering system.

Rules:
1. Answer only from the provided context.
2. Do not use outside knowledge.
3. Cite supporting evidence using [Source 1], [Source 2], etc.
4. If the provided context does not contain enough evidence to answer the question, respond exactly:
I cannot answer this question from the provided documents

Context:
{context}

Question:
{question}
"""

    answer = call_llm(prompt)

    print()
    print(
        "=== CONFIGURATION C: "
        "CONTEXT-ENGINEERED RAG ==="
    )
    print(answer)

    return answer


def compare_configurations(question):
    print("=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)

    no_rag_answer = answer_no_rag(
        question
    )

    retrieved = retrieve_chunks(
        question,
        top_k=TOP_K,
    )

    basic_rag_answer = answer_basic_rag(
        question,
        retrieved,
    )

    context_rag_answer = answer_context_rag(
        question,
        retrieved,
    )

    return {
        "question": question,
        "no_rag": no_rag_answer,
        "basic_rag": basic_rag_answer,
        "context_rag": context_rag_answer,
    }


def run_k_sweep(question):
    print()
    print("#" * 80)
    print("PART 4.5: CONTEXT SIZE K-SWEEP")
    print(f"Question: {question}")
    print("#" * 80)

    for k in [1, 3, 5]:
        print()
        print("=" * 80)
        print(f"K = {k}")
        print("=" * 80)

        retrieved = retrieve_chunks(
            question,
            top_k=k,
        )

        answer_context_rag(
            question,
            retrieved,
        )


if __name__ == "__main__":
    run_k_sweep(
        QUESTIONS["Q3"]
    )