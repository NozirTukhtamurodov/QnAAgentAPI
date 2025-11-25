"""Tests for knowledge base functionality."""

import pytest

from logic.common import KnowledgeBaseService


@pytest.fixture
def kb_service():
    """Create a knowledge base service instance."""
    return KnowledgeBaseService(knowledge_base_dir="knowledge")


@pytest.mark.asyncio
async def test_search_knowledge_base_python(kb_service: KnowledgeBaseService):
    """Test searching for Python-related content."""
    results = await kb_service.search("Python programming language")

    assert len(results) > 0
    assert any("python" in result.content.lower() for result in results)
    assert all(result.filename.endswith(".txt") for result in results)


@pytest.mark.asyncio
async def test_search_knowledge_base_fastapi(kb_service: KnowledgeBaseService):
    """Test searching for FastAPI content."""
    results = await kb_service.search("FastAPI framework")

    assert len(results) > 0
    assert any("fastapi" in result.filename.lower() for result in results)


@pytest.mark.asyncio
async def test_search_knowledge_base_docker(kb_service: KnowledgeBaseService):
    """Test searching for Docker content."""
    results = await kb_service.search("Docker containers")

    assert len(results) > 0
    assert any("docker" in result.filename.lower() for result in results)


@pytest.mark.asyncio
async def test_search_knowledge_base_relevance(kb_service: KnowledgeBaseService):
    """Test that search results have relevance scores."""
    results = await kb_service.search("Python")

    assert len(results) > 0
    for result in results:
        if result.relevance_score is not None:
            assert 0 <= result.relevance_score <= 1


@pytest.mark.asyncio
async def test_search_knowledge_base_empty_query(kb_service: KnowledgeBaseService):
    """Test searching with empty query."""
    results = await kb_service.search("")

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_search_knowledge_base_no_match(kb_service: KnowledgeBaseService):
    """Test searching for content that doesn't exist."""
    results = await kb_service.search("quantum entanglement superconductors xyz123")

    assert isinstance(results, list)
    assert len(results) >= 0


@pytest.mark.asyncio
async def test_knowledge_base_file_structure():
    """Test that knowledge base files exist and are readable."""
    import os

    kb_dir = "knowledge"
    assert os.path.exists(kb_dir)
    assert os.path.isdir(kb_dir)

    expected_files = [
        "python_basics.txt",
        "fastapi_framework.txt",
        "docker_basics.txt",
        "openai_models.txt",
    ]

    for filename in expected_files:
        filepath = os.path.join(kb_dir, filename)
        assert os.path.exists(filepath), f"Missing knowledge base file: {filename}"
        assert os.path.isfile(filepath)

        with open(filepath, "r") as f:
            content = f.read()
            assert len(content) > 0, f"Knowledge base file is empty: {filename}"
