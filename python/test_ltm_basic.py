"""
Basic test script for LongTermMemory to verify installation.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing LongTermMemory...")

try:
    from long_term_memory_module.long_term_memory import LongTermMemory

    print("[OK] Successfully imported LongTermMemory")

    # Test basic initialization
    print("\nInitializing memory...")
    memory = LongTermMemory()
    print(f"[OK] Initialized: {memory}")

    # Test storing memory
    print("\nStoring memories...")
    mem_id1 = memory.store_memory("I found berries near the forest.")
    print(f"[OK] Stored memory 1: {mem_id1}")

    mem_id2 = memory.store_memory("Discovered water source near rocks.")
    print(f"[OK] Stored memory 2: {mem_id2}")

    mem_id3 = memory.store_memory("Avoided fire hazard while collecting wood.")
    print(f"[OK] Stored memory 3: {mem_id3}")

    print(f"\nTotal memories: {len(memory)}")

    # Test querying
    print("\nQuerying memories...")
    results = memory.query_memory("Where can I find berries?", k=2)
    print(f"[OK] Query returned {len(results)} results")

    for i, result in enumerate(results, 1):
        print(f"  {i}. Score: {result['score']:.3f} - {result['text'][:50]}...")

    # Test recall by ID
    print("\nRecalling by ID...")
    recalled = memory.recall_by_id(mem_id1)
    if recalled:
        print(f"[OK] Recalled: {recalled['text'][:50]}...")

    # Test get all memories
    print("\nGetting all memories...")
    all_memories = memory.get_all_memories()
    print(f"[OK] Retrieved {len(all_memories)} memories")

    print("\n[SUCCESS] All basic tests passed!")

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
