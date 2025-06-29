# Manual Verification Steps for Packaging and Deployment

These steps are to be performed manually by a user in an environment with Docker and Docker Compose installed to verify the packaging and local deployment of the Lifeboard MVP.

## Prerequisites

1.  Ensure Docker and Docker Compose are installed and running.
2.  Clone the repository.
3.  Copy `config_lifeboard/config.example.env` to `.env` in the project root (or `config_lifeboard/.env` if `docker-compose.yml` is adjusted to look there for `env_file`).
    *   Review the `.env` file and update any necessary configurations (e.g., `N8N_ENCRYPTION_KEY`, any actual API keys if you choose to test with them instead of relying on n8n credentials UI).
    *   Ensure `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` in `.env` match what `database/init.sql` might expect if it had user-specific commands (currently it uses defaults that match).
    *   Ensure n8n database credentials in `.env` (`N8N_DB_USER`, `N8N_DB_PASSWORD`, `N8N_DB_NAME`) are set.

## Verification Steps

### 1. Docker Compose Configuration and Build

*   **Action**: Open a terminal in the project root directory.
*   **Command**: `docker-compose config`
*   **Expected Outcome**: The command should execute without errors, and the parsed `docker-compose.yml` configuration should be printed. This verifies syntactical correctness.
*   **Command**: `docker-compose build`
*   **Expected Outcome**: All services defined with a `build` instruction (`n8n`, `frontend`) should build successfully without errors. This verifies the Dockerfiles are correct.

### 2. Service Startup

*   **Action**: In the same terminal.
*   **Command**: `docker-compose up -d` (to run in detached mode)
*   **Expected Outcome**:
    *   All services (postgres, qdrant, ollama, n8n, frontend) should start without immediate exit or errors.
    *   Check logs for each service: `docker-compose logs postgres`, `docker-compose logs qdrant`, etc.
    *   PostgreSQL logs should indicate the database system is ready and `init.sql` has been executed (if it produces noticeable log output).
    *   Qdrant logs should indicate it's ready to accept connections.
    *   Ollama logs should indicate it's running. (Note: Models need to be pulled separately).
    *   n8n logs should show it connecting to the database and starting its web server.
    *   Frontend (Nginx) logs should show it's serving on its port.

### 3. Pull Ollama Models (One-time setup if not pre-baked into image)

*   **Action**: If this is the first time running or `ollama_data` volume is new.
*   **Command 1**: `docker-compose exec ollama ollama pull ${OLLAMA_LLM_MODEL:-llama3.1}` (replace with actual model from `.env` if different)
*   **Command 2**: `docker-compose exec ollama ollama pull ${OLLAMA_EMBEDDER_MODEL:-nomic-embed-text}` (replace with actual model from `.env` if different)
*   **Expected Outcome**: Ollama should download the specified models.

### 4. Basic Service Accessibility

*   **n8n UI**:
    *   **Action**: Open a web browser and navigate to `http://localhost:5678` (or the port configured for n8n).
    *   **Expected Outcome**: The n8n setup/login screen should appear. You should be able to set up an admin account and access the n8n dashboard.
*   **Frontend UI**:
    *   **Action**: Open a web browser and navigate to `http://localhost:3000` (or the port configured for the frontend).
    *   **Expected Outcome**: The Lifeboard React application's main page should load (showing the calendar view by default).
*   **Qdrant API (Optional Check)**:
    *   **Action**: Navigate to `http://localhost:6333` (or Qdrant port).
    *   **Expected Outcome**: Should see a Qdrant welcome message or API endpoint listing.
*   **Ollama API (Optional Check)**:
    *   **Action**: Navigate to `http://localhost:11434/api/tags` (or Ollama port).
    *   **Expected Outcome**: A JSON response listing available Ollama models (should include those pulled in step 3).

### 5. Workflow Verification (Manual Interaction)

*   **Access n8n Workflows**:
    *   **Action**: In the n8n UI, check if the Lifeboard workflows (e.g., "Ingest Mood Data", "Generate Daily Summary", "Query Chat Interface") are present. They should be due to the volume mount `./backend/n8n_workflows:/home/node/.n8n/workflows`. Activate them if they are not active by default.
*   **Test Mood Ingestion**:
    *   **Action**: Find the webhook URL for the "Ingest Mood Data" workflow (from n8n UI or by constructing it, e.g., `http://localhost:5678/webhook/{{ $env.MOOD_WEBHOOK_ID }}`). Send a POST request to it with a JSON body like `{"mood_rating": 5, "notes": "Feeling great today!"}` using a tool like `curl` or Postman.
    *   **Expected Outcome**:
        *   The n8n workflow execution log should show a successful run.
        *   Debug logs from `mem0_handler.py` (action: add) should appear in the "Execute Command" node's output in the n8n execution log.
        *   (Advanced) Check Qdrant logs or UI (if available) to see if a new vector/point was added.
*   **Test Daily Summary and Chat (via Frontend)**:
    *   **Action**: In the Lifeboard frontend UI:
        1.  Navigate the calendar to a day.
        2.  Observe if a daily summary is fetched and displayed. Check browser console and n8n logs for "Generate Daily Summary" workflow execution.
        3.  Use the Chat Widget to send a message.
    *   **Expected Outcome**:
        *   A daily summary should appear (even if basic, from the LLM).
        *   The chat widget should show your message and then an AI-generated response.
        *   N8n execution logs for "Generate Daily Summary" and "Query Chat Interface" should show successful runs, including debug output from `mem0_handler.py` (search, summarize, generate_chat_response actions).
        *   Ollama service logs (`docker-compose logs ollama`) should show activity related to model usage if calls are reaching it.

### 6. Data Persistence

*   **Action**:
    1.  Run the application, ingest some data (e.g., moods).
    2.  Stop the services: `docker-compose down`
    3.  Restart the services: `docker-compose up -d`
    4.  Access the application again.
*   **Expected Outcome**:
    *   Previously ingested mood data should still be queryable (e.g., reflected in daily summaries or chat responses if relevant).
    *   n8n should retain its configuration and workflows.
    *   Ollama should retain its pulled models (check with `docker-compose exec ollama ollama list`).
    *   This verifies that the volume mounts (`postgres_data`, `qdrant_data`, `ollama_data`, `n8n_data`) are working.

### 7. Configuration Loading Check

*   **Action**: Modify a non-sensitive setting in your `.env` file (e.g., `DEFAULT_USER_ID`). Restart the relevant service(s) (`docker-compose up -d --force-recreate n8n` or all services).
*   **Expected Outcome**: Observe if the application behavior or logs reflect the changed configuration (e.g., debug logs in `mem0_handler.py` showing the new default user ID). This confirms the `.env` file is being loaded and used.

## Cleanup

*   **Command**: `docker-compose down -v` (the `-v` flag removes named volumes, deleting persisted data).
*   **Action**: Use this when you want to start completely fresh. Omit `-v` to keep data.

These manual steps provide a reasonable way to test if the packaged application deploys and operates as expected in a local Docker environment.
