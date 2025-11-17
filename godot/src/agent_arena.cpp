#include "agent_arena.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;
using namespace agent_arena;

// ============================================================================
// SimulationManager Implementation
// ============================================================================

SimulationManager::SimulationManager()
    : current_tick(0), tick_rate(60.0), is_running(false), event_bus(nullptr) {
}

SimulationManager::~SimulationManager() {}

void SimulationManager::_bind_methods() {
    ClassDB::bind_method(D_METHOD("start_simulation"), &SimulationManager::start_simulation);
    ClassDB::bind_method(D_METHOD("stop_simulation"), &SimulationManager::stop_simulation);
    ClassDB::bind_method(D_METHOD("step_simulation"), &SimulationManager::step_simulation);
    ClassDB::bind_method(D_METHOD("reset_simulation"), &SimulationManager::reset_simulation);

    ClassDB::bind_method(D_METHOD("get_current_tick"), &SimulationManager::get_current_tick);
    ClassDB::bind_method(D_METHOD("get_tick_rate"), &SimulationManager::get_tick_rate);
    ClassDB::bind_method(D_METHOD("get_is_running"), &SimulationManager::get_is_running);

    ClassDB::bind_method(D_METHOD("set_tick_rate", "rate"), &SimulationManager::set_tick_rate);
    ClassDB::bind_method(D_METHOD("set_seed", "seed"), &SimulationManager::set_seed);

    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "tick_rate"), "set_tick_rate", "get_tick_rate");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "current_tick"), "", "get_current_tick");
    ADD_PROPERTY(PropertyInfo(Variant::BOOL, "is_running"), "", "get_is_running");

    ADD_SIGNAL(MethodInfo("tick_advanced", PropertyInfo(Variant::INT, "tick")));
    ADD_SIGNAL(MethodInfo("simulation_started"));
    ADD_SIGNAL(MethodInfo("simulation_stopped"));
}

void SimulationManager::_ready() {
    // Get EventBus from the scene tree (sibling node)
    Node* parent = get_parent();
    if (parent) {
        event_bus = Object::cast_to<EventBus>(parent->get_node_or_null("EventBus"));
        if (event_bus) {
            UtilityFunctions::print("SimulationManager: EventBus connected");
        }
        // Note: EventBus is optional - scenes without it will simply not record events
    }
}

void SimulationManager::_process(double delta) {
    if (!is_running) return;

    // Process simulation tick
    // In a real implementation, this would handle timing and call step_simulation
}

void SimulationManager::_physics_process(double delta) {
    // Physics-based simulation tick (for deterministic physics)
}

void SimulationManager::start_simulation() {
    is_running = true;
    if (event_bus) {
        event_bus->start_recording();
    }
    emit_signal("simulation_started");
    UtilityFunctions::print("Simulation started at tick ", current_tick);
}

void SimulationManager::stop_simulation() {
    is_running = false;
    if (event_bus) {
        event_bus->stop_recording();
    }
    emit_signal("simulation_stopped");
    UtilityFunctions::print("Simulation stopped at tick ", current_tick);
}

void SimulationManager::step_simulation() {
    current_tick++;
    emit_signal("tick_advanced", current_tick);

    // Process all pending events for this tick
    if (event_bus) {
        Array events = event_bus->get_events_for_tick(current_tick);
        for (int i = 0; i < events.size(); i++) {
            // Process each event
        }
    }
}

void SimulationManager::reset_simulation() {
    current_tick = 0;
    is_running = false;
    if (event_bus) {
        event_bus->clear_events();
    }
    UtilityFunctions::print("Simulation reset");
}

void SimulationManager::set_tick_rate(double rate) {
    tick_rate = Math::max(1.0, rate);
}

void SimulationManager::set_seed(uint64_t seed) {
    // Set RNG seed for deterministic simulation
    UtilityFunctions::print("Simulation seed set to ", seed);
}

// ============================================================================
// EventBus Implementation
// ============================================================================

EventBus::EventBus() : recording(false) {}

EventBus::~EventBus() {}

void EventBus::_bind_methods() {
    ClassDB::bind_method(D_METHOD("emit_event", "event_type", "data"), &EventBus::emit_event);
    ClassDB::bind_method(D_METHOD("get_events_for_tick", "tick"), &EventBus::get_events_for_tick);
    ClassDB::bind_method(D_METHOD("clear_events"), &EventBus::clear_events);
    ClassDB::bind_method(D_METHOD("start_recording"), &EventBus::start_recording);
    ClassDB::bind_method(D_METHOD("stop_recording"), &EventBus::stop_recording);
    ClassDB::bind_method(D_METHOD("export_recording"), &EventBus::export_recording);
    ClassDB::bind_method(D_METHOD("load_recording", "events"), &EventBus::load_recording);
}

