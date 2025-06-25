"""
Tests for MemoryManager class.

This module tests the core memory management functionality including:
- Configuration loading and validation
- Memory initialization
- Adding facts with and without metadata
- Searching memories
- Chat functionality with pronoun resolution
- Getting all memories
- Reset functionality
"""

import pytest
import json
import tempfile
from unittest.mock import patch, Mock
from datetime import datetime

from memory_manager import MemoryManager


class TestMemoryManagerConfiguration:
    """Test configuration loading and validation."""

    def test_load_valid_config(self, test_config_path, clean_test_collection):
        """Test loading a valid configuration file."""
        with patch('memory_manager.Memory') as mock_memory:
            mock_memory.from_config.return_value = Mock()
            manager = MemoryManager(test_config_path)
            
            assert manager.config is not None
            assert 'memory_config' in manager.config
            assert 'processing_options' in manager.config
            assert manager.user_id == 'test_user'
    
    def test_load_config_with_custom_user_id(self, test_config):
        """Test that user_id is properly extracted from config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_config['processing_options']['user_id'] = 'custom_user'
            json.dump(test_config, f)
            config_path = f.name
        
        with patch('memory_manager.Memory') as mock_memory:
            mock_memory.from_config.return_value = Mock()
            manager = MemoryManager(config_path)
            
            assert manager.user_id == 'custom_user'
    
    def test_config_file_not_found(self):
        """Test handling of missing configuration file."""
        with pytest.raises(FileNotFoundError):
            MemoryManager('nonexistent_config.json')
    
    def test_invalid_json_config(self):
        """Test handling of invalid JSON configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{ invalid json }')
            config_path = f.name
        
        with pytest.raises(ValueError):
            MemoryManager(config_path)


class TestMemoryManagerInitialization:
    """Test memory initialization."""
    
    def test_successful_memory_initialization(self, test_config_path):
        """Test successful memory initialization."""
        with patch('memory_manager.Memory') as mock_memory:
            mock_instance = Mock()
            mock_memory.from_config.return_value = mock_instance
            
            manager = MemoryManager(test_config_path)
            
            assert manager.memory == mock_instance
            mock_memory.from_config.assert_called_once()
    
    def test_memory_initialization_failure(self, test_config_path):
        """Test handling of memory initialization failure."""
        with patch('memory_manager.Memory') as mock_memory:
            mock_memory.from_config.side_effect = Exception("Connection failed")
            
            with pytest.raises(RuntimeError, match="Failed to initialize memory"):
                MemoryManager(test_config_path)


class TestMemoryManagerFactOperations:
    """Test adding and managing facts."""
    
    def test_add_fact_success(self, memory_manager_with_mocks):
        """Test successful fact addition."""
        result = memory_manager_with_mocks.add_fact("Test fact", "test_user")
        
        assert result is not None
        assert result['results'][0]['memory'] == 'Test memory content'
        memory_manager_with_mocks.memory.add.assert_called_once_with(
            "Test fact", user_id="test_user", metadata=None
        )
    
    def test_add_fact_with_metadata(self, memory_manager_with_mocks):
        """Test adding fact with metadata."""
        metadata = {"timestamp": "2025-03-29T09:10:00", "source": "test"}
        result = memory_manager_with_mocks.add_fact(
            "Test fact", "test_user", metadata=metadata
        )
        
        assert result is not None
        memory_manager_with_mocks.memory.add.assert_called_once_with(
            "Test fact", user_id="test_user", metadata=metadata
        )
    
    def test_add_fact_default_user_id(self, memory_manager_with_mocks):
        """Test adding fact with default user ID."""
        result = memory_manager_with_mocks.add_fact("Test fact")
        
        assert result is not None
        memory_manager_with_mocks.memory.add.assert_called_once_with(
            "Test fact", user_id="test_user", metadata=None
        )
    
    def test_add_fact_no_results(self, memory_manager_with_mocks):
        """Test handling when no memory is created from fact."""
        memory_manager_with_mocks.memory.add.return_value = {'results': []}
        
        result = memory_manager_with_mocks.add_fact("Vague statement")
        
        assert result is not None
        assert result['results'] == []
    
    def test_add_fact_with_retry(self, memory_manager_with_mocks):
        """Test retry logic for fact addition."""
        # First call fails, second succeeds
        memory_manager_with_mocks.memory.add.side_effect = [
            Exception("Temporary failure"),
            {'results': [{'id': 'test-id', 'memory': 'Test memory', 'event': 'ADD'}]}
        ]
        
        with patch('time.sleep'):  # Speed up test
            result = memory_manager_with_mocks.add_fact("Test fact")
        
        assert result is not None
        assert memory_manager_with_mocks.memory.add.call_count == 2


