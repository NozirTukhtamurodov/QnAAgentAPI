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

- Python 3.12+
- Poetry (dependency management)
- OpenAI API key
- Docker Desktop (optional, for containerized deployment)
- kubectl (optional, for Kubernetes deployment)

## Quick Start (Local Development)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd QnAAgentAPI

# Install dependencies with Poetry
make install
```

### 2. Configure Environment

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

### 3. Initialize Database

```bash
# Create data directory
mkdir -p data knowledge

# Run database migrations
make migrate-up
```

### 4. Add Knowledge Base (Optional)

Place your knowledge base text files in the `knowledge/` directory. Example files are included:
- `docker_basics.txt`
- `fastapi_framework.txt`
- `openai_models.txt`
- `python_basics.txt`

### 5. Run the Application

```bash
# Start the API server
make run

# The API will be available at:
# - API: http://localhost:8000
# - Interactive Docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

## Usage Examples

### Create a Chat Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Session"}'
```

### Send a Message

```bash
curl -X POST http://localhost:8000/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What is Docker?"}'
```

### List All Sessions

```bash
curl http://localhost:8000/sessions
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Docker Deployment

### Using Docker Compose

```bash
# Build and start services
make docker-up

# View logs
make docker-logs

# Run migrations
make docker-migrate

# Stop services
make docker-down
```

### Manual Docker Build

```bash
# Build image
make docker-build

# Run container
docker run -d \
  --name qna-agent-api \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/knowledge:/app/knowledge \
  --env-file .env \
  qna-agent-api:latest
```

## Kubernetes Deployment

### Prerequisites

- Docker Desktop with Kubernetes enabled
- kubectl installed (`brew install kubectl`)

### Full Deployment

```bash
# Complete deployment (builds image, creates secrets, deploys)
make k8s-full-deploy

# The API will be automatically available at:
# - API: http://localhost:30080
# - Swagger Docs: http://localhost:30080/docs
```

### Step-by-Step Deployment

```bash
# 1. Check Kubernetes status
make k8s-start

# 2. Build Docker image
make k8s-build

# 3. Create secrets from .env file
make k8s-secret

# 4. Deploy to Kubernetes
make k8s-deploy

# 5. Check deployment status
make k8s-status

# 6. View logs
make k8s-logs

# 7. Run migrations
make k8s-migrate
```

### Access the Application

The service is configured as NodePort on port 30080, so it's automatically accessible at:
- **API**: http://localhost:30080
- **Swagger Docs**: http://localhost:30080/docs

### Cleanup

```bash
# Delete all Kubernetes resources
make k8s-delete

# Or use the clean command
make k8s-clean
```

## Development

### Run Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make test-cov
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make type-check
```

### Database Migrations

```bash
# Apply migrations
make migrate-up

# Rollback last migration
make migrate-down

# Create new migration
make migrate-create MSG="add new table"

# Check migration status
make migrate-status

# View migration history
make migrate-history
```

## Project Structure

```
.
├── src/
│   ├── api/              # FastAPI application and routers
│   ├── domain/           # Domain entities and schemas
│   ├── infrastructure/   # Database models, OpenAI client
│   ├── logic/            # Business logic (chat, sessions)
│   ├── repositories/     # Data access layer
│   └── config.py         # Configuration management
├── tests/                # Test suite
├── k8s/                  # Kubernetes manifests
├── knowledge/            # Knowledge base text files
├── data/                 # SQLite database storage
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Production Docker image
├── pyproject.toml        # Python dependencies
└── Makefile              # Automation commands
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

### Key Components

- **Chat Service**: Orchestrates LLM interactions with knowledge base search
- **Knowledge Base**: In-memory vector search using TF-IDF and cosine similarity
- **Session Management**: Persistent chat sessions with message history
- **OpenAI Integration**: GPT-4 with function calling for tool usage

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

## Production Considerations

### Kubernetes Features

- **HorizontalPodAutoscaler**: Scales 2-10 replicas based on CPU/memory
- **PodDisruptionBudget**: Ensures minimum availability during updates
- **NetworkPolicy**: Network isolation for security
- **Persistent Volumes**: Data and knowledge base persistence
- **Resource Limits**: CPU and memory constraints
- **Health Probes**: Liveness and readiness checks

### Performance

- Async I/O throughout the stack
- Connection pooling for database
- In-memory knowledge base caching
- Streaming responses for chat

### Monitoring

- Prometheus-compatible metrics annotations
- Structured logging (JSON in production)
- Health check endpoints
- Request/response logging

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Database Issues

```bash
# Reset database
rm data/qna_agent.db
make migrate-up
```

### Kubernetes Pod Not Starting

```bash
# Check pod status
kubectl get pods

# View pod logs
kubectl logs -l app=qna-agent-api

# Describe pod for events
kubectl describe pod <pod-name>
```

## Contributing

1. Format code: `make format`
2. Run tests: `make test`
3. Check types: `make type-check`
4. Ensure all checks pass before committing

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.