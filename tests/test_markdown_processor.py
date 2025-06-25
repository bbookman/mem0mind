"""
Tests for MarkdownProcessor class.

This module tests markdown processing functionality including:
- Date parsing from various formats
- Section extraction from markdown
- Conversation entry extraction with timestamps
- Fact extraction using LLM
- End-to-end file processing
"""

import pytest
from datetime import datetime
from unittest.mock import patch, Mock
import tempfile
from pathlib import Path

from markdown_processor import MarkdownProcessor


class TestMarkdownProcessorDateParsing:
    """Test date parsing functionality."""
    
    def test_parse_date_with_am_pm(self, markdown_processor_with_mocks):
        """Test parsing dates with AM/PM format."""
        processor = markdown_processor_with_mocks
        
        # Test various AM/PM formats
        test_cases = [
            ("3/29/25 9:10 AM", datetime(2025, 3, 29, 9, 10)),
            ("12/31/24 11:45 PM", datetime(2024, 12, 31, 23, 45)),
            ("1/1/25 12:00 AM", datetime(2025, 1, 1, 0, 0)),
        ]
        
        for date_str, expected in test_cases:
            result = processor.parse_date(date_str)
            assert result == expected
    
    def test_parse_date_24_hour_format(self, markdown_processor_with_mocks):
        """Test parsing dates with 24-hour format."""
        processor = markdown_processor_with_mocks
        
        test_cases = [
            ("2025-03-29 09:10:00", datetime(2025, 3, 29, 9, 10)),
            ("2025-12-31 23:45", datetime(2025, 12, 31, 23, 45)),
        ]
        
        for date_str, expected in test_cases:
            result = processor.parse_date(date_str)
            assert result == expected
    
    def test_parse_date_invalid_format(self, markdown_processor_with_mocks):
        """Test parsing invalid date formats returns None."""
        processor = markdown_processor_with_mocks
        
        invalid_dates = [
            "not a date",
            "13/45/99 25:70 XM",
            "",
            "random text"
        ]
        
        for date_str in invalid_dates:
            result = processor.parse_date(date_str)
            assert result is None
    
    def test_parse_date_embedded_in_text(self, markdown_processor_with_mocks):
        """Test parsing dates embedded in longer text."""
        processor = markdown_processor_with_mocks
        
        text_with_date = "Meeting scheduled for 3/29/25 9:10 AM with the team"
        result = processor.parse_date(text_with_date)
        
        assert result == datetime(2025, 3, 29, 9, 10)


class TestMarkdownProcessorSectionExtraction:
    """Test markdown section extraction."""
    
    def test_extract_sections_basic(self, markdown_processor_with_mocks):
        """Test basic section extraction with headers."""
        processor = markdown_processor_with_mocks
        
        markdown_text = """# Main Header
This is the main content.

## Sub Header
This is sub content.

### Sub Sub Header
This is nested content."""
        
        sections = processor.extract_sections(markdown_text)
        
        assert len(sections) == 3
        assert sections[0]['level'] == 1
        assert sections[0]['header'] == 'Main Header'
        assert 'main content' in sections[0]['content']
        
        assert sections[1]['level'] == 2
        assert sections[1]['header'] == 'Sub Header'
        assert 'sub content' in sections[1]['content']
        
        assert sections[2]['level'] == 3
        assert sections[2]['header'] == 'Sub Sub Header'
        assert 'nested content' in sections[2]['content']
    
    def test_extract_sections_no_headers(self, markdown_processor_with_mocks):
        """Test extraction when no headers are present."""
        processor = markdown_processor_with_mocks
        
        markdown_text = "Just some plain text without headers."
        sections = processor.extract_sections(markdown_text)
        
        assert len(sections) == 0
    
    def test_extract_sections_empty_content(self, markdown_processor_with_mocks):
        """Test extraction with headers but no content."""
        processor = markdown_processor_with_mocks
        
        markdown_text = """# Header One

## Header Two

### Header Three
"""
        
        sections = processor.extract_sections(markdown_text)
        
        assert len(sections) == 3
        for section in sections:
            assert section['content'].strip() == ''


