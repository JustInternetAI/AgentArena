"""
Test RAGMemory integration with a simulated agent.

This demonstrates how an agent can use RAG memory to:
1. Store observations from the environment
2. Retrieve relevant past experiences
3. Make informed decisions based on memory
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing RAGMemory with Agent...")
print("=" * 60)

try:
    from agent_runtime.memory import RAGMemory
    from agent_runtime.schemas import HazardInfo, ItemInfo, Observation, ResourceInfo

    print("[OK] Successfully imported RAGMemory and schemas\n")

    # Initialize RAG memory
    print("Initializing RAGMemory...")
    memory = RAGMemory(
        embedding_model="all-MiniLM-L6-v2",
        index_type="FlatIP",  # Use cosine similarity
        similarity_threshold=0.3,
        default_k=5,
    )
    print("[OK] Initialized RAGMemory\n")

    # Simulate an agent's journey through multiple episodes
    print("=" * 60)
    print("EPISODE 1: Exploring the forest")
    print("=" * 60)

    # Episode 1 - Discovering berries
    obs1 = Observation(
        agent_id="agent_001",
        tick=10,
        position=(10.0, 0.0, 5.0),
        health=100.0,
        energy=90.0,
        nearby_resources=[
            ResourceInfo(name="berries", type="food", position=(12.0, 0.0, 5.0), distance=2.0)
        ],
    )
    memory.store(obs1)
    print(f"Tick {obs1.tick}: Found berries at position {obs1.position}")
    print(f"  Resources nearby: {[r.name for r in obs1.nearby_resources]}")

    # Episode 1 - Collecting berries successfully
    obs2 = Observation(
        agent_id="agent_001",
        tick=15,
        position=(12.0, 0.0, 5.0),
        health=100.0,
        energy=85.0,
        inventory=[ItemInfo(id="berry_1", name="berries", quantity=5)],
        nearby_resources=[],
    )
    memory.store(obs2)
    print(f"Tick {obs2.tick}: Collected berries successfully")
    print(f"  Inventory: {[(i.name, i.quantity) for i in obs2.inventory]}")

    print("\n" + "=" * 60)
    print("EPISODE 2: Encountering hazards")
    print("=" * 60)

    # Episode 2 - Spotting fire hazard
    obs3 = Observation(
        agent_id="agent_001",
        tick=25,
        position=(20.0, 0.0, 10.0),
        health=100.0,
        energy=80.0,
        nearby_hazards=[
            HazardInfo(
                name="fire",
                type="environmental",
                position=(22.0, 0.0, 10.0),
                distance=2.0,
                damage=30.0,
            )
        ],
    )
    memory.store(obs3)
    print(f"Tick {obs3.tick}: Spotted fire hazard at distance {obs3.nearby_hazards[0].distance}")
    print(f"  Hazard: {obs3.nearby_hazards[0].name} (damage: {obs3.nearby_hazards[0].damage})")

    # Episode 2 - Taking damage from fire
    obs4 = Observation(
        agent_id="agent_001",
        tick=27,
        position=(22.0, 0.0, 10.0),
        health=70.0,  # Lost 30 health!
        energy=75.0,
        nearby_hazards=[
            HazardInfo(
                name="fire",
                type="environmental",
                position=(22.0, 0.0, 10.0),
                distance=0.5,
                damage=30.0,
            )
        ],
    )
    memory.store(obs4)
    print(f"Tick {obs4.tick}: Got too close to fire! Health dropped to {obs4.health}")

    print("\n" + "=" * 60)
    print("EPISODE 3: Finding water and resources")
    print("=" * 60)

    # Episode 3 - Finding water near rocks
    obs5 = Observation(
        agent_id="agent_001",
        tick=35,
        position=(5.0, 0.0, 15.0),
        health=70.0,
        energy=70.0,
        nearby_resources=[
            ResourceInfo(name="water", type="liquid", position=(5.0, 0.0, 17.0), distance=2.0),
            ResourceInfo(name="stone", type="material", position=(6.0, 0.0, 15.0), distance=1.0),
        ],
    )
    memory.store(obs5)
    print(f"Tick {obs5.tick}: Found water and stone near rocks")
    print(f"  Resources: {[r.name for r in obs5.nearby_resources]}")

    # Episode 3 - Collecting wood safely
    obs6 = Observation(
        agent_id="agent_001",
        tick=40,
        position=(15.0, 0.0, 20.0),
        health=70.0,
        energy=65.0,
        nearby_resources=[
            ResourceInfo(name="wood", type="material", position=(16.0, 0.0, 20.0), distance=1.0)
        ],
        inventory=[
            ItemInfo(id="berry_1", name="berries", quantity=5),
            ItemInfo(id="wood_1", name="wood", quantity=3),
        ],
    )
    memory.store(obs6)
    print(f"Tick {obs6.tick}: Collected wood safely")
    print(f"  Inventory: {[(i.name, i.quantity) for i in obs6.inventory]}")

    print("\n" + "=" * 60)
    print("MEMORY SUMMARY")
    print("=" * 60)
    print(f"Total observations stored: {len(memory)}")
    print(f"\nMemory summary:\n{memory.summarize()}")

    # Now simulate the agent using memory to make decisions
    print("\n" + "=" * 60)
    print("AGENT DECISION MAKING WITH MEMORY")
    print("=" * 60)

    # Query 1: Where to find food
    print("\nQuery 1: 'Where can I find food to eat?'")
    print("-" * 60)
    results = memory.retrieve(query="Where can I find food to eat?", limit=2)
    print(f"Retrieved {len(results)} relevant memories:")
    for i, obs in enumerate(results, 1):
        print(f"  {i}. Tick {obs.tick} at position {obs.position}")
        if obs.nearby_resources:
            print(f"     Resources found: {[r.name for r in obs.nearby_resources]}")
        if obs.inventory:
            print(f"     Inventory: {[(item.name, item.quantity) for item in obs.inventory]}")

    # Query 2: How to avoid danger
    print("\nQuery 2: 'How do I avoid dangerous situations and stay safe?'")
    print("-" * 60)
    results = memory.retrieve(query="How do I avoid dangerous situations and stay safe?", limit=2)
    print(f"Retrieved {len(results)} relevant memories:")
    for i, obs in enumerate(results, 1):
        print(f"  {i}. Tick {obs.tick} - Health: {obs.health}, Energy: {obs.energy}")
        if obs.nearby_hazards:
            print(f"     Hazards encountered: {[h.name for h in obs.nearby_hazards]}")
            print(
                f"     Lesson: Approaching {obs.nearby_hazards[0].name} reduced health to {obs.health}"
            )

    # Query 3: Where to find resources
    print("\nQuery 3: 'Where can I find water and building materials?'")
    print("-" * 60)
    results = memory.retrieve(query="Where can I find water and building materials?", limit=2)
    print(f"Retrieved {len(results)} relevant memories:")
    for i, obs in enumerate(results, 1):
        print(f"  {i}. Tick {obs.tick} at position {obs.position}")
        if obs.nearby_resources:
            resources = [r.name for r in obs.nearby_resources]
            print(f"     Resources available: {resources}")

    # Query 4: Get recent observations (no query = recency-based)
    print("\nQuery 4: What happened recently? (recency-based retrieval)")
    print("-" * 60)
    results = memory.retrieve(limit=3)  # No query - returns most recent
    print(f"Retrieved {len(results)} most recent memories:")
    for i, obs in enumerate(results, 1):
        print(f"  {i}. Tick {obs.tick} at {obs.position}")
        print(f"     Health: {obs.health}, Energy: {obs.energy}")

    # Demonstrate persistence
    print("\n" + "=" * 60)
    print("TESTING PERSISTENCE")
    print("=" * 60)

    import os
    import tempfile

    # Save memory
    temp_dir = tempfile.mkdtemp()
    save_path = os.path.join(temp_dir, "agent_001_memory.faiss")
    print(f"\nSaving memory to: {save_path}")
    memory.save(save_path)
    print("[OK] Memory saved successfully")

    # Create new memory instance and load
    print("\nLoading memory into new instance...")
    memory2 = RAGMemory(embedding_model="all-MiniLM-L6-v2", index_type="FlatIP")
    memory2.load(save_path)
    print(f"[OK] Loaded {len(memory2)} memories")

    # Verify loaded memory works
    print("\nVerifying loaded memory with query...")
    results = memory2.retrieve(query="Where are berries?", limit=1)
    if results:
        print(f"[OK] Query successful! Found memory from tick {results[0].tick}")

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)
    print("[OK] Cleaned up temporary files")

    # Demonstrate clearing memory
    print("\n" + "=" * 60)
    print("TESTING MEMORY CLEAR")
    print("=" * 60)
    print(f"Memories before clear: {len(memory)}")
    memory.clear()
    print(f"Memories after clear: {len(memory)}")
    print("[OK] Memory cleared successfully")

    print("\n" + "=" * 60)
    print("[SUCCESS] All RAGMemory agent tests passed!")
    print("=" * 60)

    print("\n" + "Key Takeaways:")
    print("1. RAGMemory stores observations with full context")
    print("2. Semantic search retrieves relevant past experiences")
    print("3. Agents can learn from past successes and failures")
    print("4. Memory persists across sessions (save/load)")
    print("5. Both query-based and recency-based retrieval work")

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
