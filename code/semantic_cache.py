
import logging
import os
import re
from time import perf_counter
from uuid import uuid4

import numpy as np
import redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError
from sentence_transformers import SentenceTransformer

from agent import run_agent

logger = logging.getLogger(__name__)

# Personal configuration
PREFIX = "s9981"

# Redis semantic cache configuration
INDEX_NAME = f"{PREFIX}:semantic:index"
KEY_PREFIX = f"{PREFIX}:semantic:entry:"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_THRESHOLD = 0.95
DEFAULT_DATA_VERSION = "v1"

# Number of nearest candidates to examine
TOP_K = 20


def extract_entity_ids(question):
    """
    Extract explicit restaurant and inspection identifiers.

    Examples:
        Restaurant 13 -> restaurant ID 13
        Restaurant 14 -> restaurant ID 14
        Inspection 10017 -> inspection ID 10017
    """

    restaurant_ids = tuple(
        sorted(
            set(
                re.findall(
                    r"\brestaurant\s*(?:number\s*|#\s*)?(\d+)\b",
                    question,
                    flags=re.IGNORECASE,
                )
            )
        )
    )

    inspection_ids = tuple(
        sorted(
            set(
                re.findall(
                    r"\binspection\s*(?:id\s*|number\s*|#\s*)?(\d+)\b",
                    question,
                    flags=re.IGNORECASE,
                )
            )
        )
    )

    return restaurant_ids, inspection_ids


def compatible_entities(incoming, cached):
    """
    Reject cache reuse when explicit entity identifiers differ.

    Restaurant 13 vs Restaurant 13 -> compatible
    Restaurant 13 vs Restaurant 14 -> incompatible
    Inspection 10017 vs Inspection 10018 -> incompatible
    """

    return extract_entity_ids(incoming) == extract_entity_ids(cached)