class TestMarkdownProcessorConversationExtraction:
    """Test conversation entry extraction."""
    
    def test_extract_conversation_entries_with_timestamps(self, markdown_processor_with_mocks):
        """Test extracting conversation entries with timestamps."""
        processor = markdown_processor_with_mocks
        
        section_content = """- 3/29/25 9:10 AM: Discussed project timeline with John
- 3/29/25 9:15 AM: John mentioned he prefers working remotely
- 3/29/25 9:20 AM: We agreed to meet weekly on Fridays"""
        
        entries = processor.extract_conversation_entries(section_content)
        
        assert len(entries) == 3
        
        # Check first entry
        assert entries[0]['timestamp'] == datetime(2025, 3, 29, 9, 10)
        assert 'Discussed project timeline with John' in entries[0]['content']
        
        # Check second entry
        assert entries[1]['timestamp'] == datetime(2025, 3, 29, 9, 15)
        assert 'John mentioned he prefers working remotely' in entries[1]['content']
        
        # Check third entry
        assert entries[2]['timestamp'] == datetime(2025, 3, 29, 9, 20)
        assert 'We agreed to meet weekly on Fridays' in entries[2]['content']
    
    def test_extract_conversation_entries_without_timestamps(self, markdown_processor_with_mocks):
        """Test extracting entries without timestamps."""
        processor = markdown_processor_with_mocks
        
        section_content = """- This is a bullet point without timestamp
- Another point without time
- Yet another entry"""
        
        entries = processor.extract_conversation_entries(section_content)
        
        assert len(entries) == 3
        for entry in entries:
            assert entry['timestamp'] is None
            assert len(entry['content']) > 0
    
    def test_extract_conversation_entries_mixed(self, markdown_processor_with_mocks):
        """Test extracting mixed entries (with and without timestamps)."""
        processor = markdown_processor_with_mocks
        
        section_content = """- 3/29/25 9:10 AM: Meeting with John
- Regular bullet point without timestamp
- 3/29/25 2:30 PM: Had lunch at Mario's"""
        
        entries = processor.extract_conversation_entries(section_content)
        
        assert len(entries) == 3
        assert entries[0]['timestamp'] is not None
        assert entries[1]['timestamp'] is None
        assert entries[2]['timestamp'] is not None
    
    def test_extract_conversation_entries_empty_content(self, markdown_processor_with_mocks):
        """Test extraction from empty content."""
        processor = markdown_processor_with_mocks
        
        entries = processor.extract_conversation_entries("")
        assert len(entries) == 0


class TestMarkdownProcessorFactExtraction:
    """Test LLM-based fact extraction."""
    
    def test_extract_facts_with_llm_success(self, markdown_processor_with_mocks):
        """Test successful fact extraction using LLM."""
        processor = markdown_processor_with_mocks

        # Mock the memory manager's _call_ollama_api method
        processor.memory_manager._call_ollama_api = Mock(
            return_value="User likes pizza\nUser works at TechCorp\nUser prefers remote work"
        )
        
        facts = processor.extract_facts_with_llm(
            context="Meeting Notes",
            content="I love pizza and work at TechCorp. I prefer working from home.",
            timestamp=datetime(2025, 3, 29, 9, 10)
        )
        
        assert len(facts) == 3
        assert "User likes pizza" in facts
        assert "User works at TechCorp" in facts
        assert "User prefers remote work" in facts
        
        # Verify API was called with proper prompt
        processor.memory_manager._call_ollama_api.assert_called_once()
        call_args = processor.memory_manager._call_ollama_api.call_args[0][0]
        assert "Meeting Notes" in call_args
        assert "March 29, 2025 at 09:10 AM" in call_args
    
    def test_extract_facts_with_llm_no_timestamp(self, markdown_processor_with_mocks):
        """Test fact extraction without timestamp."""
        processor = markdown_processor_with_mocks

        processor.memory_manager._call_ollama_api = Mock(return_value="User enjoys coffee")
        
        facts = processor.extract_facts_with_llm(
            context="Personal Notes",
            content="I really enjoy my morning coffee",
            timestamp=None
        )
        
        assert len(facts) == 1
        assert "User enjoys coffee" in facts
        
        # Verify timestamp context is not included
        call_args = processor.memory_manager._call_ollama_api.call_args[0][0]
        assert "This information was recorded on" not in call_args
    
    def test_extract_facts_with_llm_empty_response(self, markdown_processor_with_mocks):
        """Test handling of empty LLM response."""
        processor = markdown_processor_with_mocks

        processor.memory_manager._call_ollama_api = Mock(return_value="")
        
        facts = processor.extract_facts_with_llm(
            context="Notes",
            content="Some content",
            timestamp=None
        )
        
        assert len(facts) == 0
    
    def test_extract_facts_with_llm_api_error(self, markdown_processor_with_mocks):
        """Test handling of API errors during fact extraction."""
        processor = markdown_processor_with_mocks

        processor.memory_manager._call_ollama_api = Mock(side_effect=Exception("API Error"))
        
        facts = processor.extract_facts_with_llm(
            context="Notes",
            content="Some content",
            timestamp=None
        )
        
        assert len(facts) == 0


