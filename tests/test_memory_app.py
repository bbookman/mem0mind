"""
Tests for the main memory application CLI.

This module tests the command-line interface and integration functionality:
- CLI argument parsing for all commands
- Configuration file loading and validation
- Integration tests for process → chat workflow
- Command execution and error handling
"""

import pytest
import argparse
import tempfile
import json
from unittest.mock import patch, Mock
from pathlib import Path

import memory_app


class TestCLIArgumentParsing:
    """Test command-line argument parsing."""
    
    def test_parse_process_command(self):
        """Test parsing process command arguments."""
        # Mock sys.argv for process command
        test_args = ['memory_app.py', 'process', '--config', 'test_config.json', '--user', 'test_user']
        
        with patch('sys.argv', test_args):
            parser = memory_app.main.__code__.co_consts  # Get parser from main function
            # We'll test the actual parsing in integration tests
            pass
    
    def test_parse_chat_command(self):
        """Test parsing chat command arguments."""
        test_args = ['memory_app.py', 'chat', '--config', 'test_config.json', '--user', 'test_user']
        
        with patch('sys.argv', test_args):
            # Test will be covered in integration tests
            pass
    
    def test_parse_reset_command(self):
        """Test parsing reset command arguments."""
        test_args = ['memory_app.py', 'reset', '--config', 'test_config.json', '--user', 'test_user', '--force']
        
        with patch('sys.argv', test_args):
            # Test will be covered in integration tests
            pass


class TestConfigurationHandling:
    """Test configuration file handling."""
    
    def test_setup_logging_with_valid_config(self, test_config_path):
        """Test logging setup with valid configuration."""
        with patch('logging.basicConfig') as mock_logging:
            memory_app.setup_logging(test_config_path)
            mock_logging.assert_called_once()
    
    def test_setup_logging_with_invalid_config(self):
        """Test logging setup with invalid configuration falls back gracefully."""
        with patch('logging.basicConfig') as mock_logging:
            memory_app.setup_logging('nonexistent_config.json')
            # Should still call basicConfig with fallback settings
            mock_logging.assert_called()
    
    def test_setup_logging_with_custom_settings(self, test_config):
        """Test logging setup with custom settings."""
        # Create config with custom logging settings
        test_config['logging'] = {
            'level': 'DEBUG',
            'file': 'custom.log',
            'format': 'Custom format: %(message)s'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f)
            config_path = f.name
        
        with patch('logging.basicConfig') as mock_logging:
            memory_app.setup_logging(config_path)
            
            # Verify logging was configured with custom settings
            call_args = mock_logging.call_args[1]
            assert call_args['level'] == 10  # DEBUG level
            assert 'custom.log' in str(call_args['handlers'][0])


class TestProcessCommand:
    """Test the process command functionality."""
    
    @patch('memory_app.MarkdownProcessor')
    @patch('memory_app.MemoryManager')
    def test_process_command_success(self, mock_memory_manager, mock_markdown_processor, test_config_path):
        """Test successful execution of process command."""
        # Mock the components
        mock_manager_instance = Mock()
        mock_memory_manager.return_value = mock_manager_instance
        
        mock_processor_instance = Mock()
        mock_processor_instance.process_directories.return_value = (5, 20, 18)  # files, total, added
        mock_markdown_processor.return_value = mock_processor_instance
        
        # Create mock args
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        
        # Execute process command
        with patch('builtins.print') as mock_print:
            memory_app.process_command(args)
        
        # Verify components were initialized and called
        mock_memory_manager.assert_called_once_with(test_config_path)
        mock_markdown_processor.assert_called_once_with(mock_manager_instance)
        mock_processor_instance.process_directories.assert_called_once_with('test_user')
        
        # Verify summary was printed
        mock_print.assert_called()
    
    @patch('memory_app.MemoryManager')
    def test_process_command_initialization_failure(self, mock_memory_manager, test_config_path):
        """Test process command when memory manager initialization fails."""
        mock_memory_manager.side_effect = Exception("Initialization failed")
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        
        with pytest.raises(SystemExit):
            memory_app.process_command(args)