class TestMemoryManagerSearch:
    """Test memory search functionality."""
    
    def test_search_memories_success(self, memory_manager_with_mocks):
        """Test successful memory search."""
        result = memory_manager_with_mocks.search_memories("test query", "test_user")
        
        assert result is not None
        assert len(result['results']) == 1
        memory_manager_with_mocks.memory.search.assert_called_once_with(
            "test query", user_id="test_user", limit=5
        )
    
    def test_search_memories_with_limit(self, memory_manager_with_mocks):
        """Test memory search with custom limit."""
        result = memory_manager_with_mocks.search_memories(
            "test query", "test_user", limit=10
        )
        
        assert result is not None
        memory_manager_with_mocks.memory.search.assert_called_once_with(
            "test query", user_id="test_user", limit=10
        )
    
    def test_search_memories_default_user(self, memory_manager_with_mocks):
        """Test memory search with default user ID."""
        result = memory_manager_with_mocks.search_memories("test query")
        
        assert result is not None
        memory_manager_with_mocks.memory.search.assert_called_once_with(
            "test query", user_id="test_user", limit=5
        )
    
    def test_get_all_memories(self, memory_manager_with_mocks):
        """Test getting all memories for a user."""
        result = memory_manager_with_mocks.get_all_memories("test_user")
        
        assert result is not None
        assert len(result['results']) == 1
        memory_manager_with_mocks.memory.get_all.assert_called_once_with(
            user_id="test_user"
        )


class TestMemoryManagerChat:
    """Test chat functionality."""
    
    @patch('memory_manager.requests.post')
    def test_chat_with_memories(self, mock_post, memory_manager_with_mocks):
        """Test chat functionality with relevant memories."""
        # Mock Ollama API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test user likes pizza!'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = memory_manager_with_mocks.chat("What do I like to eat?", "test_user")
        
        assert result == 'Test user likes pizza!'
        memory_manager_with_mocks.memory.search.assert_called_once()
        mock_post.assert_called_once()
    
    @patch('memory_manager.requests.post')
    def test_chat_no_memories_found(self, mock_post, memory_manager_with_mocks):
        """Test chat when no relevant memories are found."""
        # Mock no search results
        memory_manager_with_mocks.memory.search.return_value = {'results': []}
        
        # Mock Ollama API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'I don\'t have information about that.'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = memory_manager_with_mocks.chat("What do I like?", "test_user")
        
        assert "don't have information" in result
    
    @patch('memory_manager.requests.post')
    def test_chat_pronoun_resolution_in_prompt(self, mock_post, memory_manager_with_mocks):
        """Test that chat prompt includes pronoun resolution instructions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'response': 'Test response'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        memory_manager_with_mocks.chat("What do I like?", "test_user")
        
        # Check that the prompt includes pronoun resolution instructions
        call_args = mock_post.call_args[1]['json']
        prompt = call_args['prompt']
        assert 'When the user says "I", "me", "my", or "mine", they are referring to test_user' in prompt
        assert 'What do I like?' in prompt


class TestMemoryManagerReset:
    """Test memory reset functionality."""
    
    def test_reset_memories_success(self, memory_manager_with_mocks):
        """Test successful memory reset."""
        deleted_count = memory_manager_with_mocks.reset_memories("test_user")
        
        assert deleted_count == 1
        memory_manager_with_mocks.memory.get_all.assert_called_once_with(user_id="test_user")
        memory_manager_with_mocks.memory.delete.assert_called_once_with(memory_id="test-memory-id")
    
    def test_reset_memories_no_memories(self, memory_manager_with_mocks):
        """Test reset when no memories exist."""
        memory_manager_with_mocks.memory.get_all.return_value = {'results': []}
        
        deleted_count = memory_manager_with_mocks.reset_memories("test_user")
        
        assert deleted_count == 0
        memory_manager_with_mocks.memory.delete.assert_not_called()
    
    def test_reset_memories_default_user(self, memory_manager_with_mocks):
        """Test reset with default user ID."""
        deleted_count = memory_manager_with_mocks.reset_memories()
        
        assert deleted_count == 1
        memory_manager_with_mocks.memory.get_all.assert_called_once_with(user_id="test_user")
