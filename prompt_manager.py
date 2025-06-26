"""
Centralized prompt management system for the unified memory application.

This module provides a comprehensive system for managing prompts used throughout
the application including:
- Organized directory structure for different prompt categories
- Template support with variable substitution
- Caching for performance
- Version control and maintenance support
- Integration with logging system

Features:
- Category-based organization (chat, extraction, processing, system)
- Template variable substitution using {variable} syntax
- Automatic prompt discovery and loading
- Caching for frequently used prompts
- Comprehensive error handling and logging
"""

import os
import json
from pathlib import Path
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
from typing import Dict, Any, Optional, List
from string import Template
from logging_config import get_logger, log_exception
from logging_decorators import log_function_calls, log_performance, log_exceptions


class PromptManager:
    """
    Centralized prompt management system.
    
    This class handles loading, caching, and retrieving prompts from the
    organized directory structure. It supports template variable substitution
    and provides comprehensive error handling.
    
    Attributes
    ----------
    prompts_dir: Path to the prompts directory
    cache: Dictionary cache for loaded prompts
    logger: Logger instance for this class
    
    Example
    -------
        >>> pm = PromptManager()
        >>> prompt = pm.get_prompt('chat', 'user_interaction', 
        ...                       user_id='bruce', context='facts')
        >>> print(prompt)
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize PromptManager.
        
        Args
        ----
        prompts_dir: Path to the prompts directory
        """
        self.logger = get_logger(__name__)
        self.prompts_dir = Path(prompts_dir)
        self.cache = {}
        self._ensure_directory_structure()
        self._load_all_prompts()
    
    @log_exceptions("Failed to ensure prompt directory structure")
    def _ensure_directory_structure(self):
        """
        Ensure the prompt directory structure exists.
        
        Creates the main categories if they don't exist.
        """
        categories = ['chat', 'extraction', 'processing', 'system']
        
        for category in categories:
            category_dir = self.prompts_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a README file for each category if it doesn't exist
            readme_file = category_dir / "README.md"
            if not readme_file.exists():
                self._create_category_readme(category, readme_file)
        
        self.logger.info(f"Prompt directory structure ensured at: {self.prompts_dir.absolute()}")
    
    def _create_category_readme(self, category: str, readme_path: Path):
        """
        Create README file for a prompt category.
        
        Args
        ----
        category: Category name
        readme_path: Path to the README file
        """
        readme_content = {
            'chat': """# Chat Prompts

This directory contains prompts used for user interactions and chat functionality.

## Files:
- user_interaction.txt: Main chat prompt with pronoun resolution
- error_response.txt: Prompt for handling chat errors
- no_memories.txt: Response when no relevant memories found

## Variables:
- {user_id}: The user's identifier
- {context}: Relevant memory context
- {query}: User's question or message
""",
            'extraction': """# Extraction Prompts

This directory contains prompts used for extracting facts from various sources.

## Files:
- markdown_facts.txt: Extract facts from markdown conversations
- conversation_facts.txt: Extract facts from conversation entries
- document_facts.txt: Extract facts from documents

## Variables:
- {context}: Section or document context
- {content}: Content to extract facts from
- {timestamp}: Timestamp information if available
""",
            'processing': """# Processing Prompts

This directory contains prompts used for data processing operations.

## Files:
- data_validation.txt: Validate extracted data
- content_summarization.txt: Summarize content
- quality_check.txt: Check quality of extracted facts

## Variables:
- {data}: Data to process
- {criteria}: Processing criteria
- {format}: Expected output format
""",
            'system': """# System Prompts

This directory contains system-level prompts for error handling and operations.

## Files:
- error_analysis.txt: Analyze system errors
- health_check.txt: System health check prompts
- maintenance.txt: Maintenance operation prompts

## Variables:
- {error_message}: Error message details
- {system_state}: Current system state
- {operation}: Operation being performed
"""
        }
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content.get(category, f"# {category.title()} Prompts\n\nPrompts for {category} operations."))
    
    @log_performance(threshold_seconds=1.0)
    @log_exceptions("Failed to load all prompts")
    def _load_all_prompts(self):
        """
        Load all prompts from the directory structure into cache.
        
        Supports .txt, .json, and .yaml files.
        """
        if not self.prompts_dir.exists():
            self.logger.warning(f"Prompts directory does not exist: {self.prompts_dir}")
            return
        
        loaded_count = 0
        
        for category_dir in self.prompts_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            self.cache[category] = {}
            
            for prompt_file in category_dir.iterdir():
                if prompt_file.suffix in ['.txt', '.json', '.yaml', '.yml']:
                    try:
                        prompt_name = prompt_file.stem
                        prompt_content = self._load_prompt_file(prompt_file)
                        self.cache[category][prompt_name] = prompt_content
                        loaded_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to load prompt file {prompt_file}: {e}")
        
        self.logger.info(f"Loaded {loaded_count} prompts from {len(self.cache)} categories")
    
    def _load_prompt_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a single prompt file.
        
        Args
        ----
        file_path: Path to the prompt file
        
        Returns
        -------
        Dictionary containing prompt data
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix == '.txt':
                return {
                    'content': f.read().strip(),
                    'type': 'text',
                    'file': str(file_path)
                }
            elif file_path.suffix == '.json':
                data = json.load(f)
                data['type'] = 'json'
                data['file'] = str(file_path)
                return data
            elif file_path.suffix in ['.yaml', '.yml']:
                if not YAML_AVAILABLE:
                    raise ValueError(f"YAML support not available. Install PyYAML to use {file_path}")
                data = yaml.safe_load(f)
                data['type'] = 'yaml'
                data['file'] = str(file_path)
                return data
        
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    @log_function_calls(include_params=True, include_result=False)
    def get_prompt(self, category: str, name: str, **variables) -> str:
        """
        Get a prompt with variable substitution.
        
        Args
        ----
        category: Prompt category (chat, extraction, processing, system)
        name: Prompt name within the category
        **variables: Variables to substitute in the prompt template
        
        Returns
        -------
        Formatted prompt string with variables substituted
        
        Raises
        ------
        ValueError: If category or prompt name not found
        
        Example
        -------
            >>> pm = PromptManager()
            >>> prompt = pm.get_prompt('chat', 'user_interaction',
            ...                       user_id='bruce', context='facts', query='What do I like?')
        """
        if category not in self.cache:
            raise ValueError(f"Prompt category '{category}' not found. Available: {list(self.cache.keys())}")
        
        if name not in self.cache[category]:
            available = list(self.cache[category].keys())
            raise ValueError(f"Prompt '{name}' not found in category '{category}'. Available: {available}")
        
        prompt_data = self.cache[category][name]
        
        # Get the content based on prompt type
        if prompt_data['type'] == 'text':
            template_content = prompt_data['content']
        elif 'content' in prompt_data:
            template_content = prompt_data['content']
        elif 'template' in prompt_data:
            template_content = prompt_data['template']
        else:
            raise ValueError(f"No content found in prompt '{category}/{name}'")
        
        # Substitute variables
        try:
            template = Template(template_content)
            formatted_prompt = template.safe_substitute(**variables)
            
            # Log if there are unsubstituted variables
            if '$' in formatted_prompt:
                self.logger.warning(f"Unsubstituted variables found in prompt '{category}/{name}'")
            
            return formatted_prompt
            
        except Exception as e:
            self.logger.error(f"Failed to substitute variables in prompt '{category}/{name}': {e}")
            log_exception(self.logger, e, f"Prompt substitution for {category}/{name}")
            raise
    
    @log_function_calls(include_params=False, include_result=True)
    def list_categories(self) -> List[str]:
        """
        List all available prompt categories.
        
        Returns
        -------
        List of category names
        """
        return list(self.cache.keys())
    
    @log_function_calls(include_params=True, include_result=True)
    def list_prompts(self, category: str) -> List[str]:
        """
        List all prompts in a specific category.
        
        Args
        ----
        category: Category name
        
        Returns
        -------
        List of prompt names in the category
        
        Raises
        ------
        ValueError: If category not found
        """
        if category not in self.cache:
            raise ValueError(f"Category '{category}' not found. Available: {list(self.cache.keys())}")
        
        return list(self.cache[category].keys())
    
    def get_prompt_info(self, category: str, name: str) -> Dict[str, Any]:
        """
        Get information about a specific prompt.
        
        Args
        ----
        category: Prompt category
        name: Prompt name
        
        Returns
        -------
        Dictionary with prompt metadata
        """
        if category not in self.cache:
            raise ValueError(f"Category '{category}' not found")
        
        if name not in self.cache[category]:
            raise ValueError(f"Prompt '{name}' not found in category '{category}'")
        
        prompt_data = self.cache[category][name].copy()
        
        # Add metadata
        prompt_data['category'] = category
        prompt_data['name'] = name
        prompt_data['variables'] = self._extract_variables(prompt_data.get('content', ''))
        
        return prompt_data
    
    def _extract_variables(self, content: str) -> List[str]:
        """
        Extract variable names from prompt content.
        
        Args
        ----
        content: Prompt content
        
        Returns
        -------
        List of variable names found in the content
        """
        import re
        variables = re.findall(r'\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)', content)
        # Flatten the tuples and filter empty strings
        return [var for group in variables for var in group if var]
    
    @log_exceptions("Failed to reload prompts")
    def reload_prompts(self):
        """
        Reload all prompts from disk.
        
        Useful for development and when prompts are updated externally.
        """
        self.logger.info("Reloading all prompts from disk")
        self.cache.clear()
        self._load_all_prompts()
        self.logger.info("Prompt reload completed")


