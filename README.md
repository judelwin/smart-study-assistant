# ClassGPT

A scalable, modular Retrieval-Augmented Generation (RAG) system designed for multi-class academic document ingestion, semantic search, and LLM-based Q&A.

## Overview

ClassGPT allows students and educators to:
- Upload academic documents (PDFs, slides, notes) organized by class
- Ask questions about course materials using natural language
- Receive generated answers with source citations
- Maintain separate knowledge bases for different courses

## Architecture

The system consists of several microservices:

- **Frontend**: React + Tailwind UI for file uploads and chat interface
- **Ingestion Service**: PDF parsing and OCR for document processing
- **Embedding Worker**: Converts text chunks to embeddings using Celery
- **Query Service**: RAG pipeline with semantic search and LLM integration
- **Vector Store**: Pinecone for embedding storage and retrieval
- **Database**: PostgreSQL for metadata and job tracking

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.9+ (for local development)

### Running with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd classgpt
```

2. Create a `.env` file in the project root and set the required environment variables. See the 'Configuration' section below for the full list of required variables (e.g., OPENAI_API_KEY, REDIS_URL, CELERY_REDIS_URL, DATABASE_URL, etc.).

3. Start all services:
```bash
docker-compose up -d
```

4. Access the application:
- Frontend: http://localhost:3000
- Query Service API: http://localhost:8000
- Vector Store: http://localhost:6333

### Local Development

1. Install dependencies for each service:
```bash
# Frontend
cd frontend
npm install

# Python services
cd ../ingestion-service
pip install -r requirements.txt

cd ../embedding-worker
pip install -r requirements.txt

cd ../query-service
pip install -r requirements.txt
```

2. Start services individually

## Project Structure

```
classgpt/
├── frontend/              # React + Tailwind UI
├── ingestion-service/     # PDF/slide parsing + OCR
├── embedding-worker/      # Celery worker for embedding jobs
├── query-service/         # RAG pipeline + search endpoint
├── shared/               # Common logic used across services
├── database/             # PostgreSQL schema and migrations
├── docker-compose.yml    # Service orchestration
└── README.md
```

## Configuration

Key environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key for LLM queries
- `REDIS_URL`: Redis connection string (Upstash recommended; use `rediss://` protocol)
- `CELERY_REDIS_URL`: (Optional, but required for Upstash) Redis connection string for Celery with `/0?ssl_cert_reqs=CERT_NONE` appended. See below.
- `DATABASE_URL`: PostgreSQL connection string
- `VECTOR_STORE_URL`: Pinecone connection string

## Example .env file

Create a `.env` file in the project root with the following variables:

```
# OpenAI API key for LLM queries
OPENAI_API_KEY=your-openai-api-key

# Redis connection strings
REDIS_URL=your-redis-url
CELERY_REDIS_URL=your-celery-redis-url

# PostgreSQL connection string
DATABASE_URL=your-postgresql-url

# Pinecone vector store
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=your-index-name

# AWS S3 for file storage
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_S3_BUCKET=your-s3-bucket
AWS_S3_REGION=your-s3-region

# Auth service and JWT
AUTH_SERVICE_URL=your-auth-service-url
JWT_SECRET_KEY=your-jwt-secret-key

# Frontend API URLs (for production deployment)
VITE_INGESTION_SERVICE_URL=https://your-ingestion-service-url.com
VITE_AUTH_SERVICE_URL=https://your-auth-service-url.com
VITE_QUERY_SERVICE_URL=https://your-query-service-url.com
```

## Usage

1. **Create a Class**: Use the class selector to create a new course
2. **Upload Documents**: Drag and drop PDFs, slides, or notes
3. **Ask Questions**: Type questions about your course materials
4. **Get Answers**: Receive AI-generated responses with source citations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+
- Python 3.9+

### Quick Start

1. **Start the backend services:**
   ```bash
   docker-compose up -d
   ```
   This starts all backend services (database, auth, ingestion, query, etc.)

2. **Start the frontend in development mode:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The frontend will run on `http://localhost:5173` with hot reloading and API proxying.

3. **Register and login:**
   - Visit `http://localhost:5173`
   - Register with any email/password
   - You'll be automatically logged in

### Why This Setup?

- **Frontend in dev mode**: Uses Vite's built-in proxy for API calls, making development seamless
- **Backend in Docker**: Ensures consistent environment and easy service orchestration
- **Production ready**: When deploying, each service gets its own URL, no proxy needed

### API Endpoints

- **Auth Service**: `http://localhost:8002` (via proxy `/auth/*`)
- **Ingestion Service**: `http://localhost:8001` (via proxy `/classes/*`, `/upload/*`, `/documents/*`)
- **Query Service**: `http://localhost:8000` (via proxy `/query/*`)

## Production Deployment

Each service can be deployed independently to your preferred cloud platform.

## Redis/Upstash and Celery Configuration

If you use Upstash Redis (recommended for production):

- Set `REDIS_URL` to your Upstash `rediss://` URL (no query params):
  ```
  REDIS_URL=rediss://default:<password>@<your-upstash-url>.upstash.io:6379
  ```
- Set `CELERY_REDIS_URL` to the same, but with `/0?ssl_cert_reqs=CERT_NONE` at the end:
  ```
  CELERY_REDIS_URL=rediss://default:<password>@<your-upstash-url>.upstash.io:6379/0?ssl_cert_reqs=CERT_NONE
  ```
- In Docker Compose, ensure both variables are passed to all Celery worker and backend services.
- This is required for Celery to connect to Upstash with SSL.

## Troubleshooting

**Celery/Redis SSL Error:**

If you see:
```
A rediss:// URL must have parameter ssl_cert_reqs and this must be set to CERT_REQUIRED, CERT_OPTIONAL, or CERT_NONE
```
Make sure your Celery worker and backend are using `CELERY_REDIS_URL` with the correct query parameter, and that it is passed in the Docker Compose environment.

**Document Deletion UX:**

When deleting a document, the UI now shows a "Deleting..." state and disables the delete button for that document until the operation completes. This prevents accidental multiple deletions and improves user experience.

## Security and Usage Limits

This application includes conservative rate limiting and usage quotas to prevent abuse and control costs for a personal project budget of $5-10/month:

### Rate Limits
- **File Uploads**: 10 uploads per hour per IP
- **Queries**: 30 queries per hour per IP  
- **Class Creation**: 5 classes per hour per IP
- **Login Attempts**: 10 attempts per hour per IP
- **Registrations**: 5 registrations per hour per IP

### Usage Quotas
- **File Size**: Maximum 10MB per file
- **Files per Upload**: Maximum 3 files per upload
- **Documents per User**: Maximum 50 documents per user
- **Classes per User**: Maximum 5 classes per user
- **Query Length**: Maximum 500 characters per query
- **Query Results**: Maximum 10 results per query

### Cost Control Measures
- OpenAI API responses limited to 500 tokens
- File size limits reduce S3 storage costs
- Rate limiting prevents API abuse
- User quotas prevent unlimited resource consumption

These limits are designed to keep monthly costs under $10 while allowing normal usage for personal/educational projects.