void EventBus::emit_event(const String& event_type, const Dictionary& data) {
    Dictionary event;
    event["type"] = event_type;
    event["data"] = data;
    event["timestamp"] = Time::get_singleton()->get_ticks_msec();

    if (recording) {
        event_queue.append(event);
    }
}

Array EventBus::get_events_for_tick(uint64_t tick) {
    Array tick_events;
    // Filter events for the specified tick
    return tick_events;
}

void EventBus::clear_events() {
    event_queue.clear();
}

void EventBus::start_recording() {
    recording = true;
    UtilityFunctions::print("Event recording started");
}

void EventBus::stop_recording() {
    recording = false;
    UtilityFunctions::print("Event recording stopped");
}

Array EventBus::export_recording() {
    return event_queue.duplicate();
}

void EventBus::load_recording(const Array& events) {
    event_queue = events.duplicate();
    UtilityFunctions::print("Loaded ", events.size(), " events");
}

// ============================================================================
// Agent Implementation
// ============================================================================

Agent::Agent() : is_active(true), tool_registry(nullptr) {
    agent_id = "agent_" + String::num_int64(Time::get_singleton()->get_ticks_msec());
}

Agent::~Agent() {}

void Agent::_bind_methods() {
    ClassDB::bind_method(D_METHOD("perceive", "observations"), &Agent::perceive);
    ClassDB::bind_method(D_METHOD("decide_action"), &Agent::decide_action);
    ClassDB::bind_method(D_METHOD("execute_action", "action"), &Agent::execute_action);

    ClassDB::bind_method(D_METHOD("store_memory", "key", "value"), &Agent::store_memory);
    ClassDB::bind_method(D_METHOD("retrieve_memory", "key"), &Agent::retrieve_memory);
    ClassDB::bind_method(D_METHOD("clear_short_term_memory"), &Agent::clear_short_term_memory);

    ClassDB::bind_method(D_METHOD("call_tool", "tool_name", "params"), &Agent::call_tool);
    ClassDB::bind_method(D_METHOD("set_tool_registry", "registry"), &Agent::set_tool_registry);
    ClassDB::bind_method(D_METHOD("get_tool_registry"), &Agent::get_tool_registry);

    ClassDB::bind_method(D_METHOD("get_agent_id"), &Agent::get_agent_id);
    ClassDB::bind_method(D_METHOD("set_agent_id", "id"), &Agent::set_agent_id);

    ADD_PROPERTY(PropertyInfo(Variant::STRING, "agent_id"), "set_agent_id", "get_agent_id");

    ADD_SIGNAL(MethodInfo("action_decided", PropertyInfo(Variant::DICTIONARY, "action")));
    ADD_SIGNAL(MethodInfo("perception_received", PropertyInfo(Variant::DICTIONARY, "observations")));
}

void Agent::_ready() {
    // Try to find ToolRegistry in the scene tree
    Node* parent = get_parent();
    if (parent) {
        tool_registry = Object::cast_to<ToolRegistry>(parent->get_node_or_null("ToolRegistry"));
        if (tool_registry) {
            UtilityFunctions::print("Agent ", agent_id, " connected to ToolRegistry");
        }
    }
    UtilityFunctions::print("Agent ", agent_id, " ready");
}

void Agent::_process(double delta) {
    if (!is_active) return;

    // Agent processing loop (perception -> decision -> action)
}

void Agent::perceive(const Dictionary& observations) {
    emit_signal("perception_received", observations);
    store_memory("last_observation", observations);
}

Dictionary Agent::decide_action() {
    Dictionary action;
    action["type"] = "idle";
    action["params"] = Dictionary();

    emit_signal("action_decided", action);
    return action;
}

void Agent::execute_action(const Dictionary& action) {
    action_history.append(action);
    UtilityFunctions::print("Agent ", agent_id, " executing action: ", action["type"]);
}

void Agent::store_memory(const String& key, const Variant& value) {
    short_term_memory[key] = value;
}

Variant Agent::retrieve_memory(const String& key) {
    if (short_term_memory.has(key)) {
        return short_term_memory[key];
    }
    return Variant();
}

void Agent::clear_short_term_memory() {
    short_term_memory.clear();
}

Dictionary Agent::call_tool(const String& tool_name, const Dictionary& params) {
    Dictionary result;

    if (tool_registry) {
        result = tool_registry->execute_tool(tool_name, params);
        UtilityFunctions::print("Agent ", agent_id, " called tool '", tool_name, "'");
    } else {
        result["success"] = false;
        result["error"] = "No ToolRegistry available";
        UtilityFunctions::print("Agent ", agent_id, " error: No ToolRegistry for tool '", tool_name, "'");
    }

    return result;
}

void Agent::set_tool_registry(ToolRegistry* registry) {
    tool_registry = registry;
    if (registry) {
        UtilityFunctions::print("Agent ", agent_id, ": ToolRegistry set");
    }
}