class TestMarkdownProcessorFileProcessing:
    """Test end-to-end file processing."""
    
    @patch('markdown_processor.MarkdownProcessor.extract_facts_with_llm')
    def test_process_file_success(self, mock_extract_facts, markdown_processor_with_mocks, temp_markdown_dir):
        """Test successful processing of a markdown file."""
        processor = markdown_processor_with_mocks
        
        # Mock fact extraction to return predictable results
        mock_extract_facts.return_value = ["User discussed project timeline", "User likes pizza"]
        
        # Process the sample file
        file_path = Path(temp_markdown_dir) / "conversations.md"
        total_facts, added_facts = processor.process_file(str(file_path), "test_user")
        
        assert total_facts > 0
        assert added_facts > 0
        assert mock_extract_facts.call_count > 0
        
        # Verify memory manager was called to add facts
        assert processor.memory_manager.memory.add.call_count > 0
    
    def test_process_file_not_found(self, markdown_processor_with_mocks):
        """Test processing non-existent file."""
        processor = markdown_processor_with_mocks
        
        total_facts, added_facts = processor.process_file("nonexistent.md", "test_user")
        
        assert total_facts == 0
        assert added_facts == 0
    
    @patch('markdown_processor.MarkdownProcessor.extract_facts_with_llm')
    def test_process_file_no_facts_extracted(self, mock_extract_facts, markdown_processor_with_mocks, temp_markdown_dir):
        """Test processing file when no facts are extracted."""
        processor = markdown_processor_with_mocks
        
        # Mock no facts extracted
        mock_extract_facts.return_value = []
        
        file_path = Path(temp_markdown_dir) / "conversations.md"
        total_facts, added_facts = processor.process_file(str(file_path), "test_user")
        
        assert total_facts == 0
        assert added_facts == 0


class TestMarkdownProcessorDirectoryProcessing:
    """Test directory processing functionality."""
    
    @patch('markdown_processor.MarkdownProcessor.process_file')
    def test_process_directories_success(self, mock_process_file, markdown_processor_with_mocks, temp_markdown_dir):
        """Test successful processing of directories."""
        processor = markdown_processor_with_mocks
        
        # Update config to point to temp directory
        processor.config['markdown_directories'] = [temp_markdown_dir]
        
        # Mock file processing results
        mock_process_file.return_value = (5, 4)  # 5 facts extracted, 4 added
        
        files_processed, total_facts, added_facts = processor.process_directories("test_user")
        
        assert files_processed == 2  # Two sample files in temp directory
        assert total_facts == 10  # 2 files * 5 facts each
        assert added_facts == 8   # 2 files * 4 facts each
        assert mock_process_file.call_count == 2
    
    def test_process_directories_nonexistent_directory(self, markdown_processor_with_mocks):
        """Test processing when directories don't exist."""
        processor = markdown_processor_with_mocks
        
        # Set non-existent directory
        processor.config['markdown_directories'] = ["/nonexistent/directory"]
        
        files_processed, total_facts, added_facts = processor.process_directories("test_user")
        
        assert files_processed == 0
        assert total_facts == 0
        assert added_facts == 0
    
    def test_process_directories_empty_config(self, markdown_processor_with_mocks):
        """Test processing with empty directory configuration."""
        processor = markdown_processor_with_mocks
        
        # Set empty directories list
        processor.config['markdown_directories'] = []
        
        files_processed, total_facts, added_facts = processor.process_directories("test_user")
        
        assert files_processed == 0
        assert total_facts == 0
        assert added_facts == 0
