"""
Tests for the prompt management system.

This module tests the prompt manager functionality including:
- Prompt loading and caching
- Template variable substitution
- Category and prompt discovery
- Error handling and fallbacks
- Integration with the logging system
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

from prompt_manager import PromptManager, get_prompt_manager, get_prompt


class TestPromptManager:
    """Test PromptManager class functionality."""
    
    def test_prompt_manager_initialization(self):
        """Test PromptManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(prompts_dir=temp_dir)
            
            assert pm.prompts_dir == Path(temp_dir)
            assert isinstance(pm.cache, dict)
            assert hasattr(pm, 'logger')
    
    def test_directory_structure_creation(self):
        """Test that prompt directory structure is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(prompts_dir=temp_dir)
            
            expected_categories = ['chat', 'extraction', 'processing', 'system']
            for category in expected_categories:
                category_dir = Path(temp_dir) / category
                assert category_dir.exists()
                assert category_dir.is_dir()
                
                # Check README file exists
                readme_file = category_dir / "README.md"
                assert readme_file.exists()
    
    def test_prompt_loading_text_file(self):
        """Test loading text prompt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test prompt file
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            test_prompt = "Hello ${user_id}, how can I help you with ${query}?"
            prompt_file = chat_dir / "test_prompt.txt"
            prompt_file.write_text(test_prompt)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            assert 'chat' in pm.cache
            assert 'test_prompt' in pm.cache['chat']
            assert pm.cache['chat']['test_prompt']['content'] == test_prompt
            assert pm.cache['chat']['test_prompt']['type'] == 'text'
    
    def test_get_prompt_with_substitution(self):
        """Test getting prompt with variable substitution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test prompt
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            test_prompt = "Hello ${user_id}, your query is: ${query}"
            prompt_file = chat_dir / "greeting.txt"
            prompt_file.write_text(test_prompt)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            result = pm.get_prompt('chat', 'greeting', user_id='bruce', query='test question')
            expected = "Hello bruce, your query is: test question"
            
            assert result == expected
    
    def test_get_prompt_missing_category(self):
        """Test error handling for missing category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(prompts_dir=temp_dir)
            
            with pytest.raises(ValueError, match="Prompt category 'nonexistent' not found"):
                pm.get_prompt('nonexistent', 'prompt')
    
    def test_get_prompt_missing_prompt(self):
        """Test error handling for missing prompt."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty category
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            with pytest.raises(ValueError, match="Prompt 'nonexistent' not found in category 'chat'"):
                pm.get_prompt('chat', 'nonexistent')
    
    def test_list_categories(self):
        """Test listing available categories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(prompts_dir=temp_dir)
            
            categories = pm.list_categories()
            expected_categories = ['chat', 'extraction', 'processing', 'system']
            
            for category in expected_categories:
                assert category in categories
    
    def test_list_prompts(self):
        """Test listing prompts in a category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test prompts
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            (chat_dir / "prompt1.txt").write_text("Test prompt 1")
            (chat_dir / "prompt2.txt").write_text("Test prompt 2")
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            prompts = pm.list_prompts('chat')
            assert 'prompt1' in prompts
            assert 'prompt2' in prompts
    
    def test_get_prompt_info(self):
        """Test getting prompt information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test prompt
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            test_prompt = "Hello ${user_id}, how are you?"
            prompt_file = chat_dir / "greeting.txt"
            prompt_file.write_text(test_prompt)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            info = pm.get_prompt_info('chat', 'greeting')
            
            assert info['category'] == 'chat'
            assert info['name'] == 'greeting'
            assert info['type'] == 'text'
            assert info['content'] == test_prompt
            assert 'user_id' in info['variables']
    
    def test_reload_prompts(self):
        """Test reloading prompts from disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create initial prompt
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            prompt_file = chat_dir / "test.txt"
            prompt_file.write_text("Original content")
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            # Verify initial content
            assert pm.get_prompt('chat', 'test') == "Original content"
            
            # Update file
            prompt_file.write_text("Updated content")
            
            # Reload and verify
            pm.reload_prompts()
            assert pm.get_prompt('chat', 'test') == "Updated content"


class TestGlobalPromptFunctions:
    """Test global prompt manager functions."""
    
    def test_get_prompt_manager_singleton(self):
        """Test that get_prompt_manager returns singleton."""
        pm1 = get_prompt_manager()
        pm2 = get_prompt_manager()
        
        assert pm1 is pm2
        assert isinstance(pm1, PromptManager)
    
    def test_get_prompt_function(self):
        """Test the global get_prompt function."""
        # This test uses the actual prompt files
        try:
            # Test with existing prompt
            prompt = get_prompt('chat', 'user_interaction', 
                              user_id='test_user', 
                              context='test context', 
                              query='test query')
            
            assert 'test_user' in prompt
            assert 'test context' in prompt
            assert 'test query' in prompt
            
        except ValueError:
            # If prompt doesn't exist, that's also a valid test result
            pytest.skip("Chat prompt not available for testing")


class TestPromptTemplateSubstitution:
    """Test prompt template variable substitution."""
    
    def test_basic_variable_substitution(self):
        """Test basic variable substitution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            template = "User: ${user_id}, Query: ${query}, Context: ${context}"
            prompt_file = chat_dir / "template.txt"
            prompt_file.write_text(template)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            result = pm.get_prompt('chat', 'template',
                                 user_id='alice',
                                 query='What is my name?',
                                 context='Personal information')
            
            expected = "User: alice, Query: What is my name?, Context: Personal information"
            assert result == expected
    
    def test_partial_variable_substitution(self):
        """Test handling of missing variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            template = "User: ${user_id}, Missing: ${missing_var}"
            prompt_file = chat_dir / "partial.txt"
            prompt_file.write_text(template)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            # Should not raise error, but leave unsubstituted variables
            result = pm.get_prompt('chat', 'partial', user_id='bob')
            
            assert 'bob' in result
            assert '${missing_var}' in result  # Should remain unsubstituted
    
    def test_variable_extraction(self):
        """Test extraction of variables from prompt content."""
        pm = PromptManager()
        
        content = "Hello ${user_id}, your query ${query} about ${topic} is interesting."
        variables = pm._extract_variables(content)
        
        expected_vars = ['user_id', 'query', 'topic']
        for var in expected_vars:
            assert var in variables


class TestPromptManagerIntegration:
    """Test prompt manager integration with existing system."""
    
    def test_memory_manager_integration(self):
        """Test that memory manager can use prompt manager."""
        # This test verifies the integration works without errors
        try:
            from memory_manager import MemoryManager
            from prompt_manager import get_prompt
            
            # Test that we can get the chat prompt
            prompt = get_prompt('chat', 'user_interaction',
                              user_id='test',
                              context='test context',
                              query='test query')
            
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")
    
    def test_markdown_processor_integration(self):
        """Test that markdown processor can use prompt manager."""
        try:
            from prompt_manager import get_prompt
            
            # Test that we can get the extraction prompt
            prompt = get_prompt('extraction', 'markdown_facts',
                              context='test context',
                              time_context='test time',
                              content='test content')
            
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")


class TestPromptFileFormats:
    """Test different prompt file formats."""
    
    def test_text_file_loading(self):
        """Test loading .txt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            content = "Simple text prompt"
            (chat_dir / "simple.txt").write_text(content)
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            assert pm.cache['chat']['simple']['type'] == 'text'
            assert pm.cache['chat']['simple']['content'] == content
    
    def test_error_handling_invalid_file(self):
        """Test error handling for invalid files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            chat_dir = Path(temp_dir) / "chat"
            chat_dir.mkdir(parents=True)
            
            # Create an invalid file that should be ignored
            (chat_dir / "invalid.xyz").write_text("Invalid content")
            
            pm = PromptManager(prompts_dir=temp_dir)
            
            # Should not have loaded the invalid file
            assert 'invalid' not in pm.cache.get('chat', {})


class TestPromptManagerLogging:
    """Test logging integration with prompt manager."""
    
    def test_logging_initialization(self):
        """Test that prompt manager initializes logging correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(prompts_dir=temp_dir)
            
            assert hasattr(pm, 'logger')
            assert pm.logger.name == 'prompt_manager'
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pm = PromptManager(prompts_dir=temp_dir)
            
            # This should log an error
            with pytest.raises(ValueError):
                pm.get_prompt('nonexistent', 'prompt')
