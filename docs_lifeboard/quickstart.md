# Lifeboard MVP - Quickstart Guide

This guide provides the minimal steps needed to get the Lifeboard MVP running locally using Docker and Docker Compose.

## Prerequisites

1.  **Docker and Docker Compose**: Must be installed and running.
2.  **Git**: For cloning the repository.
3.  **Terminal/Command Prompt**.

## Steps

1.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd lifeboard-mvp # Or your repository directory name
    ```

2.  **Configure Environment**:
    *   Copy the example environment file:
        ```bash
        cp config_lifeboard/config.example.env .env
        ```
    *   **Edit `.env`**:
        *   **Crucial**: Set a unique, secure `N8N_ENCRYPTION_KEY`.
        *   (Optional) Review and adjust other variables like `POSTGRES_USER/PASSWORD/DB`, `N8N_DB_USER/PASSWORD/NAME`, Ollama models (`OLLAMA_LLM_MODEL`, `OLLAMA_EMBEDDER_MODEL`), or user location (`USER_LATITUDE`, `USER_LONGITUDE`) if defaults are not suitable.

3.  **Build and Start Services**:
    *   From the project root directory, run:
        ```bash
        docker-compose up --build -d
        ```
    *   This command will:
        *   Build the custom Docker images for n8n and the frontend.
        *   Download official images for PostgreSQL, Qdrant, and Ollama.
        *   Start all services in detached mode.
    *   The initial build and download process may take several minutes.

4.  **Pull Ollama Models** (One-time setup per persistent Ollama volume):
    *   Once services are running (check `docker-compose ps`), execute the following in your terminal:
        ```bash
        docker-compose exec ollama ollama pull ${OLLAMA_LLM_MODEL:-llama3.1}
        docker-compose exec ollama ollama pull ${OLLAMA_EMBEDDER_MODEL:-nomic-embed-text}
        ```
        *(Adjust model names if you changed them in `.env`)*.
    *   Verify models are pulled: `docker-compose exec ollama ollama list`

5.  **Access Services**:
    *   **Lifeboard Frontend**: Open your web browser to `http://localhost:3000`
    *   **n8n UI**: Open `http://localhost:5678`
        *   On first access, set up your n8n admin user.
        *   Workflows from `backend/n8n_workflows/` should be loaded due to volume mounts. Activate them if necessary.

6.  **Using Lifeboard**:
    *   **Data Ingestion**:
        *   Manually trigger ingestion workflows (Limitless, Bee.computer) via the n8n UI for initial data if not waiting for schedule. Requires API credentials configured in n8n.
        *   Submit mood data via webhook (find URL in `ingestion_mood` workflow in n8n).
    *   **Explore**:
        *   Use the calendar on the frontend (`http://localhost:3000`) to view daily summaries.
        *   Interact with the AI chat widget.

7.  **Stopping Services**:
    *   To stop all services:
        ```bash
        docker-compose down
        ```
    *   To stop and remove data volumes (for a completely fresh start):
        ```bash
        docker-compose down -v
        ```

This completes the quickstart setup. Refer to `README.md` and `developer_guide.md` in this directory for more detailed information.
