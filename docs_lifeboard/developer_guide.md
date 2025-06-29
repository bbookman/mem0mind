# Lifeboard MVP - Developer Guide

This guide provides information for developers working on or extending the Lifeboard MVP.

## Project Structure Overview

*   `backend/`: Contains backend related logic.
    *   `n8n_custom/`: Dockerfile for the custom n8n image (includes Python environment).
    *   `n8n_scripts/`: Python helper scripts called by n8n workflows (e.g., `mem0_handler.py`).
    *   `n8n_workflows/`: JSON definitions of n8n workflows.
*   `config_lifeboard/`: Example configuration files (e.g., `config.example.env`).
*   `database/`:
    *   `Dockerfile`: For the PostgreSQL service (used by n8n).
    *   `init.sql`: SQL script to initialize Lifeboard-specific tables in the PostgreSQL database.
*   `docs_lifeboard/`: Project documentation.
*   `frontend/react_app/`: React frontend application.
    *   `Dockerfile`: For building and serving the React app with Nginx.
    *   `src/components/`: Core UI components.
    *   `.env.development`: Environment variables for React app (e.g., `REACT_APP_N8N_BASE_URL`).
*   `tests_lifeboard/`: Tests for the Lifeboard application.
    *   `deployment/`: Manual verification steps.
    *   `n8n_workflows/`: Pytest tests for n8n workflow structures and Python helper scripts.
    *   `setup/`: Pytest tests for initial project structure.
*   `docker-compose.yml`: Defines and orchestrates all application services.
*   `requirements.txt`: Python dependencies for helper scripts (e.g., `mem0ai`, `ollama`).
*   `requirements-dev.txt`: Python development dependencies (e.g., `pytest`).

## Local Development Setup

Refer to `docs_lifeboard/README.md` for initial setup using Docker Compose.

### Key Services and Ports (Defaults)

*   **Frontend (React/Nginx)**: `http://localhost:3000`
*   **n8n UI & Webhooks**: `http://localhost:5678`
*   **PostgreSQL**: `localhost:5432` (exposed to host, primarily for direct DB access if needed)
*   **Qdrant**: `http://localhost:6333` (HTTP API)
*   **Ollama**: `http://localhost:11434` (API)

### Environment Variables

Configuration is primarily managed via environment variables, typically set using a `.env` file in the project root (copied from `config_lifeboard/config.example.env`). Key variables include:

