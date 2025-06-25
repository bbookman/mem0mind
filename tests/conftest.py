"""
Pytest configuration and shared fixtures for the memory application test suite.

This module provides common fixtures and test utilities used across all test modules.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from memory_manager import MemoryManager
from markdown_processor import MarkdownProcessor


@pytest.fixture
def test_config_path():
    """
    Provide path to test configuration file.
    
    Returns
    -------
    Path to test_config.json
    """
    return os.path.join(os.path.dirname(__file__), 'test_config.json')


@pytest.fixture
def test_config(test_config_path):
    """
    Load test configuration from JSON file.
    
    Returns
    -------
    Configuration dictionary for testing
    """
    with open(test_config_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_memory_instance():
    """
    Create a mock mem0 Memory instance for testing.
    
    Returns
    -------
    Mock Memory instance with common methods
    """
    mock_memory = Mock()
    
    # Mock successful add operation
    mock_memory.add.return_value = {
        'results': [{
            'id': 'test-memory-id',
            'memory': 'Test memory content',
            'event': 'ADD'
        }]
    }
    
    # Mock search operation
    mock_memory.search.return_value = {
        'results': [{
            'id': 'test-memory-id',
            'memory': 'Test memory content',
            'score': 0.95
        }]
    }
    
    # Mock get_all operation
    mock_memory.get_all.return_value = {
        'results': [{
            'id': 'test-memory-id',
            'memory': 'Test memory content',
            'created_at': '2025-06-24T19:22:58.261619-07:00',
            'user_id': 'test_user'
        }]
    }
    
    # Mock delete operation
    mock_memory.delete.return_value = {'status': 'success'}
    
    return mock_memory


@pytest.fixture
def mock_ollama_response():
    """
    Create a mock response for Ollama API calls.
    
    Returns
    -------
    Mock response object
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'response': 'Test user likes pizza and works at a tech company.'
    }
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def temp_markdown_dir():
    """
    Create a temporary directory with sample markdown files.
    
    Returns
    -------
    Path to temporary directory containing test markdown files
    """
    temp_dir = tempfile.mkdtemp()
    
    # Create sample markdown content
    sample_markdown = """# Meeting Notes
- 3/29/25 9:10 AM: Discussed project timeline with John
- 3/29/25 9:15 AM: John mentioned he prefers working remotely
- 3/29/25 9:20 AM: We agreed to meet weekly on Fridays

## Personal Preferences
- 3/29/25 2:30 PM: I really enjoyed the pizza at Mario's restaurant
- 3/29/25 3:00 PM: Need to remember to call mom this weekend
- 3/29/25 3:15 PM: My favorite programming language is Python

### Work Information
- 3/30/25 10:00 AM: Started working at TechCorp as a software engineer
- 3/30/25 10:30 AM: My manager Sarah is very supportive
"""
    
    # Write sample files
    sample_file = Path(temp_dir) / "conversations.md"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_markdown)
    
    # Create another sample file
    another_sample = """# Daily Journal
- 4/1/25 8:00 AM: Had coffee at the new cafe downtown
- 4/1/25 8:30 AM: The barista recommended their house blend
- 4/1/25 9:00 AM: Decided to make this my regular morning spot

## Weekend Plans
- 4/1/25 6:00 PM: Planning to visit the art museum this Saturday
- 4/1/25 6:15 PM: My friend Alice will join me
"""
    
    another_file = Path(temp_dir) / "journal.md"
    with open(another_file, 'w', encoding='utf-8') as f:
        f.write(another_sample)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_manager_with_mocks(test_config_path, mock_memory_instance):
    """
    Create a MemoryManager instance with mocked dependencies.
    
    Returns
    -------
    MemoryManager instance with mocked mem0 Memory
    """
    with patch('memory_manager.Memory') as mock_memory_class:
        mock_memory_class.from_config.return_value = mock_memory_instance
        manager = MemoryManager(test_config_path)
        return manager


@pytest.fixture
def markdown_processor_with_mocks(memory_manager_with_mocks):
    """
    Create a MarkdownProcessor instance with mocked dependencies.
    
    Returns
    -------
    MarkdownProcessor instance with mocked MemoryManager
    """
    return MarkdownProcessor(memory_manager_with_mocks)


