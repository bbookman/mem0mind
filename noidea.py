import os
import time
import logging
from mem0 import Memory

# Reduce logging noise - only show warnings and errors
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,  # Change this according to your local model's dimensions
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3.1:latest",
            "temperature": 0.1,  # Slightly higher for more creative fact extraction
            "max_tokens": 2000,
            "ollama_base_url": "http://localhost:11434",  # Ensure this URL is correct
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
    """
    Safely add memory with retry logic and error handling.

    Args:
        memory_instance: The mem0 Memory instance
        text: The text to store
        user_id: User identifier
        max_retries: Maximum number of retry attempts

    Returns:
        Result from memory.add() or None if failed
    """
    for attempt in range(max_retries):
        try:
            print(f"  Attempt {attempt + 1}: Adding '{text}'")
            result = memory_instance.add(text, user_id=user_id)

            if result and result.get('results'):
                print(f"  ✅ SUCCESS: {result['results'][0]['memory']}")
                return result
            else:
                print(f"  ⚠️  No facts extracted from: '{text}'")
                return result

        except Exception as e:
            print(f"  ❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"  Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print(f"  Failed after {max_retries} attempts")
                return None

def reset_user_memories(memory_instance, user_id):
    """
    Reset all memories for a specific user.

    Args:
        memory_instance: The mem0 Memory instance
        user_id: User identifier to reset

    Returns:
        Number of memories deleted
    """
    try:
        print(f"Resetting all memories for user '{user_id}'...")
        all_memories = memory_instance.get_all(user_id=user_id)

        if all_memories and all_memories.get('results'):
            memory_count = len(all_memories['results'])
            print(f"Found {memory_count} memories to delete")

            deleted_count = 0
            for memory in all_memories['results']:
                try:
                    memory_instance.delete(memory_id=memory['id'])
                    deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete memory: {e}")

            print(f"✅ Deleted {deleted_count}/{memory_count} memories")
            return deleted_count
        else:
            print("No memories found to delete")
            return 0

    except Exception as e:
        print(f"❌ Error during reset: {e}")
        return 0

def add_as_fact(memory_instance, text, user_id, subject_name=None):
    """
    Add text as a fact with improved formatting.

    Args:
        memory_instance: The mem0 Memory instance
        text: The text to store
        user_id: User identifier
        subject_name: Optional subject name to make it more factual

    Returns:
        Result from safe_add_memory()
    """
    # If no subject provided, try to make it more factual
    if subject_name and not text.startswith(subject_name):
        factual_text = f"{subject_name} {text}"
    else:
        factual_text = text

    # Ensure it sounds like a definitive fact
    if not any(factual_text.lower().startswith(word) for word in
               ['the', 'this', 'that', subject_name.lower() if subject_name else '']):
        if subject_name:
            factual_text = f"{subject_name} {factual_text}"

    return safe_add_memory(memory_instance, factual_text, user_id)

print("Initializing Memory...")
# Initialize Memory with the configuration
try:
    m = Memory.from_config(config)
    print("✅ Memory initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize memory: {e}")
    exit(1)

# Optional: Reset memories before adding new ones
# Uncomment the next line if you want to start fresh each time
# reset_user_memories(m, "bruce")
print("\nTesting memory addition with safe retry logic:")
print("=" * 60)

# Test memories with improved error handling
test_memories = [
    "Bruce works at Walgreens",
    "Bruce lives in Wilmington, NC",
    "Bruce works as a customer service representative",
    "Bruce's favorite food is pizza"
]

# Method 1: Using safe_add_memory directly
print("\n1. Adding memories with safe retry logic:")
for i, memory_text in enumerate(test_memories, 1):
    print(f"\n{i}. {memory_text}")
    result = safe_add_memory(m, memory_text, user_id="bruce")
    time.sleep(1)  # Small delay between operations to prevent conflicts

# Method 2: Using helper function for additional memories
print("\n2. Adding memories using helper function:")
additional_memories = [
    ("enjoys software development", "Bruce"),
    ("graduated from college in 1992", "Bruce"),
    ("drives a Honda HRV", "Bruce")
]

for text, subject in additional_memories:
    print(f"\n   {subject} {text}")
    result = add_as_fact(m, text, user_id="bruce", subject_name=subject)
    time.sleep(1)  # Small delay between operations

# Retrieve all memories with error handling
print("\n" + "=" * 60)
print("Retrieving all stored memories:")
try:
    all_memories = m.get_all(user_id="bruce")
    if all_memories and all_memories.get('results'):
        print(f"\n✅ Found {len(all_memories['results'])} memories:")
        for i, memory in enumerate(all_memories['results'], 1):
            created_at = memory.get('created_at', 'Unknown time')
            print(f"{i:2d}. {memory['memory']} (Created: {created_at})")
    else:
        print("\n⚠️  No memories found")
except Exception as e:
    print(f"\n❌ Failed to retrieve memories: {e}")

print("\n" + "=" * 60)
print("Memory operations completed!")