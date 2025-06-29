import json
import os

WORKFLOW_DIR = "backend/n8n_workflows"
EXPECTED_WORKFLOW_FILES = [
    "ingestion_limitless.json",
    "ingestion_bee_computer.json",
    "ingestion_weather.json",
    "ingestion_mood.json",
    "query_daily_view.json",
    "query_chat_interface.json",
    "generate_daily_summary.json"
]

# Add generate_daily_summary.json to EXPECTED_WORKFLOW_FILES if not already by mistake
if "generate_daily_summary.json" not in EXPECTED_WORKFLOW_FILES:
    EXPECTED_WORKFLOW_FILES.append("generate_daily_summary.json")

def load_workflow_json(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        assert False, f"Failed to load or parse JSON from {file_path}: {e}"

def test_all_workflow_files_exist():
    for file_name in EXPECTED_WORKFLOW_FILES:
        file_path = os.path.join(WORKFLOW_DIR, file_name)
        assert os.path.exists(file_path), f"Workflow file {file_path} does not exist."
        assert os.path.isfile(file_path), f"Workflow path {file_path} is not a file."

def test_workflow_json_validity_and_basic_structure():
    for file_name in EXPECTED_WORKFLOW_FILES:
        file_path = os.path.join(WORKFLOW_DIR, file_name)
        if not os.path.exists(file_path): # Skip if file doesn't exist (covered by previous test)
            continue

        data = load_workflow_json(file_path)

        assert "name" in data, f"'name' missing in {file_name}"
        assert "nodes" in data, f"'nodes' missing in {file_name}"
        assert isinstance(data["nodes"], list), f"'nodes' is not a list in {file_name}"
        assert len(data["nodes"]) > 0, f"'nodes' list is empty in {file_name}"
        assert "connections" in data, f"'connections' missing in {file_name}"

        # Check for ExecuteCommand node calling mem0_handler.py
        execute_command_nodes = [
            node for node in data["nodes"]
            if node.get("type") == "n8n-nodes-base.executeCommand" and \
               "mem0_handler.py" in node.get("parameters", {}).get("command", "")
        ]

        # Ingestion and Query workflows should have at least one such node
        # Mood ingestion has one, Weather has one, Limitless has one, Bee has one
        # Daily view has one, Chat has one
        assert len(execute_command_nodes) >= 1, f"No ExecuteCommand node calling mem0_handler.py found in {file_name}"

        for ec_node in execute_command_nodes:
            params = ec_node.get("parameters", {})
            command = params.get("command", "")
            assert command.startswith("python backend/n8n_scripts/mem0_handler.py"), f"Command in {file_name} does not start correctly: {command}"
            action = command.split(" ")[2] # python script_path action '{...}'
            assert action in ["add", "search", "summarize", "generate_chat_response"], f"Invalid action '{action}' in command in {file_name}"

            # Check for presence of env vars in options (basic check)
            options = params.get("options", {})
            assert "env" in options, f"'env' missing in ExecuteCommand options in {file_name} for node {ec_node.get('name')}"
            assert "QDRANT_HOST" in options["env"], f"'QDRANT_HOST' missing in env options in {file_name}"
            assert "OLLAMA_BASE_URL" in options["env"], f"'OLLAMA_BASE_URL' missing in env options in {file_name}"


def test_specific_workflow_triggers():
    # Ingestion Limitless
    wf_path = os.path.join(WORKFLOW_DIR, "ingestion_limitless.json")
    if os.path.exists(wf_path):
      data = load_workflow_json(wf_path)
      cron_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.cron"]
      assert len(cron_nodes) == 1, "Limitless ingestion should have one Cron trigger"

    # Ingestion Mood
    wf_path = os.path.join(WORKFLOW_DIR, "ingestion_mood.json")
    if os.path.exists(wf_path):
      data = load_workflow_json(wf_path)
      webhook_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
      assert len(webhook_nodes) == 1, "Mood ingestion should have one Webhook trigger"

    # Query Daily View
    wf_path = os.path.join(WORKFLOW_DIR, "query_daily_view.json")
    if os.path.exists(wf_path):
      data = load_workflow_json(wf_path)
      webhook_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
      assert len(webhook_nodes) == 1, "Daily View query should have one Webhook trigger"

    # Query Chat Interface
    wf_path = os.path.join(WORKFLOW_DIR, "query_chat_interface.json")
    if os.path.exists(wf_path):
      data = load_workflow_json(wf_path)
      webhook_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
      assert len(webhook_nodes) == 1, "Chat query should have one Webhook trigger"
      function_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.function"]
      assert len(function_nodes) >= 1, "Chat query should have at least one Function node for formatting"
      # Should have two executeCommand nodes: one for search, one for LLM response
      ec_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.executeCommand"]
      assert len(ec_nodes) == 2, "Chat query should have two ExecuteCommand nodes"


    # Generate Daily Summary
    wf_path = os.path.join(WORKFLOW_DIR, "generate_daily_summary.json")
    if os.path.exists(wf_path):
      data = load_workflow_json(wf_path)
      webhook_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.webhook"]
      assert len(webhook_nodes) == 1, "Daily Summary should have one Webhook trigger"
      function_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.function"]
      assert len(function_nodes) >= 1, "Daily Summary should have a Function node for formatting"
      ec_nodes = [n for n in data["nodes"] if n.get("type") == "n8n-nodes-base.executeCommand"]
      assert len(ec_nodes) == 2, "Daily Summary should have two ExecuteCommand nodes (search & summarize)"
