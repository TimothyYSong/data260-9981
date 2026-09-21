import json
import time
import yaml
import numpy as np

from pathlib import Path
from pypdf import PdfReader

from llama_index.core import (
    Document,
    VectorStoreIndex,
    StorageContext,
)

from llama_index.core.node_parser import (
    TokenTextSplitter,
    SemanticSplitterNodeParser,
    SentenceWindowNodeParser,
)

from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.schema import MetadataMode


CORPUS_DIR = Path("reports/hw03/corpus")
QUESTIONS_PATH = Path("reports/hw03/questions.yaml")
RAW_DIR = Path("reports/hw03/raw")

TOP_K = 5

RAW_DIR.mkdir(parents=True, exist_ok=True)


embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


documents = []

for pdf_path in sorted(CORPUS_DIR.glob("*.pdf")):
    reader = PdfReader(str(pdf_path))

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()

        if text and text.strip():
            document = Document(
                text=text,
                metadata={
                    "file_name": pdf_path.name,
                    "page_number": page_number
                }
            )

            document.excluded_embed_metadata_keys = [
                "file_name",
                "page_number"
            ]

            documents.append(document)


print(f"Loaded {len(documents)} document/page objects.")

print("\nFirst extracted page preview:")
print(documents[0].text[:500])


token_splitter = TokenTextSplitter(
    chunk_size=256,
    chunk_overlap=50
)

token_nodes = token_splitter.get_nodes_from_documents(
    documents
)

print(f"\nToken chunks: {len(token_nodes)}")


semantic_splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=embed_model
)

semantic_nodes = semantic_splitter.get_nodes_from_documents(
    documents
)

print(f"Semantic chunks: {len(semantic_nodes)}")


sentence_splitter = SentenceWindowNodeParser.from_defaults(
    window_size=3,
    window_metadata_key="window",
    original_text_metadata_key="original_text"
)

sentence_nodes = sentence_splitter.get_nodes_from_documents(
    documents
)

print(
    f"Sentence-window chunks: "
    f"{len(sentence_nodes)}"
)


chunk_stats = {
    "token": {
        "chunks": len(token_nodes),
        "avg_chunk_len": float(
            np.mean(
                [
                    len(node.text)
                    for node in token_nodes
                ]
            )
        )
    },
    "semantic": {
        "chunks": len(semantic_nodes),
        "avg_chunk_len": float(
            np.mean(
                [
                    len(node.text)
                    for node in semantic_nodes
                ]
            )
        )
    },
    "sentence_window": {
        "chunks": len(sentence_nodes),
        "avg_chunk_len": float(
            np.mean(
                [
                    len(node.text)
                    for node in sentence_nodes
                ]
            )
        )
    }
}


with open(
    RAW_DIR / "chunk_stats.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        chunk_stats,
        f,
        indent=2
    )


print("\nChunk statistics:")
print(
    json.dumps(
        chunk_stats,
        indent=2
    )
)


token_vector_store = SimpleVectorStore()

token_storage = StorageContext.from_defaults(
    vector_store=token_vector_store
)

token_index = VectorStoreIndex(
    token_nodes,
    storage_context=token_storage,
    embed_model=embed_model
)


semantic_vector_store = SimpleVectorStore()

semantic_storage = StorageContext.from_defaults(
    vector_store=semantic_vector_store
)

semantic_index = VectorStoreIndex(
    semantic_nodes,
    storage_context=semantic_storage,
    embed_model=embed_model
)


sentence_vector_store = SimpleVectorStore()

sentence_storage = StorageContext.from_defaults(
    vector_store=sentence_vector_store
)

sentence_index = VectorStoreIndex(
    sentence_nodes,
    storage_context=sentence_storage,
    embed_model=embed_model
)


print("\nSentence-window example:")
print("Indexed sentence:")
print(sentence_nodes[0].text)

print("\nWindow metadata:")
print(
    sentence_nodes[0].metadata.get("window")
)


def cosine_similarity(a, b):
    a = np.array(
        a,
        dtype=float
    )

    b = np.array(
        b,
        dtype=float
    )

    denominator = (
        np.linalg.norm(a)
        * np.linalg.norm(b)
    )

    if denominator == 0:
        return 0.0

    return float(
        np.dot(a, b)
        / denominator
    )


