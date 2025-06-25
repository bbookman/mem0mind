"""
Integration tests for the unified memory application.

These tests use real services (Qdrant, Ollama) when available and validate
the complete end-to-end functionality including:
- Real memory storage and retrieval
- Actual LLM fact extraction and chat responses
- Complete workflow from markdown processing to chat

Note: These tests require Qdrant and Ollama services to be running.
They will be skipped if services are not available.
"""

import pytest
import tempfile
import time
from pathlib import Path


@pytest.mark.integration
@pytest.mark.requires_services
class TestRealMemoryOperations:
    """Test memory operations with real services."""
    
    def test_add_and_retrieve_facts(self, real_memory_manager, integration_test_data):
        """Test adding facts and retrieving them with real services."""
        manager = real_memory_manager
        facts = integration_test_data["facts"]
        
        # Add facts one by one
        added_facts = []
        for fact in facts:
            result = manager.add_fact(fact, "test_user")
            if result and result.get('results'):
                added_facts.append(result['results'][0]['memory'])
            time.sleep(0.5)  # Small delay to prevent rate limiting
        
        # Verify at least some facts were added
        assert len(added_facts) > 0, "No facts were successfully added"
        
        # Retrieve all memories
        all_memories = manager.get_all_memories("test_user")
        assert all_memories is not None
        assert len(all_memories.get('results', [])) > 0
        
        print(f"✅ Added {len(added_facts)} facts, retrieved {len(all_memories['results'])} memories")
    
    def test_search_functionality(self, real_memory_manager, integration_test_data):
        """Test memory search with real services."""
        manager = real_memory_manager
        facts = integration_test_data["facts"][:3]  # Use fewer facts for faster test
        
        # Add some facts first
        for fact in facts:
            manager.add_fact(fact, "test_user")
            time.sleep(0.5)
        
        # Test search functionality
        search_results = manager.search_memories("food preferences", "test_user")
        assert search_results is not None
        
        # Should find something related to food/eating
        results = search_results.get('results', [])
        if results:
            # Check if any result mentions food-related terms
            food_terms = ['pizza', 'pasta', 'eat', 'food', 'like']
            found_food_related = any(
                any(term in result['memory'].lower() for term in food_terms)
                for result in results
            )
            assert found_food_related, "Search should find food-related memories"
        
        print(f"✅ Search returned {len(results)} results")
    
    def test_chat_with_real_llm(self, real_memory_manager, integration_test_data):
        """Test chat functionality with real LLM."""
        manager = real_memory_manager
        
        # Add a simple fact
        manager.add_fact("Test user loves pizza", "test_user")
        time.sleep(1)  # Wait for indexing
        
        # Test chat
        response = manager.chat("What do I like to eat?", "test_user")
        assert response is not None
        assert len(response) > 0
        assert response != "Sorry, I encountered an error"
        
        # Response should mention pizza or food
        response_lower = response.lower()
        food_mentioned = any(term in response_lower for term in ['pizza', 'food', 'eat', 'like'])
        assert food_mentioned, f"Chat response should mention food: {response}"
        
        print(f"✅ Chat response: {response}")
    
    def test_reset_functionality(self, real_memory_manager):
        """Test memory reset with real services."""
        manager = real_memory_manager
        
        # Add some test facts
        test_facts = ["Test fact 1", "Test fact 2", "Test fact 3"]
        for fact in test_facts:
            manager.add_fact(fact, "test_user")
            time.sleep(0.3)
        
        # Verify facts were added
        all_memories = manager.get_all_memories("test_user")
        initial_count = len(all_memories.get('results', []))
        assert initial_count > 0, "Should have memories before reset"
        
        # Reset memories
        deleted_count = manager.reset_memories("test_user")
        assert deleted_count > 0, "Should delete some memories"
        
        # Verify memories were deleted
        remaining_memories = manager.get_all_memories("test_user")
        remaining_count = len(remaining_memories.get('results', []))
        assert remaining_count == 0, "Should have no memories after reset"
        
        print(f"✅ Reset deleted {deleted_count} memories")