// ============================================================================
// ToolRegistry Implementation
// ============================================================================

ToolRegistry::ToolRegistry() : ipc_client(nullptr) {}

ToolRegistry::~ToolRegistry() {}

void ToolRegistry::_bind_methods() {
    ClassDB::bind_method(D_METHOD("register_tool", "name", "schema"), &ToolRegistry::register_tool);
    ClassDB::bind_method(D_METHOD("unregister_tool", "name"), &ToolRegistry::unregister_tool);
    ClassDB::bind_method(D_METHOD("get_tool_schema", "name"), &ToolRegistry::get_tool_schema);
    ClassDB::bind_method(D_METHOD("get_all_tool_names"), &ToolRegistry::get_all_tool_names);
    ClassDB::bind_method(D_METHOD("execute_tool", "name", "params"), &ToolRegistry::execute_tool);
    ClassDB::bind_method(D_METHOD("set_ipc_client", "client"), &ToolRegistry::set_ipc_client);
    ClassDB::bind_method(D_METHOD("get_ipc_client"), &ToolRegistry::get_ipc_client);
}

void ToolRegistry::_ready() {
    // Try to find IPCClient in the scene tree
    Node* parent = get_parent();
    if (parent) {
        ipc_client = Object::cast_to<IPCClient>(parent->get_node_or_null("IPCClient"));
        if (ipc_client) {
            UtilityFunctions::print("ToolRegistry: IPCClient connected");
        } else {
            UtilityFunctions::print("ToolRegistry: Warning - No IPCClient found. Tools will not execute.");
        }
    }
}

void ToolRegistry::register_tool(const String& name, const Dictionary& schema) {
    registered_tools[name] = schema;
    UtilityFunctions::print("Registered tool: ", name);
}

void ToolRegistry::unregister_tool(const String& name) {
    if (registered_tools.has(name)) {
        registered_tools.erase(name);
        UtilityFunctions::print("Unregistered tool: ", name);
    }
}

Dictionary ToolRegistry::get_tool_schema(const String& name) {
    if (registered_tools.has(name)) {
        return registered_tools[name];
    }
    return Dictionary();
}

Array ToolRegistry::get_all_tool_names() {
    return registered_tools.keys();
}

Dictionary ToolRegistry::execute_tool(const String& name, const Dictionary& params) {
    Dictionary result;

    if (!registered_tools.has(name)) {
        result["success"] = false;
        result["error"] = "Tool not found: " + name;
        return result;
    }

    // Execute tool via IPC if available
    if (ipc_client) {
        result = ipc_client->execute_tool_sync(name, params);
        UtilityFunctions::print("Executed tool '", name, "' via IPC");
    } else {
        result["success"] = false;
        result["error"] = "No IPC client available for tool execution";
        UtilityFunctions::print("Error: Cannot execute tool '", name, "' - no IPC client");
    }

    return result;
}

void ToolRegistry::set_ipc_client(IPCClient* client) {
    ipc_client = client;
    if (client) {
        UtilityFunctions::print("ToolRegistry: IPC client set");
    }
}

// ============================================================================
// IPCClient Implementation
// ============================================================================

IPCClient::IPCClient()
    : server_url("http://127.0.0.1:5000"),
      http_request(nullptr),
      is_connected(false),
      current_tick(0),
      response_received(false) {
}

IPCClient::~IPCClient() {
    if (http_request != nullptr) {
        http_request->queue_free();
    }
}

void IPCClient::_bind_methods() {
    ClassDB::bind_method(D_METHOD("connect_to_server", "url"), &IPCClient::connect_to_server);
    ClassDB::bind_method(D_METHOD("disconnect_from_server"), &IPCClient::disconnect_from_server);
    ClassDB::bind_method(D_METHOD("is_server_connected"), &IPCClient::is_server_connected);

    ClassDB::bind_method(D_METHOD("send_tick_request", "tick", "perceptions"), &IPCClient::send_tick_request);
    ClassDB::bind_method(D_METHOD("get_tick_response"), &IPCClient::get_tick_response);
    ClassDB::bind_method(D_METHOD("has_response"), &IPCClient::has_response);

    ClassDB::bind_method(D_METHOD("execute_tool_sync", "tool_name", "params", "agent_id", "tick"),
                         &IPCClient::execute_tool_sync);

    ClassDB::bind_method(D_METHOD("get_server_url"), &IPCClient::get_server_url);
    ClassDB::bind_method(D_METHOD("set_server_url", "url"), &IPCClient::set_server_url);

    ClassDB::bind_method(D_METHOD("_on_request_completed", "result", "response_code", "headers", "body"),
                         &IPCClient::_on_request_completed);

    ADD_PROPERTY(PropertyInfo(Variant::STRING, "server_url"), "set_server_url", "get_server_url");

    ADD_SIGNAL(MethodInfo("response_received", PropertyInfo(Variant::DICTIONARY, "response")));
    ADD_SIGNAL(MethodInfo("connection_failed", PropertyInfo(Variant::STRING, "error")));
}

