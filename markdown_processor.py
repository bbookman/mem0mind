"""
Markdown processing module for extracting facts from markdown files.

This module handles parsing markdown files, extracting conversation entries,
and using LLM to extract factual statements for memory creation.
"""

import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from memory_manager import MemoryManager
from logging_config import get_logger, log_exception
from logging_decorators import log_function_calls, log_performance, log_exceptions
from prompt_manager import get_prompt


class MarkdownProcessor:
    """
    Process markdown files to extract facts for memory storage.
    
    This class handles parsing markdown files, extracting timestamped entries,
    and using LLM to extract factual statements that can be stored as memories.
    
    Attributes
    ----------
    memory_manager: MemoryManager instance for storing facts
    config: Configuration dictionary
    logger: Logger instance for this class
    
    Example
    -------
        >>> processor = MarkdownProcessor(memory_manager)
        >>> total, added = processor.process_file("conversations.md", "bruce")
        >>> print(f"Added {added} facts from {total} extracted")
    """
    
    @log_function_calls(include_params=False, include_result=False)
    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize MarkdownProcessor.

        Args
        ----
        memory_manager: MemoryManager instance for storing extracted facts
        """
        self.memory_manager = memory_manager
        self.config = memory_manager.config
        self.logger = get_logger(__name__)
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date strings from markdown files into datetime objects.
        
        Args
        ----
        date_str: String containing a date in various formats
        
        Returns
        -------
        Parsed datetime object or None if parsing fails
        
        Example
        -------
            >>> processor.parse_date("3/29/25 9:10 AM")
            datetime(2025, 3, 29, 9, 10)
        """
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',  # 3/29/25 9:10 AM
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)',  # 2025-03-29 09:10:00
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'  # 29 March 2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                date_text = match.group(1)
                try:
                    # Try multiple date formats
                    for fmt in [
                        "%m/%d/%y %I:%M %p", "%m/%d/%Y %I:%M %p",
                        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
                        "%d %b %Y", "%d %B %Y"
                    ]:
                        try:
                            return datetime.strptime(date_text, fmt)
                        except ValueError:
                            continue
                except Exception as e:
                    self.logger.warning(f"Failed to parse date '{date_text}': {e}")
        
        return None
    
    def extract_sections(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Extract sections from markdown text with their headers and content.
        
        Args
        ----
        markdown_text: Raw markdown text
        
        Returns
        -------
        List of dictionaries containing section headers and content
        
        Example
        -------
            >>> sections = processor.extract_sections("# Header\\nContent\\n## Sub\\nMore")
            >>> len(sections)
            2
        """
        # Split by headers (# or ## or ###)
        header_pattern = r'^(#{1,3})\s+(.+)$'
        lines = markdown_text.split('\n')
        sections = []
        current_section = None
        current_content = []
        
        for line in lines:
            header_match = re.match(header_pattern, line)
            if header_match:
                # Save previous section if it exists
                if current_section:
                    sections.append({
                        'level': len(current_section['level']),
                        'header': current_section['header'],
                        'content': '\n'.join(current_content)
                    })
                
                # Start new section
                current_section = {
                    'level': header_match.group(1),
                    'header': header_match.group(2).strip()
                }
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Add the last section
        if current_section:
            sections.append({
                'level': len(current_section['level']),
                'header': current_section['header'],
                'content': '\n'.join(current_content)
            })
        # If no sections were found (e.g., no headers), treat the whole file as one section
        elif not sections and markdown_text.strip():
            # Try to get a filename for the header, fallback to "General Facts"
            # This part is a bit tricky as extract_sections only gets text.
            # We'll rely on a placeholder or a more generic approach for now.
            # A better solution might involve passing the filename to this function.
            # For now, let's use a generic header.
            sections.append({
                'level': 0, # Indicates no specific header level
                'header': "General Facts from File",
                'content': markdown_text.strip()
            })

        return sections
    
    def extract_conversation_entries(self, section_content: str) -> List[Dict[str, Any]]:
        """
        Extract timestamped conversation entries from a section.
        
        Args
        ----
        section_content: Content of a markdown section
        
        Returns
        -------
        List of conversation entries with timestamps and content
        
        Example
        -------
            >>> entries = processor.extract_conversation_entries("- 3/29/25 9:10 AM: Hello")
            >>> len(entries)
            1
        """
        entries = []
        # Match timestamped entries (bullet points with timestamps)
        entry_pattern = r'[-*]\s*(.*?)(?=\n[-*]|\n\n|\n$|$)'
        matches = re.finditer(entry_pattern, section_content, re.DOTALL)
        
        for match in matches:
            entry_text = match.group(1).strip()
            # Try to extract timestamp from the entry
            timestamp = self.parse_date(entry_text)
            
            if timestamp:
                # Split timestamp from content
                content_parts = re.split(r'\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?[:\s]*', entry_text, 1)
                if len(content_parts) > 1:
                    content = content_parts[1].strip()
                else:
                    content = entry_text
            else:
                timestamp = None
                content = entry_text
            
            entries.append({
                'timestamp': timestamp,
                'content': content
            })
        
        # If no entries were extracted using the timestamped bullet point pattern,
        # and the section content is not empty, treat each line as an entry.
        if not entries and section_content.strip():
            lines = section_content.strip().split('\n')
            for line in lines:
                line_content = line.strip()
                if line_content: # Ensure the line is not empty
                    entries.append({
                        'timestamp': None, # No timestamp for these types of entries
                        'content': line_content
                    })
            self.logger.info(f"No bullet-point entries found; processed {len(lines)} lines as individual entries.")

        return entries
    
    def extract_facts_with_llm(self, context: str, content: str, 
                              timestamp: Optional[datetime] = None) -> List[str]:
        """
        Use LLM to extract factual statements from conversation content.
        
        Args
        ----
        context: Context information (section headers, etc.)
        content: Conversation content to extract facts from
        timestamp: Timestamp of the conversation entry
        
        Returns
        -------
        List of extracted factual statements
        
        Example
        -------
            >>> facts = processor.extract_facts_with_llm("Meeting", "I live in NYC")
            >>> len(facts) > 0
            True
        """
        # Format the timestamp for inclusion in the prompt
        time_context = ""
        if timestamp:
            time_context = f"This information was recorded on {timestamp.strftime('%B %d, %Y at %I:%M %p')}."
        
        # Get fact extraction prompt from prompt manager
        try:
            prompt = get_prompt('extraction', 'markdown_facts',
                              context=context,
                              time_context=time_context,
                              content=content)
        except Exception as e:
            self.logger.error(f"Failed to load extraction prompt: {e}")
            # Fallback to basic extraction
            prompt = f"Extract key facts from: {content}"

        try:
            # Use the memory manager's Ollama API call method
            response = self.memory_manager._call_ollama_api(prompt)
            
            # Split the response into individual facts
            facts = [fact.strip() for fact in response.strip().split('\n') if fact.strip()]
            return facts
            
        except Exception as e:
            self.logger.error(f"Error extracting facts with LLM: {e}")
            return []

    @log_performance(threshold_seconds=10.0)
    @log_exceptions("Markdown file processing failed")
    def process_file(self, file_path: str, user_id: Optional[str] = None) -> Tuple[int, int]:
        """
        Process a markdown file and extract memories.

        Args
        ----
        file_path: Path to the markdown file
        user_id: User ID to associate with the memories

        Returns
        -------
        Tuple of (total facts extracted, successfully added facts)

        Example
        -------
            >>> total, added = processor.process_file("conversations.md", "bruce")
            >>> total > 0
            True
        """
        user_id = user_id or self.memory_manager.user_id
        self.logger.info(f"Processing file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_text = f.read()

            # Extract sections
            sections = self.extract_sections(markdown_text)
            self.logger.info(f"Found {len(sections)} sections")

            total_facts = 0
            added_facts = 0

            # Process each section
            for section in sections:
                section_header = section['header']
                self.logger.info(f"Processing section: {section_header}")

                # Extract conversation entries
                entries = self.extract_conversation_entries(section['content'])
                self.logger.info(f"Found {len(entries)} entries in section")

                # Process each entry
                for entry in entries:
                    # Skip empty entries
                    if not entry['content'] or len(entry['content'].strip()) < 10:
                        continue

                    # Extract facts using LLM
                    facts = self.extract_facts_with_llm(
                        context=section_header,
                        content=entry['content'],
                        timestamp=entry['timestamp']
                    )

                    total_facts += len(facts)

                    # Add each fact to memory
                    for fact in facts:
                        metadata = {}
                        if entry['timestamp']:
                            metadata["timestamp"] = entry['timestamp'].isoformat()

                        result = self.memory_manager.add_fact(
                            fact=fact,
                            user_id=user_id,
                            metadata=metadata
                        )

                        if result and result.get('results'):
                            added_facts += 1

                    # Small delay to prevent rate limiting
                    time.sleep(0.5)

            self.logger.info(f"Completed processing file: {file_path}")
            self.logger.info(f"Total facts extracted: {total_facts}")
            self.logger.info(f"Successfully added facts: {added_facts}")

            return total_facts, added_facts

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {e}")
            return 0, 0

    def process_directories(self, user_id: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Process all markdown directories from configuration.

        Args
        ----
        user_id: User ID to associate with the memories

        Returns
        -------
        Tuple of (files processed, total facts extracted, successfully added facts)

        Example
        -------
            >>> files, total, added = processor.process_directories("bruce")
            >>> print(f"Processed {files} files, added {added}/{total} facts")
        """
        user_id = user_id or self.memory_manager.user_id
        directories = self.config.get('markdown_directories', [])
        processing_options = self.config.get('processing_options', {})

        recursive = processing_options.get('recursive', True)
        file_extensions = processing_options.get('file_extensions', ['.md', '.markdown'])

        self.logger.info(f"Processing {len(directories)} directories")

        all_files = []

        # Collect all markdown files from directories
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                self.logger.warning(f"Directory does not exist: {directory}")
                continue

            if not dir_path.is_dir():
                self.logger.warning(f"Path is not a directory: {directory}")
                continue

            # Find markdown files
            for ext in file_extensions:
                pattern = f"**/*{ext}" if recursive else f"*{ext}"
                files = list(dir_path.glob(pattern))
                all_files.extend(files)
                self.logger.info(f"Found {len(files)} {ext} files in {directory}")

        if not all_files:
            self.logger.warning("No markdown files found in configured directories")
            return 0, 0, 0

        self.logger.info(f"Processing {len(all_files)} total markdown files")

        total_files = len(all_files)
        total_facts = 0
        added_facts = 0

        # Process each file
        for i, file_path in enumerate(all_files, 1):
            self.logger.info(f"Processing file {i}/{total_files}: {file_path}")
            file_total, file_added = self.process_file(str(file_path), user_id)
            total_facts += file_total
            added_facts += file_added

            # Batch delay
            if i % processing_options.get('batch_size', 10) == 0:
                delay = processing_options.get('delay_between_batches', 1.0)
                self.logger.info(f"Batch complete, waiting {delay} seconds...")
                time.sleep(delay)

        self.logger.info("=" * 50)
        self.logger.info(f"Processing complete!")
        self.logger.info(f"Files processed: {total_files}")
        self.logger.info(f"Total facts extracted: {total_facts}")
        self.logger.info(f"Successfully added facts: {added_facts}")

        return total_files, total_facts, added_facts
