import os
import sys
import json
from mem0 import Memory

# Configuration for Mem0 (adjust paths/URLs if services are dockerized and called from another container)
# This configuration assumes Ollama and Qdrant are accessible.
# If this script is run from within an n8n Docker container, 'localhost' needs to resolve correctly
# to the host machine (for host-run Ollama/Qdrant) or to other containers in the same Docker network.
# For container-to-container, service names from docker-compose (e.g., 'http://qdrant:6333') are used.
# For container-to-host, 'host.docker.internal' can be used on Docker Desktop, or specific IP.
# For now, using localhost, assuming n8n might run on host or has network_mode: host for simplicity in dev.

MEM0_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", 6333)),
            "embedding_model_dims": 768, # nomic-embed-text
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": os.getenv("OLLAMA_LLM_MODEL", "llama3.1"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": os.getenv("OLLAMA_EMBEDDER_MODEL", "nomic-embed-text"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        },
    },
}

mem0_instance = None

def get_mem0_instance():
    global mem0_instance
    if mem0_instance is None:
        print(f"[DEBUG] Initializing Mem0 instance with config: {json.dumps(MEM0_CONFIG)}", file=sys.stderr)
        try:
            mem0_instance = Memory.from_config(MEM0_CONFIG)
            print("[DEBUG] Mem0 instance initialized successfully.", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Critical error initializing Mem0: {e}", file=sys.stderr)
            # Optionally, print traceback for more debug info
            # import traceback
            # traceback.print_exc(file=sys.stderr)
            sys.exit(1) # Exit as the script cannot function without Mem0
    return mem0_instance

def add_memory(data_to_add, user_id, metadata=None):
    """Adds memory to Mem0."""
    mem0 = get_mem0_instance()
    # Mem0's m.add() expects a list of messages or a string.
    # If data_to_add is a structured dict, convert to string or list of messages.
    # For now, assuming data_to_add is a string or can be directly processed.
    # Example: if data_to_add is a dict: `text_content = json.dumps(data_to_add)`

    text_content = data_to_add
    if isinstance(data_to_add, dict) or isinstance(data_to_add, list):
        text_content = json.dumps(data_to_add)

    print(f"[DEBUG] add_memory called for user_id: {user_id}, metadata: {metadata}", file=sys.stderr)
    # print(f"[DEBUG] Text content for add_memory: {text_content[:200]}...", file=sys.stderr) # Log snippet

    try:
        result = mem0.add(text_content, user_id=user_id, metadata=metadata)
        print(f"[DEBUG] mem0.add result: {result}", file=sys.stderr)
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"[ERROR] Error in add_memory for user_id {user_id}: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}

def search_memories(query, user_id):
    """Searches memories in Mem0."""
    mem0 = get_mem0_instance()
    print(f"[DEBUG] search_memories called for user_id: {user_id}, query: {query}", file=sys.stderr)
    try:
        results = mem0.search(query, user_id=user_id)
        print(f"[DEBUG] mem0.search results count: {len(results) if isinstance(results, list) else 'N/A'}", file=sys.stderr)
        return {"status": "success", "results": results}
    except Exception as e:
        print(f"[ERROR] Error in search_memories for user_id {user_id}: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}

def main():
    print(f"[DEBUG] mem0_handler.py called with args: {sys.argv}", file=sys.stderr)
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "message": "Usage: python mem0_handler.py <action> <payload_json_string>"}), file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]
    print(f"[DEBUG] Action: {action}", file=sys.stderr)

    try:
        payload_str = sys.argv[2]
        payload = json.loads(payload_str)
        print(f"[DEBUG] Payload: {json.dumps(payload)}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON payload: {e}. Payload string: {payload_str}"}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Error processing payload: {e}"}), file=sys.stderr)
        sys.exit(1)

    user_id = payload.get("user_id", os.getenv("DEFAULT_USER_ID", "lifeboard_user"))
    print(f"[DEBUG] Effective user_id: {user_id}", file=sys.stderr)


    if action == "add":
        data = payload.get("data")
        metadata = payload.get("metadata")
        if data is None:
            print(json.dumps({"status": "error", "message": "Missing 'data' in payload for add action"}), file=sys.stderr)
            sys.exit(1)
        result = add_memory(data, user_id, metadata)
        print(json.dumps(result)) # This is the script's stdout to n8n
    elif action == "search":
        query = payload.get("query")
        if query is None:
            print(json.dumps({"status": "error", "message": "Missing 'query' in payload for search action"}), file=sys.stderr)
            sys.exit(1)
        result = search_memories(query, user_id)
        print(json.dumps(result))
    elif action == "summarize":
        text_to_summarize = payload.get("text")
        prompt = payload.get("prompt", "Summarize the following text in a warm and reflective tone, like a personal newspaper highlight:")
        if text_to_summarize is None:
            print(json.dumps({"status": "error", "message": "Missing 'text' in payload for summarize action"}), file=sys.stderr)
            sys.exit(1)
        result = summarize_text_ollama(text_to_summarize, prompt, user_id) # Pass user_id for logging context
        print(json.dumps(result))
    elif action == "generate_chat_response":
        user_query = payload.get("query")
        context_memories = payload.get("context", [])

        prompt_template = payload.get("prompt_template",
            "You are a helpful AI assistant for the Lifeboard application. "
            "Based on the following relevant memories and the user's query, provide a concise and helpful response. "
            "If the memories are not relevant or insufficient, say you couldn't find specific information in the memories but try to answer generally if possible."
        )

        if user_query is None:
            print(json.dumps({"status": "error", "message": "Missing 'query' in payload for generate_chat_response action"}), file=sys.stderr)
            sys.exit(1)

        result = llm_chat_response_ollama(user_query, context_memories, prompt_template, user_id) # Pass user_id for logging context
        print(json.dumps(result))
    else:
        print(json.dumps({"status": "error", "message": f"Unknown action: {action}"}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()


# Helper function for summarization using Ollama (could be in a different module)
# This requires the 'ollama' Python package to be installed.
def summarize_text_ollama(text_content, prompt_template, user_id="N/A"): # Added user_id for context
    import ollama  # Ensure ollama is imported here or globally if preferred
    print(f"[DEBUG] summarize_text_ollama called for user_id: {user_id}", file=sys.stderr)
    # print(f"[DEBUG] Summarization text (first 200 chars): {text_content[:200]}...", file=sys.stderr)

    full_prompt = f"{prompt_template}\n\n---\n\nText to summarize:\n{text_content}\n\n---\n\nSummary:"

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_llm_model = os.getenv("OLLAMA_LLM_MODEL", "llama3.1")

    try:
        client = ollama.Client(host=ollama_base_url)
        response = client.chat(
            model=ollama_llm_model,
            messages=[
                {
                    'role': 'user',
                    'content': full_prompt,
                }
            ]
        )
        summary = response['message']['content']
        print(f"[DEBUG] Ollama summarization successful for user_id: {user_id}.", file=sys.stderr)
        return {"status": "success", "summary": summary.strip()}
    except Exception as e:
        print(f"[ERROR] Ollama summarization error for user_id {user_id}: {e}", file=sys.stderr)
        return {"status": "error", "message": f"Ollama summarization error: {str(e)}"}

def llm_chat_response_ollama(user_query, context_memories, prompt_template, user_id="N/A"): # Added user_id
    import ollama
    print(f"[DEBUG] llm_chat_response_ollama called for user_id: {user_id}, query: {user_query}", file=sys.stderr)

    context_str = "\n".join([str(mem) for mem in context_memories]) # Simple formatting for context
    if not context_str:
        context_str = "No specific memories found."
    # print(f"[DEBUG] Context for chat response (first 200 chars): {context_str[:200]}...", file=sys.stderr)


    full_prompt = (
        f"{prompt_template}\n\n"
        f"Relevant Memories:\n---\n{context_str}\n---\n\n"
        f"User Query: \"{user_query}\"\n\n"
        f"AI Response:"
    )
    # print(f"[DEBUG] Full prompt for LLM chat: {full_prompt}", file=sys.stderr)

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_llm_model = os.getenv("OLLAMA_LLM_MODEL", "llama3.1") # Or a model specifically for chat

    try:
        client = ollama.Client(host=ollama_base_url)
        print(f"[DEBUG] Attempting Ollama chat with model: {ollama_llm_model} at {ollama_base_url}", file=sys.stderr)
        response = client.chat(
            model=ollama_llm_model,
            messages=[
                {'role': 'user', 'content': full_prompt}
            ]
        )
        chat_reply = response['message']['content']
        print(f"[DEBUG] Ollama chat response successful for user_id: {user_id}.", file=sys.stderr)
        return {"status": "success", "reply": chat_reply.strip()}
    except Exception as e:
        print(f"[ERROR] Ollama chat response error for user_id {user_id}: {e}", file=sys.stderr)
        return {"status": "error", "message": f"Ollama chat response error: {str(e)}"}