def run_retrieval(
    technique,
    index,
    query_id,
    query,
    expected_answer,
    expected_source,
    k=TOP_K
):
    print(
        "\n"
        + "=" * 100
    )

    print(
        f"Technique: {technique}"
    )

    print(
        f"Question ID: {query_id}"
    )

    print(
        f"Query: {query}"
    )

    print(
        "=" * 100
    )

    query_embedding = np.array(
        embed_model.get_query_embedding(
            query
        ),
        dtype=float
    )

    print(
        f"Query embedding dimension: "
        f"{len(query_embedding)}"
    )

    print(
        "First 8 query embedding values:",
        query_embedding[:8].tolist()
    )

    retriever = index.as_retriever(
        similarity_top_k=k
    )

    start_time = time.perf_counter()

    results = retriever.retrieve(
        query
    )

    latency_ms = (
        time.perf_counter()
        - start_time
    ) * 1000

    rows = []
    doc_vectors = []

    for rank, result in enumerate(
        results,
        start=1
    ):
        chunk_text = result.node.get_content(
            metadata_mode=MetadataMode.NONE
        )

        doc_embedding = np.array(
            embed_model.get_text_embedding(
                chunk_text
            ),
            dtype=float
        )

        doc_vectors.append(
            doc_embedding
        )

        cosine_sim = cosine_similarity(
            query_embedding,
            doc_embedding
        )

        preview = " ".join(
            chunk_text.split()
        )[:160]

        source_file = (
            result.node.metadata.get(
                "file_name"
            )
            or result.node.metadata.get(
                "filename"
            )
            or result.node.metadata.get(
                "file_path"
            )
            or "unknown"
        )

        if source_file != "unknown":
            source_file = Path(
                str(source_file)
            ).name

        window_context = None

        if technique == "sentence_window":
            window_context = (
                result.node.metadata.get(
                    "window"
                )
            )

        row = {
            "rank": rank,
            "store_score": (
                float(result.score)
                if result.score is not None
                else None
            ),
            "cosine_sim": cosine_sim,
            "chunk_len": len(
                chunk_text
            ),
            "preview": preview,
            "source_file": source_file,
            "window_context": (
                window_context
            )
        }

        rows.append(
            row
        )

    if doc_vectors:
        doc_matrix = np.vstack(
            doc_vectors
        )

    else:
        doc_matrix = np.empty(
            (
                0,
                len(query_embedding)
            )
        )

    print(
        f"Query vector shape: "
        f"{query_embedding.shape}"
    )

    print(
        f"Stacked document vector shape: "
        f"{doc_matrix.shape}"
    )

    print(
        f"Retrieval latency: "
        f"{latency_ms:.3f} ms"
    )

    print()

    print(
        f"{'Rank':<6}"
        f"{'Store Score':<15}"
        f"{'Cosine Sim':<15}"
        f"{'Chunk Len':<12}"
        f"Preview"
    )

    print(
        "-" * 100
    )

    for row in rows:
        if row["store_score"] is not None:
            store_score = (
                f"{row['store_score']:.6f}"
            )

        else:
            store_score = "N/A"

        print(
            f"{row['rank']:<6}"
            f"{store_score:<15}"
            f"{row['cosine_sim']:<15.6f}"
            f"{row['chunk_len']:<12}"
            f"{row['preview']}"
        )


    output = {
        "technique": technique,
        "question_id": query_id,
        "query": query,
        "expected_answer": (
            expected_answer
        ),
        "expected_source": (
            expected_source
        ),
        "k": k,
        "query_embedding_dimension": (
            len(query_embedding)
        ),
        "query_embedding_first_8": (
            query_embedding[:8].tolist()
        ),
        "query_vector_shape": list(
            query_embedding.shape
        ),
        "doc_vector_shape": list(
            doc_matrix.shape
        ),
        "latency_ms": latency_ms,
        "results": rows
    }


    output_file = (
        RAW_DIR
        / f"{technique}_{query_id}.json"
    )


    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )


    print(
        f"\nSaved raw output: "
        f"{output_file}"
    )

    return output


with open(
    QUESTIONS_PATH,
    "r",
    encoding="utf-8"
) as f:
    question_data = yaml.safe_load(
        f
    )


techniques = {
    "token": token_index,
    "semantic": semantic_index,
    "sentence_window": sentence_index
}


for question_item in question_data[
    "questions"
]:
    query_id = (
        question_item["id"]
    )

    query = (
        question_item["question"]
    )

    expected_answer = (
        question_item[
            "expected_answer"
        ]
    )

    expected_source = (
        question_item[
            "expected_source"
        ]
    )

    for (
        technique_name,
        technique_index
    ) in techniques.items():

        run_retrieval(
            technique=technique_name,
            index=technique_index,
            query_id=query_id,
            query=query,
            expected_answer=expected_answer,
            expected_source=expected_source,
            k=TOP_K
        )


print(
    "\n"
    + "=" * 100
)

print(
    "Completed all retrieval runs."
)

print(
    f"Raw outputs saved in: "
    f"{RAW_DIR}"
)

print(
    "=" * 100
)