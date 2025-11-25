# QnA Agent API

Production-ready Question & Answer Agent API powered by OpenAI GPT-4 with integrated knowledge base search capabilities.

## Features

- 🤖 **AI-Powered Chat**: GPT-4 integration with function calling for knowledge base searches
- 📚 **Knowledge Base**: Vector similarity search across custom documentation
- 💾 **Session Management**: Persistent chat sessions with conversation history
- 🔄 **Async Architecture**: Built with FastAPI and async SQLAlchemy for high performance
- 🐳 **Docker Ready**: Complete Docker and Kubernetes deployment configurations
- ✅ **Tested**: Comprehensive test suite with pytest
- 📊 **Production Ready**: Health checks, structured logging, and observability

## Prerequisites

- Docker Desktop
- OpenAI API key
- kubectl (optional, for Kubernetes deployment)

## Quick Start

### 1. Configure Environment

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./data/qna_agent.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### 2. Add Knowledge Base (Optional)

Place your knowledge base text files in the `knowledge/` directory. Example files are included:
- `docker_basics.txt`
- `fastapi_framework.txt`
- `openai_models.txt`
- `python_basics.txt`

### 3. Run the Application

```bash
make docker-build
make docker-up
make docker-migrate
```

Access the API at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### View Logs

```bash
make docker-logs
```

### Stop the Application

```bash
make docker-down
```

## Kubernetes Deployment

### Full Deployment

```bash
make k8s-full-deploy
```

Access at http://localhost:30080

### Manual Deployment

```bash
make k8s-build
make k8s-secret
make k8s-deploy
make k8s-status
make k8s-migrate
```

### Cleanup

```bash
make k8s-delete
```

## Development

### Run Tests

```bash
make docker-test
make docker-test-cov
```

### Database Migrations

```bash
make docker-migrate
```

## Architecture

### Clean Architecture Layers

1. **API Layer** (`src/api/`): FastAPI routers and dependencies
2. **Domain Layer** (`src/domain/`): Business entities and schemas
3. **Logic Layer** (`src/logic/`): Business logic and services
4. **Repository Layer** (`src/repositories/`): Database operations
5. **Infrastructure Layer** (`src/infrastructure/`): External integrations

### Why the Logic Layer?

The `logic/` folder is intentionally organized by business domains (chat, sessions, common) rather than technical concerns. This design choice enables easy transition to a microservices architecture:

- **Clear Domain Boundaries**: Each subfolder (`chat/`, `sessions/`) represents a potential microservice
- **Independent Deployment**: Business logic is self-contained and can be extracted with minimal refactoring
- **Service Separation**: When scaling demands arise, you can split:
  - `logic/chat/` → Chat Service (handles LLM interactions and knowledge base queries)
  - `logic/sessions/` → Session Service (manages user sessions and conversation history)
  - `logic/common/` → Shared libraries or separate utility services

This structure reduces coupling and makes horizontal scaling straightforward when your application grows beyond a monolithic architecture.

## Project Structure

```
.
├── src/
│   ├── api/              # FastAPI routers
│   ├── domain/           # Entities and schemas
│   ├── infrastructure/   # DB models, OpenAI client
│   ├── logic/            # Business logic
│   ├── repositories/     # Data access
│   └── config.py
├── tests/
├── k8s/
├── knowledge/
├── data/
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── Makefile
```

## API Endpoints

### Health
- `GET /health` - Health check with version info

### Sessions
- `POST /sessions` - Create new chat session
- `GET /sessions` - List all sessions
- `GET /sessions/{session_id}` - Get session details
- `PATCH /sessions/{session_id}` - Update session name
- `DELETE /sessions/{session_id}` - Delete session

### Chat
- `POST /sessions/{session_id}/messages` - Send message (streaming response)
- `GET /sessions/{session_id}/messages` - Get message history

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | - |
| `OPENAI_MODEL` | Model to use | `gpt-4o-mini` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./data/qna_agent.db` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `KNOWLEDGE_DIR` | Knowledge base directory | `knowledge` |

## Troubleshooting

```bash
# Port already in use
lsof -i :8000 && kill -9 <PID>

# Reset database
rm data/qna_agent.db && make migrate-up

# Check Kubernetes pods
kubectl get pods
kubectl logs -l app=qna-agent-api
```