void IPCClient::_ready() {
    // Create HTTPRequest node
    http_request = memnew(HTTPRequest);
    add_child(http_request);

    // Connect signal
    http_request->connect("request_completed",
                         Callable(this, "_on_request_completed"));

    UtilityFunctions::print("IPCClient initialized with server URL: ", server_url);
}

void IPCClient::_process(double delta) {
    // Process method for any per-frame updates
}

void IPCClient::connect_to_server(const String& url) {
    server_url = url;

    // Test connection with health check
    String health_url = server_url + "/health";
    Error err = http_request->request(health_url);

    if (err != OK) {
        UtilityFunctions::print("Failed to connect to server: ", server_url);
        emit_signal("connection_failed", "HTTP request failed");
        is_connected = false;
    } else {
        UtilityFunctions::print("Connecting to IPC server: ", server_url);
    }
}

void IPCClient::disconnect_from_server() {
    is_connected = false;
    http_request->cancel_request();
    UtilityFunctions::print("Disconnected from IPC server");
}

void IPCClient::set_server_url(const String& url) {
    server_url = url;
}

void IPCClient::send_tick_request(uint64_t tick, const Array& perceptions) {
    if (!is_connected) {
        UtilityFunctions::print("Warning: Sending request while not connected");
    }

    current_tick = tick;
    response_received = false;

    // Build request JSON
    Dictionary request_dict;
    request_dict["tick"] = tick;
    request_dict["perceptions"] = perceptions;
    request_dict["simulation_state"] = Dictionary();

    String json = JSON::stringify(request_dict);

    // Send POST request
    String url = server_url + "/tick";
    PackedStringArray headers;
    headers.append("Content-Type: application/json");

    Error err = http_request->request(url, headers, HTTPClient::METHOD_POST, json);

    if (err != OK) {
        UtilityFunctions::print("Error sending tick request: ", err);
    }
}

Dictionary IPCClient::get_tick_response() {
    if (response_received) {
        response_received = false;
        return pending_response;
    }
    return Dictionary();
}

void IPCClient::_on_request_completed(int result, int response_code,
                                      const PackedStringArray& headers,
                                      const PackedByteArray& body) {
    if (result != HTTPRequest::RESULT_SUCCESS) {
        UtilityFunctions::print("HTTP Request failed with result: ", result);
        emit_signal("connection_failed", "Request failed");
        is_connected = false;
        return;
    }

    if (response_code == 200) {
        // Parse JSON response
        String body_string = body.get_string_from_utf8();

        // Parse JSON
        JSON json;
        Error err = json.parse(body_string);

        if (err == OK) {
            Variant data = json.get_data();
            if (data.get_type() == Variant::DICTIONARY) {
                pending_response = data;
                response_received = true;
                is_connected = true;

                emit_signal("response_received", pending_response);

                UtilityFunctions::print("Received tick response for tick ", current_tick);
            } else {
                UtilityFunctions::print("Invalid JSON response format");
            }
        } else {
            UtilityFunctions::print("Failed to parse JSON response");
        }
    } else {
        UtilityFunctions::print("HTTP request returned error code: ", response_code);
        is_connected = false;
    }
}

Dictionary IPCClient::execute_tool_sync(const String& tool_name, const Dictionary& params,
                                        const String& agent_id, uint64_t tick) {
    Dictionary result;

    if (!is_connected) {
        UtilityFunctions::print("Warning: Tool execution while not connected to server");
    }

    // Build request JSON
    Dictionary request_dict;
    request_dict["tool_name"] = tool_name;
    request_dict["params"] = params;
    request_dict["agent_id"] = agent_id;
    request_dict["tick"] = tick;

    String json_str = JSON::stringify(request_dict);

    // Send POST request using main http_request
    String url = server_url + "/tools/execute";
    PackedStringArray headers;
    headers.append("Content-Type: application/json");

    Error err = http_request->request(url, headers, HTTPClient::METHOD_POST, json_str);

    if (err != OK) {
        UtilityFunctions::print("Error sending tool execution request: ", err);
        result["success"] = false;
        result["error"] = "Failed to send HTTP request";
        return result;
    }

    // NOTE: This is a simplified implementation that returns immediately
    // In a real scenario, you'd want to wait for the response or use callbacks
    // For now, we'll use the pending_response mechanism
    UtilityFunctions::print("Tool execution request sent for '", tool_name, "'");

    // Return a pending status - the actual response will come through the signal
    result["success"] = true;
    result["result"] = Dictionary();
    result["note"] = "Tool execution initiated - check response signal";

    return result;
}