class SemanticCache:
    def __init__(self):
        # Connect to Redis Stack, separate from HW9 Part 1 Redis.
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_SEARCH_HOST", "localhost"),
            port=int(os.getenv("REDIS_SEARCH_PORT", "6380")),
            decode_responses=False,
        )

        # Load embedding model.
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        self.dimensions = self.model.get_embedding_dimension()

        if self.dimensions != 384:
            raise ValueError(
                f"Expected 384-dimensional embeddings, "
                f"received {self.dimensions}"
            )

        # Ensure the Redis vector index exists.
        self.create_index()

    def create_index(self):
        """
        Create a Redis vector index if one does not already exist.

        The index stores:
            - Original question
            - Final agent answer
            - Data-version marker
            - FLOAT32 embedding
        """

        try:
            self.redis_client.ft(INDEX_NAME).info()

            logger.info(
                "Redis vector index already exists: %s",
                INDEX_NAME,
            )
            return

        except ResponseError as exc:
            if "unknown index" not in str(exc).lower():
                raise

        schema = [
            TextField("query"),
            TextField("answer"),
            TagField("data_version"),
            VectorField(
                "embedding",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.dimensions,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        ]

        definition = IndexDefinition(
            prefix=[KEY_PREFIX],
            index_type=IndexType.HASH,
        )

        self.redis_client.ft(INDEX_NAME).create_index(
            schema,
            definition=definition,
        )

        logger.info(
            "Created Redis vector index: %s",
            INDEX_NAME,
        )

    def embed(self, query):
        """
        Convert a question into a normalized FLOAT32 embedding.
        """

        vector = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return np.asarray(
            vector,
            dtype=np.float32,
        ).tobytes()

    def search(self, embedding, data_version, question):
        """
        Search Redis for semantically similar cached questions.

        Retrieve up to TOP_K candidates, ordered by cosine distance.

        Reject candidates with incompatible restaurant or inspection
        identifiers before selecting the closest valid match.
        """

        # Validate the data-version marker.
        if not data_version.replace("_", "").isalnum():
            raise ValueError("Invalid data version")

        query = (
            Query(
                f"(@data_version:{{{data_version}}})"
                f"=>[KNN {TOP_K} @embedding $vec AS distance]"
            )
            .sort_by("distance")
            .return_fields(
                "query",
                "answer",
                "data_version",
                "distance",
            )
            .paging(0, TOP_K)
            .dialect(2)
        )

        result = self.redis_client.ft(INDEX_NAME).search(
            query,
            query_params={"vec": embedding},
        )

        for doc in result.docs:
            cached_question = doc.query
            cached_answer = doc.answer

            if isinstance(cached_question, bytes):
                cached_question = cached_question.decode("utf-8")

            if isinstance(cached_answer, bytes):
                cached_answer = cached_answer.decode("utf-8")

            # Reject mismatched restaurant or inspection IDs.
            if not compatible_entities(
                question,
                cached_question,
            ):
                logger.info(
                    "CACHE CANDIDATE REJECTED: "
                    "entity mismatch | incoming=%s | cached=%s",
                    question,
                    cached_question,
                )
                continue

            # Redis COSINE distance -> cosine similarity.
            distance = float(doc.distance)

            similarity = max(
                -1.0,
                min(1.0, 1.0 - distance),
            )

            return {
                "answer": cached_answer,
                "similarity": similarity,
                "key": doc.id,
                "cached_question": cached_question,
            }

        # No entity-compatible candidate found.
        return None

    def store(
        self,
        query,
        embedding,
        answer,
        data_version,
    ):
        """
        Store the original query, embedding, final answer,
        and data version in Redis.
        """

        key = f"{KEY_PREFIX}{uuid4().hex}"

        self.redis_client.hset(
            key,
            mapping={
                "query": query,
                "embedding": embedding,
                "answer": answer,
                "data_version": data_version,
            },
        )

        logger.info(
            "CACHE STORED key=%s version=%s",
            key,
            data_version,
        )

        return key

    def ask(
        self,
        question,
        threshold=DEFAULT_THRESHOLD,
        data_version=DEFAULT_DATA_VERSION,
    ):
        """
        Handle a domain Q&A request.

        Cache hit:
            Return stored answer without executing the HW8 agent.

        Cache miss:
            Execute the HW8 agent, store its final answer,
            and return the generated response.

        Measure end-to-end handler latency for both paths.
        """

        start = perf_counter()

        # Validate input.
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question cannot be empty")

        if not 0 <= threshold <= 1:
            raise ValueError(
                "Threshold must be between 0 and 1"
            )

        question = question.strip()

        # Generate embedding for incoming question.
        embedding = self.embed(question)

        # Search Redis using similarity and entity compatibility.
        match = self.search(
            embedding,
            data_version,
            question,
        )

        # --------------------------------------------------
        # CACHE HIT
        # --------------------------------------------------
        if (
            match is not None
            and match["similarity"] >= threshold
        ):
            latency_ms = (
                perf_counter() - start
            ) * 1000

            logger.info(
                "CACHE HIT similarity=%.4f latency_ms=%.2f",
                match["similarity"],
                latency_ms,
            )

            return {
                "question": question,
                "answer": match["answer"],
                "is_cached": True,
                "similarity": round(
                    match["similarity"], 4
                ),
                "latency_ms": round(latency_ms, 2),
                "data_version": data_version,
            }

        # --------------------------------------------------
        # CACHE MISS
        # --------------------------------------------------
        logger.info(
            "CACHE MISS question=%s nearest_similarity=%s",
            question,
            (
                None
                if match is None
                else round(match["similarity"], 4)
            ),
        )

        # Run the existing HW8 agent using ModelClient.
        result = run_agent(question)

        answer = result.get("answer")
        stop_reason = result.get("stop_reason")

        # Never cache unsuccessful agent outputs.
        if stop_reason != "normal_completion" or not answer:
            raise RuntimeError(
                f"Agent failed: {stop_reason}; "
                f"{result.get('error', 'no final answer')}"
            )

        # Store the successful final answer.
        self.store(
            question,
            embedding,
            answer,
            data_version,
        )

        latency_ms = (
            perf_counter() - start
        ) * 1000

        logger.info(
            "CACHE MISS COMPLETED latency_ms=%.2f",
            latency_ms,
        )

        return {
            "question": question,
            "answer": answer,
            "is_cached": False,
            "similarity": (
                None
                if match is None
                else round(match["similarity"], 4)
            ),
            "latency_ms": round(latency_ms, 2),
            "data_version": data_version,
        }
