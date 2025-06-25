# Unified Memory Application

A comprehensive memory management system that processes markdown files to extract facts and provides interactive chat functionality with stored memories.

## Features

- 📁 **Configurable Directory Processing**: Process multiple markdown directories
- 🧠 **Intelligent Fact Extraction**: Uses LLM to extract meaningful facts from conversations
- 💬 **Interactive Chat**: Chat with your memories using natural language
- 🔧 **Modular Architecture**: Clean separation of concerns with reusable components
- ⚙️ **JSON Configuration**: Easy configuration management
- 🔄 **Retry Logic**: Robust error handling and retry mechanisms
- 📝 **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Architecture

The application consists of three main modules:

1. **`memory_manager.py`** - Core memory operations (add, search, chat, reset)
2. **`markdown_processor.py`** - Markdown parsing and fact extraction
3. **`memory_app.py`** - Main application with CLI interface

## Configuration

Edit `config.json` to configure your setup:

```json
{
  "memory_config": {
    "vector_store": {
      "provider": "qdrant",
      "config": {
        "collection_name": "unified_memories",
        "host": "localhost",
        "port": 6333,
        "embedding_model_dims": 768
      }
    },
    "llm": {
      "provider": "ollama",
      "config": {
        "model": "llama3.1:latest",
        "temperature": 0.1,
        "max_tokens": 2000,
        "ollama_base_url": "http://localhost:11434"
      }
    },
    "embedder": {
      "provider": "ollama",
      "config": {
        "model": "nomic-embed-text:latest",
        "ollama_base_url": "http://localhost:11434"
      }
    }
  },
  "markdown_directories": [
    "/path/to/your/conversations",
    "/path/to/your/notes",
    "/path/to/your/journal"
  ],
  "processing_options": {
    "recursive": true,
    "file_extensions": [".md", ".markdown"],
    "user_id": "bruce",
    "batch_size": 10,
    "delay_between_batches": 1.0
  }
}
```

## Prerequisites

1. **Qdrant Vector Database** running on localhost:6333
2. **Ollama** running on localhost:11434 with required models:
   - `llama3.1:latest`
   - `nomic-embed-text:latest`
3. **Python Dependencies**:
   ```bash
   pip install mem0ai requests pathlib
   ```

## Usage

### 1. Process Markdown Files

Extract facts from your markdown files and create memories:

```bash
python memory_app.py process --config config.json --user bruce
```

This will:
- Read all markdown files from configured directories
- Extract conversation entries with timestamps
- Use LLM to extract factual statements
- Store facts as searchable memories

### 2. Interactive Chat

Chat with your stored memories:

```bash
python memory_app.py chat --config config.json --user bruce
```

Chat commands:
- Ask questions: `"What do I like to eat?"`
- View all memories: `memories`
- Reset memories: `reset`
- Exit: `exit`, `quit`, or `q`

### 3. Reset Memories

Clear all memories for a user:

```bash
python memory_app.py reset --config config.json --user bruce
```

Add `--force` to skip confirmation prompt.

## Example Workflow

1. **Setup Configuration**:
   ```bash
   # Edit config.json with your markdown directories
   nano config.json
   ```

2. **Process Your Files**:
   ```bash
   python memory_app.py process --config config.json
   ```

3. **Start Chatting**:
   ```bash
   python memory_app.py chat --config config.json
   ```

4. **Example Chat Session**:
   ```
   💭 Found 25 memories for bruce
   🤖 Memory Chat - Ask questions about your stored information
   ============================================================
   
   bruce> What do I like to eat?
   🤔 Thinking...
   🤖 Bruce loves pizza! It's actually his go-to food.
   
   bruce> Where do I work?
   🤔 Thinking...
   🤖 Bruce works at Walgreens as a customer service representative.
   
   bruce> memories
   📚 All memories for bruce:
    1. Bruce's favorite food is pizza
    2. Works at Walgreens
    3. Lives in Wilmington, NC
   ...
   
   bruce> exit
   Goodbye! 👋
   ```

## Markdown Format

The processor expects markdown files with timestamped conversation entries:

```markdown
# Meeting with John
- 3/29/25 9:10 AM: Discussed the new project timeline
- 3/29/25 9:15 AM: John mentioned he prefers working remotely
- 3/29/25 9:20 AM: We agreed to meet weekly on Fridays

## Personal Notes
- 3/29/25 2:30 PM: I really enjoyed the pizza at Mario's restaurant
- 3/29/25 3:00 PM: Need to remember to call mom this weekend
```

## Logging

Logs are written to both console and file (configurable in `config.json`):
- Processing progress and statistics
- Memory addition success/failure
- Chat interactions
- Error details for debugging

## Error Handling

The application includes comprehensive error handling:
- Retry logic for memory operations
- Graceful handling of malformed markdown
- Connection error recovery
- Detailed error logging

## Troubleshooting

1. **"No memories found"**: Run the `process` command first
2. **Connection errors**: Ensure Qdrant and Ollama are running
3. **No facts extracted**: Check your markdown format and LLM responses
4. **Permission errors**: Ensure directories in config are readable

## Development

To extend the application:
- Add new processors in `markdown_processor.py`
- Extend memory operations in `memory_manager.py`
- Add new CLI commands in `memory_app.py`