# Global prompt manager instance
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """
    Get the global prompt manager instance.
    
    Returns
    -------
    PromptManager instance
    
    Example
    -------
        >>> from prompt_manager import get_prompt_manager
        >>> pm = get_prompt_manager()
        >>> prompt = pm.get_prompt('chat', 'user_interaction', user_id='bruce')
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def get_prompt(category: str, name: str, **variables) -> str:
    """
    Convenience function to get a prompt with variable substitution.

    Args
    ----
    category: Prompt category
    name: Prompt name
    **variables: Variables to substitute

    Returns
    -------
    Formatted prompt string

    Example
    -------
        >>> from prompt_manager import get_prompt
        >>> prompt = get_prompt('chat', 'user_interaction', user_id='bruce', context='facts')
    """
    return get_prompt_manager().get_prompt(category, name, **variables)


def main():
    """
    CLI tool for managing prompts.

    Usage examples:
        python prompt_manager.py list
        python prompt_manager.py list chat
        python prompt_manager.py info chat user_interaction
        python prompt_manager.py test chat user_interaction user_id=bruce query="test"
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prompt_manager.py <command> [args...]")
        print("Commands:")
        print("  list [category]           - List categories or prompts in category")
        print("  info <category> <name>    - Show prompt information")
        print("  test <category> <name> [var=value ...]  - Test prompt with variables")
        print("  reload                    - Reload all prompts from disk")
        return

    command = sys.argv[1]
    pm = get_prompt_manager()

    try:
        if command == "list":
            if len(sys.argv) == 2:
                # List categories
                categories = pm.list_categories()
                print("Available categories:")
                for cat in categories:
                    prompts = pm.list_prompts(cat)
                    print(f"  {cat}: {len(prompts)} prompts")
            else:
                # List prompts in category
                category = sys.argv[2]
                prompts = pm.list_prompts(category)
                print(f"Prompts in '{category}':")
                for prompt in prompts:
                    print(f"  {prompt}")

        elif command == "info":
            if len(sys.argv) < 4:
                print("Usage: python prompt_manager.py info <category> <name>")
                return

            category, name = sys.argv[2], sys.argv[3]
            info = pm.get_prompt_info(category, name)

            print(f"Prompt: {category}/{name}")
            print(f"Type: {info['type']}")
            print(f"File: {info['file']}")
            print(f"Variables: {info['variables']}")
            print(f"Content preview: {info['content'][:100]}...")

        elif command == "test":
            if len(sys.argv) < 4:
                print("Usage: python prompt_manager.py test <category> <name> [var=value ...]")
                return

            category, name = sys.argv[2], sys.argv[3]

            # Parse variables from command line
            variables = {}
            for arg in sys.argv[4:]:
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    variables[key] = value

            prompt = pm.get_prompt(category, name, **variables)
            print(f"Generated prompt for {category}/{name}:")
            print("-" * 50)
            print(prompt)
            print("-" * 50)

        elif command == "reload":
            pm.reload_prompts()
            print("Prompts reloaded successfully")

        else:
            print(f"Unknown command: {command}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
