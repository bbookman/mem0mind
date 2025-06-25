"""
Core memory management module for the unified memory application.

This module provides the MemoryManager class that handles all memory operations
including initialization, adding memories, searching, and chat functionality.
"""

import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from mem0 import Memory
from pathlib import Path


class MemoryManager:
    """
    Manage memory operations with configuration-based setup.
    
    This class handles memory initialization, adding facts, searching memories,
    and providing chat functionality with proper error handling and retry logic.
    
    Attributes
    ----------
    config: Configuration dictionary for memory setup
    memory: mem0 Memory instance
    user_id: Default user ID for memory operations
    logger: Logger instance for this class
    
    Example
    -------
        >>> manager = MemoryManager("config.json")
        >>> manager.add_fact("Bruce likes pizza", "bruce")
        >>> response = manager.chat("What does Bruce like to eat?", "bruce")
    """
    
    def __init__(self, config_path: str):
        """
        Initialize MemoryManager with configuration.
        
        Args
        ----
        config_path: Path to the JSON configuration file
        
        Raises
        ------
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.memory = None
        self.user_id = self.config.get('processing_options', {}).get('user_id', 'default')
        self._initialize_memory()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from JSON file.
        
        Args
        ----
        config_path: Path to configuration file
        
        Returns
        -------
        Configuration dictionary
        
        Raises
        ------
        FileNotFoundError: If config file doesn't exist
        ValueError: If JSON is invalid
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def _initialize_memory(self):
        """
        Initialize the mem0 Memory instance.
        
        Raises
        ------
        RuntimeError: If memory initialization fails
        """
        try:
            memory_config = self.config['memory_config']
            self.memory = Memory.from_config(memory_config)
            self.logger.info("✅ Memory initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize memory: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def add_fact(self, fact: str, user_id: Optional[str] = None, 
                 metadata: Optional[Dict] = None, max_retries: int = 3) -> Optional[Dict]:
        """
        Add a fact to memory with retry logic.
        
        Args
        ----
        fact: Factual statement to add
        user_id: User ID (defaults to configured user_id)
        metadata: Optional metadata dictionary
        max_retries: Maximum retry attempts
        
        Returns
        -------
        Result from memory.add() or None if failed
        
        Example
        -------
            >>> result = manager.add_fact("Bruce lives in NYC", "bruce")
            >>> result['results'][0]['memory']
            'Lives in NYC'
        """
        user_id = user_id or self.user_id
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Adding fact (attempt {attempt + 1}): '{fact}'")
                result = self.memory.add(fact, user_id=user_id, metadata=metadata)
                
                if result and result.get('results'):
                    self.logger.info(f"✅ Added: {result['results'][0]['memory']}")
                    return result
                else:
                    self.logger.warning(f"⚠️ No memory created from: '{fact}'")
                    return result
                    
            except Exception as e:
                self.logger.error(f"❌ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    self.logger.error(f"Failed after {max_retries} attempts")
                    return None
    
    def search_memories(self, query: str, user_id: Optional[str] = None, 
                       limit: int = 5) -> Optional[Dict]:
        """
        Search for relevant memories.
        
        Args
        ----
        query: Search query
        user_id: User ID (defaults to configured user_id)
        limit: Maximum number of results
        
        Returns
        -------
        Search results dictionary or None if failed
        
        Example
        -------
            >>> results = manager.search_memories("food preferences", "bruce")
            >>> len(results['results'])
            3
        """
        user_id = user_id or self.user_id
        
        try:
            results = self.memory.search(query, user_id=user_id, limit=limit)
            self.logger.debug(f"Search for '{query}' returned {len(results.get('results', []))} results")
            return results
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return None
    
    def get_all_memories(self, user_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get all memories for a user.
        
        Args
        ----
        user_id: User ID (defaults to configured user_id)
        
        Returns
        -------
        All memories dictionary or None if failed
        """
        user_id = user_id or self.user_id
        
        try:
            results = self.memory.get_all(user_id=user_id)
            self.logger.debug(f"Retrieved {len(results.get('results', []))} total memories")
            return results
        except Exception as e:
            self.logger.error(f"Failed to get all memories: {e}")
            return None
    
    def reset_memories(self, user_id: Optional[str] = None) -> int:
        """
        Reset all memories for a user.
        
        Args
        ----
        user_id: User ID (defaults to configured user_id)
        
        Returns
        -------
        Number of memories deleted
        """
        user_id = user_id or self.user_id
        
        try:
            self.logger.info(f"Resetting all memories for user '{user_id}'...")
            all_memories = self.get_all_memories(user_id)
            
            if not all_memories or not all_memories.get('results'):
                self.logger.info("No memories found to delete")
                return 0
            
            deleted_count = 0
            for memory in all_memories['results']:
                try:
                    self.memory.delete(memory_id=memory['id'])
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to delete memory {memory['id']}: {e}")
            
            self.logger.info(f"✅ Deleted {deleted_count} memories")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error during reset: {e}")
            return 0

    def chat(self, query: str, user_id: Optional[str] = None,
             max_context_memories: Optional[int] = None) -> str:
        """
        Chat with memories using LLM.

        Args
        ----
        query: User's question or message
        user_id: User ID (defaults to configured user_id)
        max_context_memories: Max memories to include as context

        Returns
        -------
        LLM response based on relevant memories

        Example
        -------
            >>> response = manager.chat("What do I like to eat?", "bruce")
            >>> "pizza" in response.lower()
            True
        """
        user_id = user_id or self.user_id
        max_context_memories = max_context_memories or self.config.get('chat_options', {}).get('max_context_memories', 5)

        try:
            # Search for relevant memories
            self.logger.debug(f"Searching for memories relevant to: '{query}'")
            memories = self.search_memories(query, user_id, max_context_memories)

            # Format context
            if not memories or not memories.get('results'):
                self.logger.debug("No relevant memories found")
                context = f"No specific information available about {user_id}."
            else:
                memory_facts = [mem['memory'] for mem in memories['results']]
                self.logger.debug(f"Found {len(memory_facts)} relevant memories")
                context = f"Facts about {user_id}:\n" + "\n".join(f"• {fact}" for fact in memory_facts)

            # Create improved prompt
            prompt = f"""You are a helpful personal assistant for {user_id}. You have access to the following facts about {user_id}:

{context}

IMPORTANT INSTRUCTIONS:
- When the user says "I", "me", "my", or "mine", they are referring to {user_id}
- Use the facts above to answer questions confidently when the information is available
- Connect related concepts (e.g., "favorite food" relates to "what I like to eat")
- Give natural, conversational responses as if you know {user_id} personally
- Only say you don't know if the facts truly don't contain relevant information

Examples of how to handle pronouns:
- "What do I like?" → "What does {user_id} like?"
- "What's my favorite?" → "What's {user_id}'s favorite?"
- "Tell me about myself" → "Tell me about {user_id}"

User question: {query}

Provide a helpful, natural response based on the available facts:"""

            # Get LLM response using direct Ollama API
            return self._call_ollama_api(prompt)

        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def _call_ollama_api(self, prompt: str) -> str:
        """
        Call Ollama API directly for LLM responses.

        Args
        ----
        prompt: Prompt to send to the LLM

        Returns
        -------
        LLM response text

        Raises
        ------
        requests.RequestException: If API call fails
        """
        chat_config = self.config.get('chat_options', {})
        memory_config = self.config['memory_config']['llm']['config']

        ollama_url = f"{memory_config['ollama_base_url']}/api/generate"
        payload = {
            "model": memory_config['model'],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": chat_config.get('temperature', 0.7),
                "num_predict": memory_config.get('max_tokens', 2000)
            }
        }

        timeout = chat_config.get('response_timeout', 60)

        try:
            response = requests.post(ollama_url, json=payload, timeout=timeout)
            response.raise_for_status()
            result = response.json()

            if 'response' in result:
                return result['response'].strip()
            else:
                return "Sorry, I couldn't generate a response."

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama API error: {e}")
            raise
