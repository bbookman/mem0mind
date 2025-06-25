import os
import logging
from mem0 import Memory

# Reduce logging noise
logging.basicConfig(level=logging.WARNING)

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

def reset_all_memories(user_id="bruce"):
    """Reset all memories for a specific user."""
    try:
        print("Initializing Memory...")
        m = Memory.from_config(config)
        print("✅ Memory initialized")
        
        # Get all current memories
        print(f"\nChecking current memories for user '{user_id}'...")
        all_memories = m.get_all(user_id=user_id)
        
        if all_memories and all_memories.get('results'):
            memory_count = len(all_memories['results'])
            print(f"Found {memory_count} memories to delete:")
            
            # Show what will be deleted
            for i, memory in enumerate(all_memories['results'], 1):
                print(f"  {i}. {memory['memory']}")
            
            # Delete each memory individually
            print(f"\nDeleting memories...")
            deleted_count = 0
            for memory in all_memories['results']:
                try:
                    memory_id = memory['id']
                    m.delete(memory_id=memory_id)
                    deleted_count += 1
                    print(f"  ✅ Deleted: {memory['memory']}")
                except Exception as e:
                    print(f"  ❌ Failed to delete {memory['memory']}: {e}")
            
            print(f"\n✅ Successfully deleted {deleted_count}/{memory_count} memories")
            
        else:
            print("No memories found to delete")
        
        # Verify deletion
        print(f"\nVerifying deletion...")
        remaining_memories = m.get_all(user_id=user_id)
        if remaining_memories and remaining_memories.get('results'):
            print(f"⚠️  {len(remaining_memories['results'])} memories still remain")
        else:
            print("✅ All memories successfully cleared!")
            
    except Exception as e:
        print(f"❌ Error during reset: {e}")

def reset_collection():
    """Reset the entire Qdrant collection."""
    import requests
    
    print("Resetting entire Qdrant collection...")
    try:
        # Delete the collection
        response = requests.delete("http://localhost:6333/collections/test")
        if response.status_code == 200:
            print("✅ Collection 'test' deleted successfully")
        else:
            print(f"⚠️  Collection deletion response: {response.status_code}")
        
        # Verify deletion
        response = requests.get("http://localhost:6333/collections")
        if response.status_code == 200:
            collections = response.json().get('result', {}).get('collections', [])
            collection_names = [c['name'] for c in collections]
            if 'test' not in collection_names:
                print("✅ Collection 'test' successfully removed")
            else:
                print("⚠️  Collection 'test' still exists")
        
    except Exception as e:
        print(f"❌ Error resetting collection: {e}")

if __name__ == "__main__":
    print("Memory Reset Options:")
    print("1. Delete memories for specific user (recommended)")
    print("2. Delete entire collection (nuclear option)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        user_id = input("Enter user_id to reset (default: bruce): ").strip() or "bruce"
        reset_all_memories(user_id)
    elif choice == "2":
        confirm = input("Are you sure you want to delete the entire collection? (yes/no): ").strip().lower()
        if confirm == "yes":
            reset_collection()
        else:
            print("Collection reset cancelled")
    else:
        print("Invalid choice. Exiting.")
