"""Vector database service coordinating indexing and semantic searching operations."""

import logging
from typing import Any
from uuid import UUID, uuid4

from qdrant_client.http.models import (
    Condition,
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.vector_db import qdrant_client
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)
COLLECTION_NAME = "documents"


class VectorService:
    """Service layer coordinating Qdrant vector collection actions."""

    def __init__(self) -> None:
        self.collection_name = COLLECTION_NAME
        self._collection_initialized = False

    def _ensure_collection_exists(self) -> None:
        """Ensure that the vector collection exists in Qdrant."""
        if self._collection_initialized:
            return

        try:
            collections = qdrant_client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info("Creating Qdrant collection: %s", self.collection_name)
                qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_service.dimension,
                        distance=Distance.COSINE,
                    ),
                )
            self._collection_initialized = True
        except Exception as err:
            logger.error("Failed to initialize Qdrant collection: %s", str(err))
            raise

    def index_document_chunks(
        self,
        doc_id: UUID,
        chunks: list[str],
        user_id: UUID,
        department_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> None:
        """Generate embeddings and upsert document text chunks into Qdrant."""
        if not chunks:
            return

        self._ensure_collection_exists()

        # 1. Generate embeddings
        embeddings = embedding_service.get_embeddings(chunks)

        # 2. Prepare points
        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            point_id = str(uuid4())
            payload = {
                "document_id": str(doc_id),
                "chunk_index": i,
                "text": chunk,
                "user_id": str(user_id),
                "department_id": str(department_id) if department_id else None,
                "team_id": str(team_id) if team_id else None,
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        # 3. Upsert points into Qdrant
        logger.info("Upserting %d points for document %s", len(points), doc_id)
        qdrant_client.upsert(collection_name=self.collection_name, points=points)

    def delete_document_points(self, doc_id: UUID) -> None:
        """Remove all indexed vector points associated with a specific document."""
        self._ensure_collection_exists()
        logger.info("Deleting Qdrant points for document %s", doc_id)
        qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=str(doc_id)),
                    )
                ]
            ),
        )

    def search_similar_chunks(
        self,
        query: str,
        limit: int = 5,
        department_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Perform semantic vector search in Qdrant with optional tenant scoping."""
        self._ensure_collection_exists()

        # 1. Generate query embedding
        query_vector = embedding_service.get_embeddings([query])[0]

        # 2. Build tenant filter conditions
        must_filters: list[Condition] = []
        if department_id:
            must_filters.append(
                FieldCondition(
                    key="department_id",
                    match=MatchValue(value=str(department_id)),
                )
            )
        if team_id:
            must_filters.append(
                FieldCondition(
                    key="team_id",
                    match=MatchValue(value=str(team_id)),
                )
            )

        qdrant_filter = Filter(must=must_filters) if must_filters else None

        # 3. Query Qdrant
        response = qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
        )
        results = response.points

        return [
            {
                "id": r.id,
                "score": r.score,
                "text": r.payload.get("text") if r.payload else "",
                "document_id": r.payload.get("document_id") if r.payload else "",
                "department_id": r.payload.get("department_id") if r.payload else None,
                "team_id": r.payload.get("team_id") if r.payload else None,
            }
            for r in results
        ]


vector_service = VectorService()
