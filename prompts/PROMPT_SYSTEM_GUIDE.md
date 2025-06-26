# Prompt Management System Guide

## Overview

The unified memory application uses a centralized prompt management system that organizes all prompts used throughout the application. This system provides:

- **Organized Structure**: Prompts categorized by purpose and responsibility
- **Template Support**: Variable substitution using `${variable}` syntax
- **Easy Maintenance**: Modify prompts without changing code
- **Version Control**: Track prompt changes alongside code
- **Caching**: Performance optimization for frequently used prompts
- **Logging Integration**: Comprehensive error handling and logging

## Directory Structure

```
prompts/
├── chat/                   # User interaction prompts
│   ├── user_interaction.txt    # Main chat prompt with pronoun resolution
│   ├── no_memories.txt         # Response when no relevant memories found
│   └── error_response.txt      # Error handling responses
├── extraction/             # Fact extraction prompts
│   ├── markdown_facts.txt      # Extract facts from markdown conversations
│   └── conversation_facts.txt  # Extract facts from conversation entries
├── processing/             # Data processing prompts
│   └── data_validation.txt     # Validate extracted data quality
├── system/                 # System-level prompts
│   └── error_analysis.txt      # Analyze system errors
└── PROMPT_SYSTEM_GUIDE.md  # This documentation
```

## Usage Examples

### Basic Usage

```python
from prompt_manager import get_prompt

# Get a chat prompt with variable substitution
prompt = get_prompt('chat', 'user_interaction',
                   user_id='bruce',
                   context='Bruce likes pizza and works at TechCorp',
                   query='What do I like to eat?')
```

### Advanced Usage

```python
from prompt_manager import get_prompt_manager

# Get the prompt manager instance
pm = get_prompt_manager()

# List available categories
categories = pm.list_categories()
print("Available categories:", categories)

# List prompts in a category
chat_prompts = pm.list_prompts('chat')
print("Chat prompts:", chat_prompts)

# Get prompt information
info = pm.get_prompt_info('chat', 'user_interaction')
print("Variables needed:", info['variables'])

# Reload prompts from disk (useful during development)
pm.reload_prompts()
```

## Template Variables

### Chat Prompts
- `${user_id}`: The user's identifier
- `${context}`: Relevant memory context
- `${query}`: User's question or message
- `${error_message}`: Error details (for error responses)

### Extraction Prompts
- `${context}`: Section or document context
- `${content}`: Content to extract facts from
- `${time_context}`: Timestamp information
- `${timestamp}`: Formatted timestamp

### Processing Prompts
- `${data}`: Data to process
- `${criteria}`: Processing criteria
- `${format}`: Expected output format

### System Prompts
- `${error_message}`: Error message details
- `${system_state}`: Current system state
- `${operation}`: Operation being performed
- `${timestamp}`: When the error occurred

## Adding New Prompts

### 1. Create the Prompt File

Create a new `.txt` file in the appropriate category directory:

```bash
# Example: Add a new chat prompt
echo "Welcome back ${user_id}! How can I help you today?" > prompts/chat/welcome.txt
```

### 2. Use the Prompt in Code

```python
from prompt_manager import get_prompt

welcome_message = get_prompt('chat', 'welcome', user_id='bruce')
```

### 3. Test the Prompt

The prompt system automatically loads new files. Test your prompt:

```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()
pm.reload_prompts()  # Force reload if needed

# Test the new prompt
result = pm.get_prompt('chat', 'welcome', user_id='test_user')
print(result)
```

## Best Practices

### 1. Naming Conventions
- Use descriptive names: `user_interaction.txt` not `chat1.txt`
- Use underscores for multi-word names: `error_response.txt`
- Keep names concise but clear

### 2. Variable Naming
- Use clear variable names: `${user_id}` not `${u}`
- Be consistent across prompts: always use `${user_id}`, not sometimes `${user}`
- Document required variables in prompt comments

### 3. Prompt Structure
- Start with clear instructions
- Use consistent formatting
- Include examples when helpful
- Keep prompts focused on one purpose

### 4. Error Handling
- Always provide fallback prompts for error cases
- Test prompts with missing variables
- Use descriptive error messages

## Integration Points

### Memory Manager
- `chat/user_interaction.txt`: Main chat prompt
- `chat/error_response.txt`: Chat error handling
- `chat/no_memories.txt`: No relevant memories found

### Markdown Processor
- `extraction/markdown_facts.txt`: Extract facts from markdown
- `extraction/conversation_facts.txt`: Extract facts from conversations

### Future Extensions
- `processing/data_validation.txt`: Validate extracted data
- `system/error_analysis.txt`: System error analysis
- `system/health_check.txt`: System health monitoring

## File Formats

### Text Files (.txt)
Simple text files with variable substitution:
```
Hello ${user_id}, your query is: ${query}
```

### JSON Files (.json) - Future Support
Structured prompts with metadata:
```json
{
  "content": "Hello ${user_id}, your query is: ${query}",
  "description": "Basic greeting prompt",
  "variables": ["user_id", "query"],
  "version": "1.0"
}
```

### YAML Files (.yaml/.yml) - Future Support
Human-readable structured format:
```yaml
content: |
  Hello ${user_id}, your query is: ${query}
description: Basic greeting prompt
variables:
  - user_id
  - query
version: "1.0"
```

## Troubleshooting

### Common Issues

1. **Prompt Not Found**
   ```
   ValueError: Prompt 'my_prompt' not found in category 'chat'
   ```
   - Check file exists in correct directory
   - Verify filename matches (without .txt extension)
   - Try reloading prompts: `pm.reload_prompts()`

2. **Category Not Found**
   ```
   ValueError: Prompt category 'my_category' not found
   ```
   - Check directory exists under `prompts/`
   - Verify directory name spelling
   - Ensure directory contains at least one prompt file

3. **Variable Substitution Issues**
   ```
   Warning: Unsubstituted variables found in prompt
   ```
   - Check all required variables are provided
   - Verify variable names match exactly (case-sensitive)
   - Use `get_prompt_info()` to see required variables

### Debugging

```python
from prompt_manager import get_prompt_manager

pm = get_prompt_manager()

# Check what's loaded
print("Categories:", pm.list_categories())
print("Chat prompts:", pm.list_prompts('chat'))

# Get detailed info about a prompt
info = pm.get_prompt_info('chat', 'user_interaction')
print("Required variables:", info['variables'])
print("File location:", info['file'])

# Test variable substitution
try:
    result = pm.get_prompt('chat', 'user_interaction',
                          user_id='test',
                          context='test context',
                          query='test query')
    print("Success:", result[:100] + "...")
except Exception as e:
    print("Error:", e)
```

## Performance Considerations

- **Caching**: Prompts are loaded once and cached in memory
- **Reload**: Use `reload_prompts()` sparingly (development only)
- **File Size**: Keep prompt files reasonably sized (< 10KB recommended)
- **Variables**: Minimize complex variable substitution for better performance

## Security Notes

- **Input Validation**: Always validate variables before substitution
- **File Permissions**: Ensure prompt files have appropriate read permissions
- **Version Control**: Track prompt changes in git for audit trail
- **Sensitive Data**: Never include secrets or credentials in prompt files
