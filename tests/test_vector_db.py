"""Integration and unit tests for Qdrant vector database and SentenceTransformers."""

from uuid import uuid4

from app.services.embedding_service import embedding_service
from app.services.vector_service import vector_service


def test_embedding_generation() -> None:
    """Test generating embeddings using SentenceTransformers."""
    texts = ["This is a test document.", "Another sample sentence."]
    embeddings = embedding_service.get_embeddings(texts)

    assert len(embeddings) == len(texts)
    assert len(embeddings[0]) == embedding_service.dimension
    assert len(embeddings[1]) == embedding_service.dimension
    assert all(isinstance(val, float) for val in embeddings[0])


def test_vector_indexing_and_search() -> None:
    """Test indexing document chunks and performing semantic searches."""
    doc_id = uuid4()
    user_id = uuid4()
    chunks = [
        "FastAPI is a modern web framework for building APIs with Python.",
        "SQLAlchemy is an SQL toolkit and Object-Relational Mapper for Python.",
        "Qdrant is a vector database designed for semantic search and retrieval.",
    ]

    # Index
    vector_service.index_document_chunks(
        doc_id=doc_id,
        chunks=chunks,
        user_id=user_id,
    )

    # Search for Qdrant
    results = vector_service.search_similar_chunks("vector databases", limit=1)
    assert len(results) == 1
    assert "Qdrant" in results[0]["text"]
    assert results[0]["document_id"] == str(doc_id)

    # Clean up
    vector_service.delete_document_points(doc_id)
    results = vector_service.search_similar_chunks(
        "vector databases", limit=10
    )
    assert not any(r["document_id"] == str(doc_id) for r in results)


def test_vector_search_tenant_scoping() -> None:
    """Test semantic search with strict tenant department/team filter scope."""
    doc_a_id = uuid4()
    doc_b_id = uuid4()
    user_id = uuid4()

    dept_hr_id = uuid4()
    dept_eng_id = uuid4()

    # Index doc A in HR department
    vector_service.index_document_chunks(
        doc_id=doc_a_id,
        chunks=["Employees must submit their timesheets before Friday noon."],
        user_id=user_id,
        department_id=dept_hr_id,
    )

    # Index doc B in Engineering department
    vector_service.index_document_chunks(
        doc_id=doc_b_id,
        chunks=[
            "Deployments should be triggered via the main pipeline branch."
        ],
        user_id=user_id,
        department_id=dept_eng_id,
    )

    # Search without scope
    results = vector_service.search_similar_chunks(
        "pipeline deployments", limit=10
    )
    assert len(results) >= 1

    # Search with HR scope -> should NOT return doc B (Engineering timesheet)
    hr_results = vector_service.search_similar_chunks(
        "pipeline deployments", limit=10, department_id=dept_hr_id
    )
    assert not any(r["document_id"] == str(doc_b_id) for r in hr_results)

    # Search with Engineering scope -> should return doc B
    eng_results = vector_service.search_similar_chunks(
        "pipeline deployments", limit=10, department_id=dept_eng_id
    )
    assert any(r["document_id"] == str(doc_b_id) for r in eng_results)

    # Clean up
    vector_service.delete_document_points(doc_a_id)
    vector_service.delete_document_points(doc_b_id)
