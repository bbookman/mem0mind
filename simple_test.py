import os
import time
from mem0 import Memory

# Simple configuration without debug logging
config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test_simple",
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

def safe_add_memory(memory_instance, text, user_id, max_retries=3):
    """Safely add memory with retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}: Adding '{text}'")
            result = memory_instance.add(text, user_id=user_id)
            
            if result and result.get('results'):
                print(f"✅ SUCCESS: {result['results'][0]['memory']}")
                return result
            else:
                print(f"⚠️  No facts extracted from: '{text}'")
                return result
                
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"Failed after {max_retries} attempts")
                return None

# Initialize Memory
print("Initializing Memory...")
try:
    m = Memory.from_config(config)
    print("✅ Memory initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize memory: {e}")
    exit(1)

# Test memories with retry logic
test_memories = [
    "Bruce works at Walgreens",
    "Bruce lives in San Francisco", 
    "Bruce enjoys hiking on weekends",
    "Bruce's favorite programming language is Python"
]

print("\nTesting memory addition with retry logic:")
print("=" * 50)

for memory_text in test_memories:
    result = safe_add_memory(m, memory_text, user_id="bruce")
    print("-" * 30)
    time.sleep(1)  # Small delay between operations

# Retrieve all memories
print("\nRetrieving all memories:")
try:
    all_memories = m.get_all(user_id="bruce")
    if all_memories and all_memories.get('results'):
        print(f"Found {len(all_memories['results'])} memories:")
        for i, memory in enumerate(all_memories['results'], 1):
            print(f"{i}. {memory['memory']}")
    else:
        print("No memories found")
except Exception as e:
    print(f"❌ Failed to retrieve memories: {e}")