@pytest.fixture
def sample_conversation_entries():
    """
    Provide sample conversation entries for testing.
    
    Returns
    -------
    List of conversation entry dictionaries
    """
    return [
        {
            'timestamp': datetime(2025, 3, 29, 9, 10),
            'content': 'Discussed project timeline with John'
        },
        {
            'timestamp': datetime(2025, 3, 29, 14, 30),
            'content': 'I really enjoyed the pizza at Mario\'s restaurant'
        },
        {
            'timestamp': None,
            'content': 'This entry has no timestamp'
        }
    ]


@pytest.fixture
def sample_markdown_sections():
    """
    Provide sample markdown sections for testing.
    
    Returns
    -------
    List of section dictionaries
    """
    return [
        {
            'level': 1,
            'header': 'Meeting Notes',
            'content': '- 3/29/25 9:10 AM: Discussed project timeline\n- 3/29/25 9:15 AM: John prefers remote work'
        },
        {
            'level': 2,
            'header': 'Personal Preferences',
            'content': '- 3/29/25 2:30 PM: Enjoyed pizza at Mario\'s\n- 3/29/25 3:00 PM: Call mom this weekend'
        }
    ]


@pytest.fixture
def clean_test_collection():
    """
    Setup and teardown test collection for each test.

    This fixture ensures a clean Qdrant collection before and after each test.
    """
    import requests

    collection_name = "test_memories"
    qdrant_url = "http://localhost:6333"

    def delete_collection():
        """Delete the test collection if it exists."""
        try:
            response = requests.delete(f"{qdrant_url}/collections/{collection_name}", timeout=10)
            if response.status_code == 200:
                print(f"✅ Deleted collection '{collection_name}'")
            elif response.status_code == 404:
                print(f"ℹ️  Collection '{collection_name}' doesn't exist")
            else:
                print(f"⚠️  Delete response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Could not delete collection: {e}")

    def verify_qdrant_available():
        """Check if Qdrant is available."""
        try:
            response = requests.get(f"{qdrant_url}/collections", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    # Setup: Clean collection before test
    if verify_qdrant_available():
        delete_collection()
        print(f"🧹 Setup: Cleaned test environment")
    else:
        print("⚠️  Qdrant not available - tests will use mocks only")

    yield collection_name

    # Teardown: Clean collection after test
    if verify_qdrant_available():
        delete_collection()
        print(f"🧹 Teardown: Cleaned test environment")


@pytest.fixture
def qdrant_available():
    """
    Check if Qdrant service is available for integration tests.

    Returns
    -------
    True if Qdrant is available, False otherwise
    """
    import requests
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


@pytest.fixture
def ollama_available():
    """
    Check if Ollama service is available for integration tests.

    Returns
    -------
    True if Ollama is available, False otherwise
    """
    import requests
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


@pytest.fixture
def real_memory_manager(test_config_path, clean_test_collection, qdrant_available, ollama_available):
    """
    Create a real MemoryManager instance when services are available.

    This fixture provides a real MemoryManager for integration tests,
    but skips if required services are not available.

    Returns
    -------
    MemoryManager instance or None if services unavailable
    """
    if not (qdrant_available and ollama_available):
        pytest.skip("Qdrant and/or Ollama services not available for integration test")

    try:
        from memory_manager import MemoryManager
        manager = MemoryManager(test_config_path)
        yield manager

        # Cleanup: Reset all memories after test
        try:
            manager.reset_memories("test_user")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

    except Exception as e:
        pytest.skip(f"Could not initialize real MemoryManager: {e}")


@pytest.fixture
def integration_test_data():
    """
    Provide test data for integration tests.

    Returns
    -------
    Dictionary with test facts and expected results
    """
    return {
        "facts": [
            "Test user likes pizza and pasta",
            "Test user works as a software engineer at TechCorp",
            "Test user lives in San Francisco, California",
            "Test user enjoys hiking on weekends",
            "Test user's favorite programming language is Python"
        ],
        "queries": [
            ("What does the test user like to eat?", ["pizza", "pasta"]),
            ("Where does the test user work?", ["TechCorp", "software engineer"]),
            ("What are the test user's hobbies?", ["hiking"]),
            ("What programming language does the test user prefer?", ["Python"])
        ]
    }