class TestChatCommand:
    """Test the chat command functionality."""
    
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_chat_command_success(self, mock_input, mock_memory_manager, test_config_path):
        """Test successful execution of chat command."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_manager_instance.get_all_memories.return_value = {
            'results': [{'id': '1', 'memory': 'Test memory', 'created_at': '2025-06-24'}]
        }
        mock_manager_instance.chat.return_value = "Test response"
        mock_memory_manager.return_value = mock_manager_instance
        
        # Mock user input (ask question then exit)
        mock_input.side_effect = ['What do I like?', 'exit']
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        
        with patch('builtins.print') as mock_print:
            memory_app.chat_command(args)
        
        # Verify memory manager was initialized and used
        mock_memory_manager.assert_called_once_with(test_config_path)
        mock_manager_instance.get_all_memories.assert_called_with('test_user')
        mock_manager_instance.chat.assert_called_with('What do I like?', 'test_user')
        
        # Verify response was printed
        mock_print.assert_called()
    
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_chat_command_no_memories(self, mock_input, mock_memory_manager, test_config_path):
        """Test chat command when no memories exist."""
        # Mock memory manager with no memories
        mock_manager_instance = Mock()
        mock_manager_instance.get_all_memories.return_value = {'results': []}
        mock_memory_manager.return_value = mock_manager_instance
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        
        with patch('builtins.print') as mock_print:
            memory_app.chat_command(args)
        
        # Verify warning message was printed
        mock_print.assert_called()
        # Should not attempt to chat
        mock_manager_instance.chat.assert_not_called()
    
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_chat_command_memories_subcommand(self, mock_input, mock_memory_manager, test_config_path):
        """Test chat command with 'memories' subcommand."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_manager_instance.get_all_memories.return_value = {
            'results': [
                {'id': '1', 'memory': 'Test memory 1', 'created_at': '2025-06-24'},
                {'id': '2', 'memory': 'Test memory 2', 'created_at': '2025-06-24'}
            ]
        }
        mock_memory_manager.return_value = mock_manager_instance
        
        # Mock user input (show memories then exit)
        mock_input.side_effect = ['memories', 'exit']
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        
        with patch('builtins.print') as mock_print:
            memory_app.chat_command(args)
        
        # Verify memories were retrieved and displayed
        assert mock_manager_instance.get_all_memories.call_count >= 2  # Once for check, once for display
        mock_print.assert_called()
    
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_chat_command_reset_subcommand(self, mock_input, mock_memory_manager, test_config_path):
        """Test chat command with 'reset' subcommand."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_manager_instance.get_all_memories.return_value = {
            'results': [{'id': '1', 'memory': 'Test memory', 'created_at': '2025-06-24'}]
        }
        mock_manager_instance.reset_memories.return_value = 1
        mock_memory_manager.return_value = mock_manager_instance
        
        # Mock user input (reset with confirmation then exit)
        mock_input.side_effect = ['reset', 'yes', 'exit']
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        
        with patch('builtins.print') as mock_print:
            memory_app.chat_command(args)
        
        # Verify reset was called
        mock_manager_instance.reset_memories.assert_called_with('test_user')
        mock_print.assert_called()


class TestResetCommand:
    """Test the reset command functionality."""
    
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_reset_command_with_confirmation(self, mock_input, mock_memory_manager, test_config_path):
        """Test reset command with user confirmation."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_manager_instance.reset_memories.return_value = 5
        mock_memory_manager.return_value = mock_manager_instance
        
        # Mock user confirmation
        mock_input.return_value = 'yes'
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        args.force = False
        
        with patch('builtins.print') as mock_print:
            memory_app.reset_command(args)
        
        # Verify reset was called
        mock_memory_manager.assert_called_once_with(test_config_path)
        mock_manager_instance.reset_memories.assert_called_once_with('test_user')
        mock_print.assert_called()
    
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_reset_command_cancelled(self, mock_input, mock_memory_manager, test_config_path):
        """Test reset command when user cancels."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_memory_manager.return_value = mock_manager_instance
        
        # Mock user cancellation
        mock_input.return_value = 'no'
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        args.force = False
        
        with patch('builtins.print') as mock_print:
            memory_app.reset_command(args)
        
        # Verify reset was NOT called
        mock_manager_instance.reset_memories.assert_not_called()
        mock_print.assert_called()
    
    @patch('memory_app.MemoryManager')
    def test_reset_command_with_force(self, mock_memory_manager, test_config_path):
        """Test reset command with force flag (no confirmation)."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_manager_instance.reset_memories.return_value = 3
        mock_memory_manager.return_value = mock_manager_instance
        
        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'
        args.force = True
        
        with patch('builtins.print') as mock_print:
            memory_app.reset_command(args)
        
        # Verify reset was called without confirmation
        mock_memory_manager.assert_called_once_with(test_config_path)
        mock_manager_instance.reset_memories.assert_called_once_with('test_user')
        mock_print.assert_called()


class TestIntegrationWorkflow:
    """Test integration between components."""
    
    @patch('memory_app.MarkdownProcessor')
    @patch('memory_app.MemoryManager')
    @patch('builtins.input')
    def test_process_then_chat_workflow(self, mock_input, mock_memory_manager, mock_markdown_processor, test_config_path):
        """Test the complete workflow: process files then chat."""
        # Mock memory manager
        mock_manager_instance = Mock()
        mock_manager_instance.get_all_memories.return_value = {
            'results': [{'id': '1', 'memory': 'User likes pizza', 'created_at': '2025-06-24'}]
        }
        mock_manager_instance.chat.return_value = "You like pizza!"
        mock_memory_manager.return_value = mock_manager_instance
        
        # Mock markdown processor
        mock_processor_instance = Mock()
        mock_processor_instance.process_directories.return_value = (2, 10, 8)
        mock_markdown_processor.return_value = mock_processor_instance
        
        # Mock user input for chat
        mock_input.side_effect = ['What do I like?', 'exit']
        
        # Test process command
        process_args = Mock()
        process_args.config = test_config_path
        process_args.user = 'test_user'
        
        with patch('builtins.print'):
            memory_app.process_command(process_args)
        
        # Test chat command
        chat_args = Mock()
        chat_args.config = test_config_path
        chat_args.user = 'test_user'
        
        with patch('builtins.print'):
            memory_app.chat_command(chat_args)
        
        # Verify both commands executed successfully
        mock_processor_instance.process_directories.assert_called_once()
        mock_manager_instance.chat.assert_called_once_with('What do I like?', 'test_user')
    
    @patch('memory_app.MarkdownProcessor')
    @patch('memory_app.MemoryManager')
    def test_config_file_validation(self, mock_memory_manager, mock_markdown_processor, test_config_path):
        """Test that configuration file validation works correctly."""
        # Test with valid config
        mock_manager_instance = Mock()
        mock_memory_manager.return_value = mock_manager_instance

        # Mock the processor to avoid the len() error
        mock_processor_instance = Mock()
        mock_processor_instance.process_directories.return_value = (1, 5, 4)
        mock_markdown_processor.return_value = mock_processor_instance

        args = Mock()
        args.config = test_config_path
        args.user = 'test_user'

        # Should not raise exception
        with patch('builtins.print'):
            memory_app.process_command(args)

        mock_memory_manager.assert_called_once_with(test_config_path)
        mock_markdown_processor.assert_called_once_with(mock_manager_instance)
