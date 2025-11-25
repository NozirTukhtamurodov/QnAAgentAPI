# Running Tests

This directory contains tests for the QnA Agent API.

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
- `test_sessions.py` - Session management API tests
- `test_chat.py` - Chat functionality and integration tests
- `test_knowledge_base.py` - Knowledge base search tests

## Running Tests

### Run all tests:
```bash
poetry run pytest
```

### Run with coverage:
```bash
poetry run pytest --cov=src --cov-report=html
```

### Run specific test file:
```bash
poetry run pytest tests/test_sessions.py
```

### Run integration tests only:
```bash
poetry run pytest -m integration
```

### Run with verbose output:
```bash
poetry run pytest -v
```

## Test Categories

- **Unit Tests**: Fast tests that don't require external services
- **Integration Tests**: Tests marked with `@pytest.mark.integration` that make real LLM API calls

## Requirements

Integration tests require:
- Valid `OPENAI_API_KEY` in `.env`
- Network connectivity to OpenAI or compatible endpoint
- Knowledge base files in `./knowledge` directory

## Notes

- Tests use in-memory SQLite database for isolation
- Integration tests may take longer due to LLM API calls
- Some tests validate conversation context and tool calling behavior
