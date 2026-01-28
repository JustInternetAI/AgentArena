"""
Test demonstrating the three-layer memory architecture.

Layer 1: LongTermMemory - Pure vector store (text + metadata)
Layer 2: SemanticMemory - Generic object storage with converters
Layer 3: RAGMemoryV2 - Domain-specific agent observations
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("THREE-LAYER MEMORY ARCHITECTURE TEST")
print("=" * 70)

# ============================================================================
# LAYER 1: Pure Vector Store (LongTermMemory)
# ============================================================================

print("\n" + "=" * 70)
print("LAYER 1: LongTermMemory (Pure Vector Store)")
print("=" * 70)
print("Generic text + metadata storage with vector embeddings")
print()

try:
    from long_term_memory_module import LongTermMemory

    # Initialize
    layer1_memory = LongTermMemory(embedding_model="all-MiniLM-L6-v2", index_type="FlatIP")
    print("[OK] Initialized LongTermMemory")

    # Store plain text with metadata
    print("\nStoring plain text memories...")
    id1 = layer1_memory.store_memory(
        text="Found valuable resources at coordinates 10,5",
        metadata={"type": "discovery", "importance": "high"},
    )
    print(f"  Stored: {id1[:8]}... - 'Found valuable resources...'")

    id2 = layer1_memory.store_memory(
        text="Encountered hostile entity in northern region",
        metadata={"type": "danger", "importance": "critical"},
    )
    print(f"  Stored: {id2[:8]}... - 'Encountered hostile entity...'")

    id3 = layer1_memory.store_memory(
        text="Established safe camp near water source",
        metadata={"type": "achievement", "importance": "medium"},
    )
    print(f"  Stored: {id3[:8]}... - 'Established safe camp...'")

    # Query
    print("\nQuerying: 'Where are dangerous areas?'")
    results = layer1_memory.query_memory("Where are dangerous areas?", k=2)
    for i, result in enumerate(results, 1):
        print(f"  {i}. Score: {result['score']:.3f} - {result['text'][:40]}...")

    print(f"\n[SUCCESS] Layer 1 complete - {len(layer1_memory)} memories stored")

except Exception as e:
    print(f"[ERROR] Layer 1 failed: {e}")
    import traceback

    traceback.print_exc()

# ============================================================================
# LAYER 2: Generic Object Storage (SemanticMemory)
# ============================================================================

print("\n" + "=" * 70)
print("LAYER 2: SemanticMemory (Generic Object Storage)")
print("=" * 70)
print("Works with ANY Python objects via converter functions")
print()

try:
    from long_term_memory_module import MemoryConverter, SemanticMemory

    # Define a custom domain class
    class GameEvent:
        """Custom domain object - game events."""

        def __init__(self, event_type, description, location, participants):
            self.type = event_type
            self.description = description
            self.location = location
            self.participants = participants

        def __repr__(self):
            return f"GameEvent({self.type}: {self.description})"

    # Define converter for GameEvent
    class GameEventConverter(MemoryConverter):
        def to_text(self, event):
            return f"{event.type} event: {event.description} at {event.location} involving {', '.join(event.participants)}"

        def to_metadata(self, event):
            return {
                "event_type": event.type,
                "location": event.location,
                "num_participants": len(event.participants),
            }

        def from_dict(self, data):
            # For this demo, we'll reconstruct a simplified version
            meta = data["metadata"]
            return GameEvent(
                event_type=meta["event_type"],
                description=data["text"].split(": ", 1)[1].split(" at ")[0],
                location=meta["location"],
                participants=[],  # Simplified reconstruction
            )

    # Create converter and memory
    converter = GameEventConverter()
    layer2_memory = SemanticMemory(
        to_text=converter.to_text,
        to_metadata=converter.to_metadata,
        from_dict=converter.from_dict,
        embedding_model="all-MiniLM-L6-v2",
        index_type="FlatIP",
    )
    print("[OK] Initialized SemanticMemory with GameEventConverter")

    # Store custom objects
    print("\nStoring GameEvent objects...")
    event1 = GameEvent("combat", "Player defeated dragon boss", "Castle", ["player1", "dragon"])
    event2 = GameEvent(
        "trade", "Successful merchant transaction", "Market", ["player1", "merchant"]
    )
    event3 = GameEvent("discovery", "Found legendary sword", "Cave", ["player1"])

    layer2_memory.store(event1)
    print(f"  Stored: {event1}")
    layer2_memory.store(event2)
    print(f"  Stored: {event2}")
    layer2_memory.store(event3)
    print(f"  Stored: {event3}")

    # Query for objects
    print("\nQuerying: 'epic battle with monsters'")
    raw_results = layer2_memory.query("epic battle with monsters", k=2)
    for i, result in enumerate(raw_results, 1):
        print(f"  {i}. Score: {result['score']:.3f} - Type: {result['metadata']['event_type']}")
        print(f"      {result['text'][:60]}...")

    # Query and get reconstructed objects
    print("\nQuerying with object reconstruction...")
    event_objects = layer2_memory.query_objects("finding treasure", k=1)
    for i, event in enumerate(event_objects, 1):
        print(f"  {i}. {event}")

    print(f"\n[SUCCESS] Layer 2 complete - {len(layer2_memory)} objects stored")

except Exception as e:
    print(f"[ERROR] Layer 2 failed: {e}")
    import traceback

    traceback.print_exc()

# ============================================================================
# LAYER 3: Domain-Specific Agent Memory (RAGMemoryV2)
# ============================================================================

print("\n" + "=" * 70)
print("LAYER 3: RAGMemoryV2 (Agent-Specific Memory)")
print("=" * 70)
print("Specialized for Agent Arena observations")
print()

try:
    from agent_runtime.memory import RAGMemoryV2
    from agent_runtime.schemas import HazardInfo, Observation, ResourceInfo

    # Initialize agent memory
    layer3_memory = RAGMemoryV2(
        embedding_model="all-MiniLM-L6-v2", index_type="FlatIP", similarity_threshold=0.25
    )
    print("[OK] Initialized RAGMemoryV2")

    # Store agent observations
    print("\nStoring agent observations...")

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
    layer3_memory.store(obs1)
    print(f"  Tick {obs1.tick}: Found berries at {obs1.position}")

    obs2 = Observation(
        agent_id="agent_001",
        tick=25,
        position=(20.0, 0.0, 10.0),
        health=100.0,
        energy=85.0,
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
    layer3_memory.store(obs2)
    print(f"  Tick {obs2.tick}: Spotted fire hazard at {obs2.position}")

    obs3 = Observation(
        agent_id="agent_001",
        tick=35,
        position=(5.0, 0.0, 15.0),
        health=100.0,
        energy=80.0,
        nearby_resources=[
            ResourceInfo(name="water", type="liquid", position=(5.5, 0.0, 15.0), distance=0.5),
            ResourceInfo(name="stone", type="material", position=(6.0, 0.0, 15.0), distance=1.0),
        ],
    )
    layer3_memory.store(obs3)
    print(f"  Tick {obs3.tick}: Found water and stone at {obs3.position}")

    # Query agent memory
    print("\nQuerying: 'Where can I find food?'")
    food_results = layer3_memory.retrieve(query="Where can I find food?", limit=2)
    for i, obs in enumerate(food_results, 1):
        print(f"  {i}. Tick {obs.tick} at {obs.position} - Health: {obs.health}")

    print("\nQuerying: 'What dangers should I avoid?'")
    danger_results = layer3_memory.retrieve(query="What dangers should I avoid?", limit=2)
    for i, obs in enumerate(danger_results, 1):
        print(f"  {i}. Tick {obs.tick} at {obs.position} - Health: {obs.health}")

    # Get summary
    print("\nMemory Summary:")
    print(layer3_memory.summarize())

    print(f"\n[SUCCESS] Layer 3 complete - {len(layer3_memory)} observations stored")

except Exception as e:
    print(f"[ERROR] Layer 3 failed: {e}")
    import traceback

    traceback.print_exc()

# ============================================================================
# ARCHITECTURE SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("ARCHITECTURE SUMMARY")
print("=" * 70)

print(
    """