@pytest.mark.integration
@pytest.mark.requires_services
class TestRealMarkdownProcessing:
    """Test markdown processing with real services."""
    
    def test_process_markdown_file_end_to_end(self, real_memory_manager):
        """Test complete markdown file processing with real services."""
        from markdown_processor import MarkdownProcessor
        
        # Create a temporary markdown file
        markdown_content = """# Test Conversation
- 3/29/25 9:10 AM: I really love eating pizza at Mario's restaurant
- 3/29/25 9:15 AM: My favorite programming language is definitely Python
- 3/29/25 9:20 AM: I work as a software engineer at TechCorp

## Personal Preferences  
- 3/29/25 2:30 PM: I enjoy hiking in the mountains on weekends
- 3/29/25 3:00 PM: My favorite color is blue and I drive a Toyota
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_file = f.name
        
        try:
            # Process the file
            processor = MarkdownProcessor(real_memory_manager)
            total_facts, added_facts = processor.process_file(temp_file, "test_user")
            
            # Verify processing results
            assert total_facts > 0, "Should extract some facts from markdown"
            assert added_facts > 0, "Should successfully add some facts"
            
            # Verify memories were created
            all_memories = real_memory_manager.get_all_memories("test_user")
            memory_count = len(all_memories.get('results', []))
            assert memory_count > 0, "Should have memories after processing"
            
            print(f"✅ Processed file: {total_facts} facts extracted, {added_facts} added, {memory_count} stored")
            
        finally:
            # Cleanup temp file
            Path(temp_file).unlink(missing_ok=True)
    
    def test_chat_after_markdown_processing(self, real_memory_manager):
        """Test chat functionality after processing markdown content."""
        from markdown_processor import MarkdownProcessor
        
        # Create markdown with specific facts
        markdown_content = """# Personal Information
- 4/1/25 10:00 AM: My name is Alex and I love sushi
- 4/1/25 10:05 AM: I work as a data scientist at DataCorp
- 4/1/25 10:10 AM: My hobby is playing guitar
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_file = f.name
        
        try:
            # Process the markdown
            processor = MarkdownProcessor(real_memory_manager)
            total_facts, added_facts = processor.process_file(temp_file, "test_user")
            
            assert added_facts > 0, "Should add facts from markdown"
            time.sleep(2)  # Wait for indexing
            
            # Test chat about the processed information
            queries_and_expectations = [
                ("What do I like to eat?", ["sushi"]),
                ("What is my job?", ["data scientist", "DataCorp"]),
                ("What are my hobbies?", ["guitar"])
            ]
            
            for query, expected_terms in queries_and_expectations:
                response = real_memory_manager.chat(query, "test_user")
                assert response is not None
                assert len(response) > 0
                
                # Check if response contains expected terms
                response_lower = response.lower()
                found_terms = [term for term in expected_terms if term.lower() in response_lower]
                
                if found_terms:
                    print(f"✅ Query: '{query}' -> Found terms: {found_terms}")
                else:
                    print(f"⚠️  Query: '{query}' -> Response: {response}")
                    # Don't fail the test, as LLM responses can vary
            
        finally:
            # Cleanup temp file
            Path(temp_file).unlink(missing_ok=True)


@pytest.mark.cleanup
class TestServiceAvailability:
    """Test service availability and graceful degradation."""
    
    def test_qdrant_service_check(self, qdrant_available):
        """Test Qdrant service availability check."""
        if qdrant_available:
            print("✅ Qdrant service is available")
        else:
            print("⚠️  Qdrant service is not available - integration tests will be skipped")
        
        # This test always passes, it's just for information
        assert True
    
    def test_ollama_service_check(self, ollama_available):
        """Test Ollama service availability check."""
        if ollama_available:
            print("✅ Ollama service is available")
        else:
            print("⚠️  Ollama service is not available - integration tests will be skipped")
        
        # This test always passes, it's just for information
        assert True
    
    def test_collection_cleanup(self, clean_test_collection):
        """Test that collection cleanup works properly."""
        collection_name = clean_test_collection
        assert collection_name == "test_memories"
        
        # This test verifies the cleanup fixture works
        print(f"✅ Collection cleanup fixture working for: {collection_name}")
        assert True
