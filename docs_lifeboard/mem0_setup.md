# Mem0 Setup for Lifeboard (Local-First)

This document outlines the setup for `mem0` as the memory/vector store for Lifeboard, focusing on a local-first deployment to align with project principles. This involves using self-hosted instances of Qdrant (for vector storage) and Ollama (for local LLM and embedding models).

## Dependencies

1.  **Docker and Docker Compose**: Essential for running the services.
2.  **Ollama**: Needs to be installed and running on the host machine, or run as a Docker container. For simplicity in initial setup, assume Ollama is running on the host at `http://localhost:11434`. Ensure you have pulled the necessary models:
    *   LLM: `ollama pull llama3.1` (or another suitable model)
    *   Embedding Model: `ollama pull nomic-embed-text` (or another suitable model, e.g., `snowflake-arctic-embed`)
    *   *Note*: The `embedding_model_dims` in the Qdrant configuration within Mem0 must match the dimensions of the chosen embedding model. For `nomic-embed-text`, this is typically 768.

## Services Overview (to be managed by Docker Compose later)

*   **Qdrant**: Vector database.
*   **Ollama**: (If containerized, otherwise host-run) Provides local LLM and embedding models.
*   **Lifeboard Application**: Will connect to Qdrant and Ollama.

## Qdrant Setup

Qdrant will be run as a Docker container. A service definition will be included in the main `docker-compose.yml`. For manual setup or testing:

```bash
# Pull the Qdrant image
docker pull qdrant/qdrant

# Run Qdrant, mapping port and persisting storage
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_data:/qdrant/storage:z \
    qdrant/qdrant
```
*(Note: `qdrant_data` will be a directory in your project root to persist Qdrant data).*

## Mem0 Python SDK Configuration

The Lifeboard application (likely via n8n workflows calling Python scripts or custom nodes) will use the `mem0ai` Python SDK.

1.  **Installation**: Add `mem0ai` to your `requirements.txt` and install.
    ```bash
    pip install mem0ai
    ```

2.  **Configuration for Local Usage (Python)**:

    ```python
    from mem0 import Memory

    # Ensure Ollama is running and models are pulled.
    # The ollama_base_url should point to your Ollama instance.
    # If Ollama is dockerized in the same network, this might be 'http://ollama:11434'.
    # If running on host from a dockerized app, special Docker networking might be needed (e.g., 'http://host.docker.internal:11434').

    MEM0_CONFIG = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": "localhost", # Or the Qdrant service name in Docker Compose (e.g., "qdrant")
                "port": 6333,
                # Important: Set dimensions for the chosen Ollama embedding model
                # For nomic-embed-text (default in example): 768
                # For snowflake-arctic-embed: 768
                "embedding_model_dims": 768,
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.1", # Or your chosen LLM model from Ollama
                "ollama_base_url": "http://localhost:11434", # Adjust if Ollama is containerized
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text", # Or your chosen embedding model from Ollama
                "ollama_base_url": "http://localhost:11434", # Adjust if Ollama is containerized
            },
        },
        # Optional: Configure history database path if needed
        # "history_db_path": "/path/to/mem0_history.db",
    }

    # Initialize Mem0
    mem0_instance = Memory.from_config(MEM0_CONFIG)

    # Example usage:
    # mem0_instance.add("Some memory text", user_id="lifeboard_user")
    # results = mem0_instance.search("Query text", user_id="lifeboard_user")
    ```

## Integration with n8n

How n8n interacts with this Mem0 setup:
*   **Python SDK via Code Node**: n8n's "Code" node can run Python. The `mem0ai` library and its dependencies would need to be available in the n8n Python environment.
*   **Custom n8n Node**: A more robust solution would be to develop a custom n8n node for Mem0 operations, which could internally use the `mem0ai` Python SDK (if n8n node development allows easy Python integration) or the `mem0` Node.js SDK.
*   **HTTP API**: If Mem0 OSS can expose an HTTP API (similar to its platform version), n8n could interact via HTTP Request nodes. The Python SDK quickstart implies `MemoryClient` for API interaction with the platform, but for OSS, direct SDK use is shown. The `mem0.proxy.main.Mem0` class in the docs might be relevant for an API, but the primary OSS approach seems to be SDK-based. For MVP, direct SDK usage from Python scripts called by n8n is likely the simplest.

This setup ensures that the memory operations, including vector storage, embedding generation, and LLM-based memory processing, all run locally, adhering to Lifeboard's design principles.
```
