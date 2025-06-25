import os
import time
import requests
import json
from mem0 import Memory

# Configuration (same as in your other files)
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
            "temperature": 0.7,  # Higher for more conversational responses
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

def chat_with_memories(query, user_id="bruce", limit=5):
    """
    Chat with an LLM using relevant memories as context.

    Args
    ----
    query: The user's question or message
    user_id: User identifier to retrieve memories for
    limit: Maximum number of memories to include as context

    Returns
    -------
    The LLM's response based on relevant memories

    Example
    -------
        >>> response = chat_with_memories("Where does Bruce live?")
        >>> print(response)
        "Based on my information, Bruce lives in Wilmington, NC."
    """
    try:
        # Initialize Memory
        print("Initializing Memory...")
        m = Memory.from_config(config)
        print("✅ Memory initialized")
        
        # Retrieve relevant memories
        print(f"Searching for memories relevant to: '{query}'")
        memories = m.search(query, user_id=user_id, limit=limit)
        
        if not memories or not memories.get('results'):
            print("⚠️ No relevant memories found")
            context = f"No specific information available about {user_id}."
        else:
            # Format memories as context with better structure
            memory_facts = [mem['memory'] for mem in memories['results']]
            print(f"Found {len(memory_facts)} relevant memories:")
            for i, fact in enumerate(memory_facts, 1):
                print(f"  {i}. {fact}")

            # Improve context formatting to be more natural
            context = f"Facts about {user_id}:\n" + "\n".join(f"• {fact}" for fact in memory_facts)
        
        # Create improved prompt for LLM with better pronoun handling
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
        
        # Get LLM response using direct Ollama API call
        print("Generating response...")

        # Use requests to call Ollama directly since mem0's LLM wrapper has issues

        ollama_url = "http://localhost:11434/api/generate"
        payload = {
            "model": "llama3.1:latest",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 2000
            }
        }

        try:
            response = requests.post(ollama_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            if 'response' in result:
                return result['response'].strip()
            else:
                return "Sorry, I couldn't generate a response."

        except requests.exceptions.RequestException as e:
            print(f"❌ Error calling Ollama API: {e}")
            return "Sorry, I couldn't connect to the language model."
        
    except Exception as e:
        print(f"❌ Error during chat: {e}")
        return f"Sorry, I encountered an error: {str(e)}"

if __name__ == "__main__":
    print("Memory Chat - Ask questions about Bruce")
    print("=" * 60)
    print("Type 'exit' to quit")
    
    while True:
        user_input = input("\nYour question: ").strip()
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        response = chat_with_memories(user_input)
        print("\nResponse:")
        print(response)