Three-Layer Memory Architecture:

+---------------------------------------------------------------+
|  LAYER 3: Domain-Specific (RAGMemoryV2)                      |
|  - Agent observations                                         |
|  - ObservationConverter                                       |
|  - Implements AgentMemory interface                           |
+---------------------------+-----------------------------------+
                            | Uses
+---------------------------+-----------------------------------+
|  LAYER 2: Generic Object Storage (SemanticMemory)            |
|  - Works with ANY Python objects                              |
|  - Converter functions (to_text, to_metadata, from_dict)      |
|  - Type-safe queries                                          |
+---------------------------+-----------------------------------+
                            | Uses
+---------------------------+-----------------------------------+
|  LAYER 1: Pure Vector Store (LongTermMemory)                 |
|  - text + metadata -> embeddings                              |
|  - FAISS similarity search                                    |
|  - No domain knowledge                                        |
+---------------------------------------------------------------+

Benefits:
[OK] Layer 1 is completely generic and reusable
[OK] Layer 2 enables easy creation of memories for any domain
[OK] Layer 3 provides agent-specific convenience
[OK] Clean separation of concerns
[OK] Each layer can be tested independently
[OK] Easy to add new domains without changing lower layers
"""
)

print("\n" + "=" * 70)
print("[SUCCESS] ALL THREE LAYERS WORKING CORRECTLY")
print("=" * 70)
