import os
from mem0 import Memory

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "test_facts",
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

# Initialize Memory
m = Memory.from_config(config)

# Test different phrasings
test_memories = [
    # Good fact patterns (likely to work)
    "Bruce lives in San Francisco, California",
    "Bruce works as a software engineer at Google",
    "Bruce's favorite programming language is Python",
    "Bruce was born on January 15, 1990",
    "Bruce completed his computer science degree in 2012",
    
    # Questionable patterns (might not work)
    "I like pizza",
    "Going to the store",
    "It was fun",
    "Maybe tomorrow",
    "Thinking about it",
    
    # Improved versions of questionable patterns
    "Bruce likes pizza, especially pepperoni",
    "Bruce went to the grocery store on Monday",
    "Bruce enjoyed the concert last night",
    "Bruce plans to visit the museum tomorrow",
    "Bruce is considering learning Spanish",
]

print("Testing different memory patterns...\n")

for i, memory_text in enumerate(test_memories, 1):
    print(f"{i:2d}. Testing: '{memory_text}'")
    result = m.add(memory_text, user_id="bruce")
    
    if result['results']:
        print(f"    ✅ SUCCESS: {result['results'][0]['memory']}")
    else:
        print(f"    ❌ FAILED: No facts extracted")
    print()

# Retrieve all memories
print("=" * 50)
print("All stored memories:")
all_memories = m.get_all(user_id="bruce")
for memory in all_memories['results']:
    print(f"- {memory['memory']}")
