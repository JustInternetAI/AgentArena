#ifndef AGENT_ARENA_H
#define AGENT_ARENA_H

#include <godot_cpp/classes/node.hpp>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/classes/time.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/utility_functions.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/variant.hpp>

namespace agent_arena {

// Forward declarations
class SimulationManager;
class Agent;
class EventBus;
class ToolRegistry;

/**
 * Core simulation manager that drives the deterministic tick loop
 */
class SimulationManager : public godot::Node {
    GDCLASS(SimulationManager, godot::Node)

private:
    uint64_t current_tick;
    double tick_rate;
    bool is_running;
    godot::Ref<EventBus> event_bus;

protected:
    static void _bind_methods();

public:
    SimulationManager();
    ~SimulationManager();

    void _process(double delta) override;
    void _physics_process(double delta) override;

    // Simulation control
    void start_simulation();
    void stop_simulation();
    void step_simulation();
    void reset_simulation();

    // Getters
    uint64_t get_current_tick() const { return current_tick; }
    double get_tick_rate() const { return tick_rate; }
    bool get_is_running() const { return is_running; }

    // Setters
    void set_tick_rate(double rate);
    void set_seed(uint64_t seed);
};

/**
 * Event bus for deterministic event ordering and replay
 */
class EventBus : public godot::RefCounted {
    GDCLASS(EventBus, godot::RefCounted)

private:
    struct Event {
        uint64_t tick;
        godot::String event_type;
        godot::Dictionary data;
    };

    godot::Array event_queue;
    bool recording;

protected:
    static void _bind_methods();

public:
    EventBus();
    ~EventBus();

    void emit_event(const godot::String& event_type, const godot::Dictionary& data);
    godot::Array get_events_for_tick(uint64_t tick);
    void clear_events();

    void start_recording();
    void stop_recording();
    godot::Array export_recording();
    void load_recording(const godot::Array& events);
};

/**
 * Base agent class with perception, memory, and action capabilities
 */
class Agent : public godot::Node {
    GDCLASS(Agent, godot::Node)

private:
    godot::String agent_id;
    godot::Dictionary short_term_memory;
    godot::Array action_history;
    bool is_active;

protected:
    static void _bind_methods();

public:
    Agent();
    ~Agent();

    void _ready() override;
    void _process(double delta) override;

    // Agent lifecycle
    void perceive(const godot::Dictionary& observations);
    godot::Dictionary decide_action();
    void execute_action(const godot::Dictionary& action);

    // Memory operations
    void store_memory(const godot::String& key, const godot::Variant& value);
    godot::Variant retrieve_memory(const godot::String& key);
    void clear_short_term_memory();

    // Tool interface
    godot::Dictionary call_tool(const godot::String& tool_name, const godot::Dictionary& params);

    // Getters/Setters
    godot::String get_agent_id() const { return agent_id; }
    void set_agent_id(const godot::String& id) { agent_id = id; }
};

/**
 * Tool registry for managing available agent actions
 */
class ToolRegistry : public godot::RefCounted {
    GDCLASS(ToolRegistry, godot::RefCounted)

private:
    godot::Dictionary registered_tools;

protected:
    static void _bind_methods();

public:
    ToolRegistry();
    ~ToolRegistry();

    void register_tool(const godot::String& name, const godot::Dictionary& schema);
    void unregister_tool(const godot::String& name);
    godot::Dictionary get_tool_schema(const godot::String& name);
    godot::Array get_all_tool_names();
    godot::Dictionary execute_tool(const godot::String& name, const godot::Dictionary& params);
};

} // namespace agent_arena

#endif // AGENT_ARENA_H
