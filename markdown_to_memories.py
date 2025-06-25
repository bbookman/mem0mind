import os
import re
import time
from datetime import datetime
import logging
from pathlib import Path
import argparse
from typing import List, Dict, Any, Optional, Tuple
import requests
from mem0 import Memory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("markdown_processing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Memory system configuration
config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:latest",
            "temperature": 0.1,
            "max_tokens": 2000,
            "ollama_base_url": "http://localhost:11434",
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text:latest",
            "ollama_base_url": "http://localhost:11434",
        },
    },
}

def parse_date(date_str: str) -> Optional[datetime]:
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
        >>> parse_date("3/29/25 9:10 AM")
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
                logger.warning(f"Failed to parse date '{date_text}': {e}")
    
    return None

def extract_sections(markdown_text: str) -> List[Dict[str, Any]]:
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
        >>> sections = extract_sections("# Header\\nContent\\n## Subheader\\nMore content")
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
    
    return sections

def extract_conversation_entries(section_content: str) -> List[Dict[str, Any]]:
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
        >>> entries = extract_conversation_entries("- 3/29/25 9:10 AM: Hello\\n- 3/29/25 9:15 AM: Hi")
        >>> len(entries)
        2
    """
    entries = []
    # Match timestamped entries (bullet points with timestamps)
    entry_pattern = r'[-*]\s*(.*?)(?=\n[-*]|\n\n|\n$|$)'
    matches = re.finditer(entry_pattern, section_content, re.DOTALL)
    
    for match in matches:
        entry_text = match.group(1).strip()
        # Try to extract timestamp from the entry
        timestamp = parse_date(entry_text)
        
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
    
    return entries

def extract_facts_with_llm(context: str, content: str, timestamp: Optional[datetime] = None) -> List[str]:
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
        >>> facts = extract_facts_with_llm("Meeting", "I live in New York", datetime(2025, 3, 29))
        >>> len(facts) > 0
        True
    """
    # Format the timestamp for inclusion in the prompt
    time_context = ""
    if timestamp:
        time_context = f"This information was recorded on {timestamp.strftime('%B %d, %Y at %I:%M %p')}."
    
    # Create prompt for the LLM
    prompt = f"""Extract discrete, factual statements from the following conversation text.
Context: {context}
{time_context}

Conversation text:
"{content}"

Instructions:
1. Extract 1-5 clear, factual statements from the text
2. Format each as a complete sentence with a subject
3. Include the date/time context in the fact when relevant
4. For multilingual content, preserve the original language
5. Focus on personal details, preferences, events, and relationships
6. Ignore small talk, greetings, or irrelevant details

Output only the extracted facts, one per line, with no additional text or explanations:"""

    try:
        # Use direct Ollama API call for more control
        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.1:latest",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 2000
            }
        }
        
        response = requests.post(ollama_url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'response' in result:
            # Split the response into individual facts
            facts = [fact.strip() for fact in result['response'].strip().split('\n') if fact.strip()]
            return facts
        else:
            logger.warning("No response from LLM")
            return []
            
    except Exception as e:
        logger.error(f"Error extracting facts with LLM: {e}")
        return []

def safe_add_memory(memory_instance: Memory, fact: str, user_id: str, 
                    timestamp: Optional[datetime] = None, max_retries: int = 3) -> Optional[Dict]:
    """
    Safely add a memory with retry logic and error handling.
    
    Args
    ----
    memory_instance: Memory instance
    fact: Factual statement to add
    user_id: User ID to associate with the memory
    timestamp: Optional timestamp for the memory
    max_retries: Maximum number of retry attempts
    
    Returns
    -------
    Result from memory.add() or None if failed
    
    Example
    -------
        >>> result = safe_add_memory(memory, "Bruce lives in New York", "bruce")
        >>> result is not None
        True
    """
    metadata = {}
    if timestamp:
        metadata["timestamp"] = timestamp.isoformat()
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Adding fact: '{fact}'")
            result = memory_instance.add(fact, user_id=user_id, metadata=metadata)
            
            if result and result.get('results'):
                logger.info(f"✅ Added: {result['results'][0]['memory']}")
                return result
            else:
                logger.warning(f"⚠️ No memory created from: '{fact}'")
                return result
                
        except Exception as e:
            logger.error(f"❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                logger.error(f"Failed after {max_retries} attempts")
                return None

def process_markdown_file(file_path: str, memory_instance: Memory, user_id: str) -> Tuple[int, int]:
    """
    Process a markdown file and extract memories.
    
    Args
    ----
    file_path: Path to the markdown file
    memory_instance: Memory instance
    user_id: User ID to associate with the memories
    
    Returns
    -------
    Tuple of (total facts extracted, successfully added facts)
    
    Example
    -------
        >>> total, added = process_markdown_file("conversations.md", memory, "bruce")
        >>> total > 0
        True
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        
        # Extract sections
        sections = extract_sections(markdown_text)
        logger.info(f"Found {len(sections)} sections")
        
        total_facts = 0
        added_facts = 0
        
        # Process each section
        for section in sections:
            section_header = section['header']
            logger.info(f"Processing section: {section_header}")
            
            # Extract conversation entries
            entries = extract_conversation_entries(section['content'])
            logger.info(f"Found {len(entries)} entries in section")
            
            # Process each entry
            for entry in entries:
                # Skip empty entries
                if not entry['content'] or len(entry['content'].strip()) < 10:
                    continue
                
                # Extract facts using LLM
                facts = extract_facts_with_llm(
                    context=section_header,
                    content=entry['content'],
                    timestamp=entry['timestamp']
                )
                
                total_facts += len(facts)
                
                # Add each fact to memory
                for fact in facts:
                    result = safe_add_memory(
                        memory_instance=memory_instance,
                        fact=fact,
                        user_id=user_id,
                        timestamp=entry['timestamp']
                    )
                    
                    if result and result.get('results'):
                        added_facts += 1
                
                # Small delay to prevent rate limiting
                time.sleep(0.5)
        
        logger.info(f"Completed processing file: {file_path}")
        logger.info(f"Total facts extracted: {total_facts}")
        logger.info(f"Successfully added facts: {added_facts}")
        
        return total_facts, added_facts
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return 0, 0

def main():
    """
    Main function to process markdown files into memories.
    """
    parser = argparse.ArgumentParser(description="Process markdown files into structured memories")
    parser.add_argument("--input", "-i", required=True, help="Input markdown file or directory")
    parser.add_argument("--user", "-u", default="bruce", help="User ID for the memories")
    parser.add_argument("--recursive", "-r", action="store_true", help="Process directories recursively")
    args = parser.parse_args()
    
    # Initialize Memory
    logger.info("Initializing Memory...")
    try:
        memory = Memory.from_config(config)
        logger.info("✅ Memory initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize memory: {e}")
        return
    
    # Process input path
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Process single file
        process_markdown_file(str(input_path), memory, args.user)
    elif input_path.is_dir():
        # Process directory
        pattern = "**/*.md" if args.recursive else "*.md"
        markdown_files = list(input_path.glob(pattern))
        logger.info(f"Found {len(markdown_files)} markdown files to process")
        
        total_files = len(markdown_files)
        total_facts = 0
        added_facts = 0
        
        for i, file_path in enumerate(markdown_files, 1):
            logger.info(f"Processing file {i}/{total_files}: {file_path}")
            file_total, file_added = process_markdown_file(str(file_path), memory, args.user)
            total_facts += file_total
            added_facts += file_added
        
        logger.info("=" * 50)
        logger.info(f"Processing complete!")
        logger.info(f"Files processed: {total_files}")
        logger.info(f"Total facts extracted: {total_facts}")
        logger.info(f"Successfully added facts: {added_facts}")
    else:
        logger.error(f"Input path does not exist: {input_path}")

if __name__ == "__main__":
    main()