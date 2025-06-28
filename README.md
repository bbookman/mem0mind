# Lifeboard - Unified Memory Application

Powered by the **Digital Memoir Engine** (DME), Lifeboard is an interactive reflection space and powerful planning assistant. It seamlessly pulls from your digital history—concerts attended, music loved, thoughts shared, places visited, meetings attended—transforming each day into a personal newspaper. With a customizable AI, you can rediscover meaning in the everyday and take control of your future journey.

This README provides guidance on how to build, run, and use the application, including details on its command-line interface and prompt management system.

## Table of Contents
- [Overview](#overview)
- [Building and Running with Docker](#building-and-running-with-docker)
  - [Prerequisites](#prerequisites)
  - [Building the Docker Image](#building-the-docker-image)
  - [Running the Docker Container](#running-the-docker-container)
  - [Persisting Data](#persisting-data)
- [Command Line Switches](#command-line-switches)
  - [Main Commands](#main-commands)
    - [`process`](#1-process)
    - [`chat`](#2-chat)
    - [`reset`](#3-reset)
- [Prompt Management System](#prompt-management-system)
  - [Overview](#overview-1)
  - [Directory Structure](#directory-structure)
  - [How Prompts Are Used](#how-prompts-are-used)
  - [Using Prompts in Code (for Developers/Advanced Users)](#using-prompts-in-code-for-developersadvanced-users)
  - [Customizing Prompts](#customizing-prompts)
  - [Adding New Prompts](#adding-new-prompts)
- [Architecture Principles](#architecture-principles)
- [Resources](#resources)
- [Contributing](#contributing)

## Overview

The Unified Memory Application is a powerful tool designed to help you manage and interact with your information. It allows you to process markdown files, extract key facts, and store them as memories. You can then chat with an AI that uses these memories to provide context-aware responses.

Core functionalities include:

*   **Processing Markdown Files**: The application can scan directories containing markdown files (.md). It extracts information from these files, identifies key facts, and stores them in a memory system. This is useful for building a knowledge base from your notes, documents, or conversation logs.
*   **Interactive Chat**: Once memories are stored, you can engage in an interactive chat session. The AI will use the information from your memories to answer questions, provide summaries, or discuss topics based on the content you've processed.
*   **Memory Management**: You have control over your memories. The application allows you to reset or clear all stored memories for a specific user, enabling you to start fresh or manage different sets of information.

## Building and Running with Docker

This application can be easily built and run using Docker.

### Prerequisites

*   Docker installed on your system.

### Building the Docker Image

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository-url> # Replace <repository-url> with the actual URL
    cd <repository-directory> # Replace <repository-directory> with the cloned directory name
    ```

2.  **Build the Docker image:**
    Open your terminal in the root directory of the project (where the `Dockerfile` is located) and run:
    ```bash
    docker build -t memory-app .
    ```
    This command tells Docker to build an image from the `Dockerfile` in the current directory (`.`) and tag it (`-t`) with the name `memory-app`.

### Running the Docker Container

Once the image is built, you can run the application in a Docker container.

1.  **Basic Run Command:**
    To run the application, you'll typically use `docker run`. You'll also need to mount your configuration file and any directories the app needs to access (like your markdown notes).

    For example, if your `config.json` is in the current directory and your notes are in a directory named `my_notes`:

    ```bash
    docker run -it --rm \
        -v "$(pwd)/config.json":/app/config.json \
        -v "$(pwd)/my_notes":/app/my_notes \
        memory-app <command> [options]
    ```

    Let's break down this command:
    *   `docker run`: The command to run a container.
    *   `-it`: Runs the container in interactive mode (`-i`) and allocates a pseudo-TTY (`-t`), which is necessary for interactive commands like `chat`.
    *   `--rm`: Automatically removes the container when it exits.
    *   `-v "$(pwd)/config.json":/app/config.json`: Mounts your local `config.json` file into the `/app/config.json` path inside the container. **Note:** Ensure your `config.json` paths for markdown directories are set relative to how they'll appear *inside the container* (e.g., `/app/my_notes`).
    *   `-v "$(pwd)/my_notes":/app/my_notes`: Mounts your local `my_notes` directory into the `/app/my_notes` path inside the container.
    *   `memory-app`: The name of the image to use.
    *   `<command> [options]`: The command you want to run inside the container (e.g., `process`, `chat`) followed by its specific options. See the "Command Line Switches" section for details.

2.  **Example: Processing Markdown Files:**
    Assuming your `config.json` is configured to read from a directory `/app/markdown_source` inside the container, and your local notes are in `~/Documents/MyNotes`:
    ```bash
    docker run --rm \
        -v "$(pwd)/config.json":/app/config.json \
        -v "$HOME/Documents/MyNotes":/app/markdown_source \
        memory-app process --user myuser
    ```

3.  **Example: Starting an Interactive Chat Session:**
    ```bash
    docker run -it --rm \
        -v "$(pwd)/config.json":/app/config.json \
        memory-app chat --user myuser
    ```
    *   Note: For the chat command, you generally don't need to mount markdown directories unless your `config.json` or memory storage relies on paths that need to be present. The memories themselves should be persisted elsewhere (e.g., a database or a mounted volume if using file-based storage for memories, which depends on `MemoryManager`'s implementation).

### Persisting Data

The `MemoryManager` handles how memories are stored. If it stores memories in files within the container's filesystem, these memories will be lost when the container stops (especially with `--rm`). To persist memories:

*   **Mount a volume for memory storage:** If memories are stored in a specific directory (e.g., `/app/memories_db`), mount a local directory or a Docker named volume to that path:
    ```bash
    docker run -it --rm \
        -v "$(pwd)/config.json":/app/config.json \
        -v "$(pwd)/my_local_memories_db":/app/memories_db \ # Example path
        memory-app chat --user myuser
    ```
    You'll need to check how `MemoryManager` in this project persists data and adjust the volume mount accordingly. The `config.json` might also specify paths for data storage that need to be considered for volume mounting.

## Command Line Switches

The application is controlled via command-line arguments. You can invoke it using `python memory_app.py <command> [options]`, or if using Docker, `docker run ... memory-app <command> [options]`.

To see the help message with all available commands and options, run:
```bash
python memory_app.py --help
```
or
```bash
docker run --rm memory-app --help
```

### Main Commands

The application has three main commands: `process`, `chat`, and `reset`.

#### 1. `process`

This command processes markdown files from configured directories, extracts facts, and creates memories.

**Usage:**
```bash
python memory_app.py process [options]
```

**Options:**

*   `--config <path>`, `-c <path>`
    *   Path to the configuration file.
    *   Default: `config.json`
*   `--user <user_id>`, `-u <user_id>`
    *   User ID for whom the memories will be processed and stored.
    *   This overrides any `user_id` specified in the `config.json` under `processing_options`.
    *   If not provided, it defaults to the `user_id` in `config.json` or 'default' if not found there.

**Example:**
```bash
python memory_app.py process --config my_config.json --user alice
```
```bash
docker run --rm -v "$(pwd)/my_config.json":/app/config.json -v "$(pwd)/notes":/app/notes memory-app process --config /app/config.json --user alice
```

#### 2. `chat`

This command starts an interactive chat session, allowing you to ask questions and get responses based on the stored memories.

**Usage:**
```bash
python memory_app.py chat [options]
```

**Options:**

*   `--config <path>`, `-c <path>`
    *   Path to the configuration file.
    *   Default: `config.json`
*   `--user <user_id>`, `-u <user_id>`
    *   User ID whose memories will be used for the chat session.
    *   This overrides any `user_id` specified in the `config.json`.
    *   If not provided, it defaults to the `user_id` in `config.json` or 'default' if not found there.

**Interactive Commands within Chat:**
Once in the chat session, you can use the following special commands:
    *   `exit`, `quit`, `q`: Exit the chat session.
    *   `memories`: Display all stored memories for the current user.
    *   `reset`: Prompts to delete all memories for the current user.

**Example:**
```bash
python memory_app.py chat --user bob
```
```bash
docker run -it --rm -v "$(pwd)/config.json":/app/config.json memory-app chat --user bob
```

#### 3. `reset`

This command deletes all memories associated with a specific user.

**Usage:**
```bash
python memory_app.py reset [options]
```

**Options:**

*   `--config <path>`, `-c <path>`
    *   Path to the configuration file.
    *   Default: `config.json`
*   `--user <user_id>`, `-u <user_id>`
    *   User ID whose memories will be deleted.
    *   This overrides any `user_id` specified in the `config.json`.
    *   If not provided, it defaults to the `user_id` in `config.json` or 'default' if not found there.
*   `--force`, `-f`
    *   Skip the confirmation prompt before deleting memories. Use with caution.

**Example:**
```bash
python memory_app.py reset --user charlie --force
```
```bash
docker run --rm -v "$(pwd)/config.json":/app/config.json memory-app reset --user charlie --force
```

## Prompt Management System

The application features a robust prompt management system that centralizes all AI prompts. This allows for easy customization and maintenance of the AI's behavior without altering the core application code.

### Overview

*   **Organized Structure**: Prompts are organized into categories within the `prompts/` directory (e.g., `chat`, `extraction`).
*   **Template Support**: Prompts are text files that can include variables using the `${variable_name}` or `$variable_name` syntax. These variables are substituted with dynamic values at runtime.
*   **Automatic Loading**: The system automatically discovers and loads prompt files (`.txt`, `.json`, `.yaml`).
*   **Caching**: Loaded prompts are cached for performance.

### Directory Structure

Prompts are located in the `prompts/` directory, categorized as follows:

```
prompts/
├── chat/                   # Prompts for user interactions and chat functionality
│   ├── user_interaction.txt    # Main chat prompt
│   ├── no_memories.txt         # Response when no relevant memories are found
│   └── error_response.txt      # Prompts for handling chat errors
├── extraction/             # Prompts for extracting facts from various sources
│   ├── markdown_facts.txt      # For extracting facts from markdown files
│   └── conversation_facts.txt  # For extracting facts from conversation entries
├── processing/             # Prompts for data processing operations
│   └── data_validation.txt     # Example: for validating extracted data
├── system/                 # System-level prompts (e.g., error analysis)
│   └── error_analysis.txt      # Example: for analyzing system errors
└── PROMPT_SYSTEM_GUIDE.md  # Detailed guide to the prompt system
```
Each category directory also contains a `README.md` explaining the purpose and variables for the prompts within that category.

### How Prompts Are Used

The application uses these prompts to instruct the AI on how to behave in different situations. For example:
*   The `chat/user_interaction.txt` prompt guides how the AI responds to user queries during a chat session.
*   The `extraction/markdown_facts.txt` prompt defines how facts should be identified and extracted from markdown content.

### Using Prompts in Code (for Developers/Advanced Users)

If you are extending the application or want to understand its internals, here's how prompts are typically accessed:

The `prompt_manager.py` module provides functions to retrieve and format prompts.

**1. Getting the Prompt Manager:**
```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()
```

**2. Getting a Specific Prompt:**
You can fetch a prompt by its category and name (which is the filename without the extension). Variables are passed as keyword arguments.

```python
from prompt_manager import get_prompt

# Example: Get the main chat interaction prompt
try:
    chat_prompt_template = get_prompt(
        category='chat',
        name='user_interaction',
        user_id='TestUser',
        context='Some relevant facts or context here.',
        query='What is the meaning of life?'
    )
    print(chat_prompt_template)
except ValueError as e:
    print(f"Error getting prompt: {e}")
```

**3. Listing Categories and Prompts:**
```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()

# List all available categories
categories = pm.list_categories()
print(f"Available categories: {categories}")

# List all prompts within the 'extraction' category
extraction_prompts = pm.list_prompts('extraction')
print(f"Extraction prompts: {extraction_prompts}")
```

**4. Getting Prompt Information:**
You can get metadata about a prompt, including the variables it expects.
```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()

try:
    info = pm.get_prompt_info('chat', 'user_interaction')
    print(f"Prompt: {info['category']}/{info['name']}")
    print(f"File: {info['file']}")
    print(f"Expected variables: {info['variables']}")
    # print(f"Content: {info['content']}") # Full content
except ValueError as e:
    print(f"Error getting prompt info: {e}")
```

### Customizing Prompts

1.  **Locate the Prompt**: Find the prompt file you want to modify in the `prompts/` directory (e.g., `prompts/chat/user_interaction.txt`).
2.  **Edit the File**: Open the `.txt` file and change the text. You can modify the wording, structure, or instructions given to the AI.
    *   Be mindful of existing variables (e.g., `${user_id}`, `${context}`, `${query}`). Ensure they remain if the application logic relies on them.
    *   You can refer to the `README.md` in each prompt category directory or the main `prompts/PROMPT_SYSTEM_GUIDE.md` for details on variables.
3.  **Save Changes**: Save the file.
4.  **Test**: The application should pick up the changes automatically on the next run. For long-running applications or development, the `PromptManager` has a `reload_prompts()` method that can be called programmatically.

### Adding New Prompts

1.  **Create a File**: Add a new `.txt` (or `.json`/`.yaml` if you extend the loader) file in the appropriate category directory (e.g., `prompts/chat/my_new_chat_prompt.txt`).
2.  **Write Content**: Add the prompt text, using variables as needed.
3.  **Use in Code**: If you're developing, call `get_prompt('category', 'my_new_chat_prompt', **variables)` in your Python code where needed.

For more detailed information, refer to the `prompts/PROMPT_SYSTEM_GUIDE.md` file within the repository.

## Architecture Principles
- Extremely low cost or free
- Novice facing if at all possible
- Leverage both AI and non-AI solutions (example nltk)
- Extreme modularity and extensability: future-proof design. Today mem0, tomorrow Langchain.. today SQLlite, tomorrow Postgres
- Extreme abstracion and encapsulation

## Resources
- `/supporting documents/`
- `/supporting documents/Design/Plan.md`
- [UseCortex](https://usecortex.ai/)

## Contributing
- The repository now has a Discussions tab, use it.
- Need user's credentials or API Keys? These live in `secrets.json` (see `secrets.example.json`).
- No hardcoding. Use `config.py` or `config.json` for configuration.
- Fork the repository.
- Consider the project directory structure - add what you need or propose changes (e.g., to `/src`).
- Create your feature branch (`git checkout -b my-new-feature`).
- If the user needs to do something (e.g., get an API key), update this README.md.
- Run code quality checks (e.g., codesmell review, as deep as possible).
- Lint your code (e.g., using black, isort, flake8).
- Add docstrings to all classes and methods.
- Ensure your code maintains abstraction and encapsulation principles.
- Add Pytests for your feature in the `/tests/` directory. All tests must pass.
- If you use other technologies (e.g., Node.js), ensure equivalent tests are provided.
- Run ALL tests prior to creating a Pull Request. All tests must pass.