*   `N8N_ENCRYPTION_KEY`: **Must be set for n8n.**
*   PostgreSQL settings: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, etc. (for Lifeboard app data)
*   n8n database settings: `N8N_DB_USER`, `N8N_DB_PASSWORD`, `N8N_DB_NAME` (for n8n's own data)
*   Qdrant settings: `QDRANT_HOST` (service name `qdrant` in Docker), `QDRANT_PORT`.
*   Ollama settings: `OLLAMA_BASE_URL` (service name `http://ollama:11434` in Docker), `OLLAMA_LLM_MODEL`, `OLLAMA_EMBEDDER_MODEL`.
*   User settings: `USER_LATITUDE`, `USER_LONGITUDE`, `DEFAULT_USER_ID`.
*   React App: `REACT_APP_N8N_BASE_URL` (for API calls from frontend to n8n).

### n8n Workflow Development

1.  **Access n8n UI**: `http://localhost:5678`.
2.  **Workflows Location**: Workflows are defined in `backend/n8n_workflows/`. Due to the volume mount in `docker-compose.yml` (`./backend/n8n_workflows:/home/node/.n8n/workflows`), changes made locally to these JSON files should reflect in the running n8n instance (you might need to refresh the n8n browser tab or restart the n8n container if it caches aggressively).
    *   Alternatively, you can import/export workflows directly via the n8n UI.
3.  **Python Scripts**: The `mem0_handler.py` script is located at `/opt/lifeboard_scripts/mem0_handler.py` inside the n8n container. Ensure your "Execute Command" nodes in n8n use this absolute path.
    *   To modify this script, edit `backend/n8n_scripts/mem0_handler.py` locally. You'll need to rebuild the `n8n` Docker image (`docker-compose build n8n`) for changes to take effect, as the script is copied during the image build.
4.  **Debugging Workflows**: Use the n8n UI's execution log. Debug prints from the Python script (`mem0_handler.py`) sent to `stderr` will appear in the "Execute Command" node's output in the execution log.

### React Frontend Development

1.  **Development Server**: For hot-reloading and faster development cycles, you might want to run the React dev server directly on your host machine instead of the Dockerized Nginx version.
    *   `cd frontend/react_app`
    *   `yarn install` (or `npm install`)
    *   `yarn start` (or `npm start`)
    *   This will typically start the app on `http://localhost:3000`.
    *   Ensure your `.env.development` file in `frontend/react_app/` has `REACT_APP_N8N_BASE_URL=http://localhost:5678` so the dev server can correctly proxy requests to the n8n Docker container. You might need to set up a proxy in `frontend/react_app/src/setupProxy.js` or `package.json` if you encounter CORS issues or want cleaner API paths.
2.  **Docker Build**: To test the production build, use `docker-compose up --build frontend`.

## Data Source API Setup

For data ingestion workflows (Limitless, Bee.computer) to fetch real data, you need to configure API credentials.

*   **Preferred Method**: Use n8n's built-in Credentials manager.
    1.  In the n8n UI, go to "Credentials" > "Add credential".
    2.  Select the appropriate credential type (e.g., "Header Auth Credential" for API keys, or a specific app credential if available).
    3.  Enter your API key and any other required details.
    4.  In the n8n workflow's HTTP Request node, select the configured credential from the "Authentication" dropdown.
*   **Alternative (Environment Variables - less secure for keys)**:
    *   You can set API keys via environment variables in your `.env` file (e.g., `LIMITLESS_API_KEY=yourkey`).
    *   Modify the HTTP Request nodes in n8n to use `{{ $env.LIMITLESS_API_KEY }}`. This is generally not recommended for sensitive keys if the `.env` file might be accidentally committed or exposed.

Refer to the respective API documentation for obtaining keys:
*   **Limitless**: (Provide link or instructions if known)
*   **Bee.computer**: (Provide link or instructions if known)
*   **Weather API (Open-Meteo)**: No API key needed for the public API used in the example. Location is configured via `USER_LATITUDE` and `USER_LONGITUDE` environment variables.

## Mem0 and Local AI

*   **Mem0**: Uses the `mem0ai` Python library. Configuration is handled in `mem0_handler.py` via environment variables (see `QDRANT_*` and `OLLAMA_*` vars).
*   **Qdrant**: Vector database. Data is persisted in the `qdrant_data` Docker volume. Access its logs via `docker-compose logs qdrant`.
*   **Ollama**: Runs LLM and embedding models locally.
    *   Models are pulled using `docker-compose exec ollama ollama pull <model_name>`.
    *   Default models are specified by `OLLAMA_LLM_MODEL` and `OLLAMA_EMBEDDER_MODEL` environment variables.
    *   Data (pulled models) is persisted in the `ollama_data` Docker volume.
    *   Access logs via `docker-compose logs ollama`.

## Testing

*   **Python Tests**:
    *   Located in `tests_lifeboard/`.
    *   Run with `python -m pytest tests_lifeboard/` from the project root (after installing dependencies from `requirements.txt` and `requirements-dev.txt`).
*   **React Tests**:
    *   Located alongside components in `frontend/react_app/src/`.
    *   Run with `npm test` (or `yarn test`) from within the `frontend/react_app` directory.
*   **Manual Deployment Verification**: See `tests_lifeboard/deployment/MANUAL_VERIFICATION.md`.

This guide should help developers understand the project structure, set up their local environment, and contribute to the Lifeboard MVP.
