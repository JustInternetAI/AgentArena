# Team Onboarding Guide

Welcome to Agent Arena development! This guide will help you get started working collaboratively on the project.

## Quick Links

- 📋 [IPC Protocol Documentation](ipc_protocol.md) - Communication format between Godot and Python
- 🎯 [GitHub Issues List](github_issues.md) - Pre-written issues ready to assign
- 🤝 [Contributing Guidelines](../CONTRIBUTING.md) - Development workflow and standards
- 📊 [Project Board Setup](project_board.md) - Kanban board structure and usage

## Getting Started Checklist

### For Your Colleague (Python Focus)

- [ ] Clone the repository: `git clone https://github.com/JustInternetAI/AgentArena.git`
- [ ] Read [architecture.md](architecture.md) to understand the system
- [ ] Read [ipc_protocol.md](ipc_protocol.md) for the communication contract
- [ ] Set up Python environment (see Issue #1 in [github_issues.md](github_issues.md))
- [ ] Create feature branch: `git checkout -b feature/python-setup`
- [ ] Review assigned issues on the project board
- [ ] Join communication channels (Discord/Slack if configured)

### For You (Godot Focus)

- [ ] Continue debugging benchmark scenes
- [ ] Implement tool execution in C++ (move_to, collect, etc.)
- [ ] Add collision detection for resources/hazards
- [ ] Improve scene visuals (materials, particles)
- [ ] Test IPC client with mock Python responses

## Work Division

### Python/Agent Runtime (Your Colleague)
**Primary Ownership**:
- `python/**/*.py` - All Python code
- `configs/**/*.yaml` - Configuration files
- `tests/**/*.py` - Python unit tests
- `requirements.txt` - Dependencies

**Key Tasks**:
1. Setup Python environment (Week 1)
2. Implement BaseBackend and IPC server (Week 1)
3. Implement AgentRuntime, Memory, Tools (Week 2)
4. Add LlamaCppBackend (Week 3)
5. Create unit tests and documentation (Week 3-4)

**Start with**: Issues #1, #2, #3 from [github_issues.md](github_issues.md)

---

### Godot/Simulation (You)
**Primary Ownership**:
- `godot/**/*` - C++ GDExtension code
- `scenes/**/*.tscn` - Godot scenes
- `scripts/**/*.gd` - GDScript files
- Scene balancing and visuals

**Key Tasks**:
1. Debug and refine benchmark scenes (Week 1-2)
2. Implement tool execution in C++ (Week 1-2)
3. Add collision detection and physics (Week 2)
4. Visual improvements (Week 2-3)
5. IPC client testing and refinement (Week 3)

**Focus areas**: Foraging, Crafting Chain, Team Capture scenes

---

### Shared/Integration (Both)
**Coordinate before modifying**:
- `docs/**/*.md` - Documentation
- `README.md` - Project overview
- `.claude/project-context.md` - Project context
- Integration testing

**Collaborative work**:
- Week 4: End-to-end integration testing
- IPC protocol refinements
- Performance optimization

## Communication Plan

### Daily Updates (Async)

Post brief updates in your team channel:

**Format**:
```
📅 [Date]
✅ Yesterday: [What you completed]
🔄 Today: [What you're working on]
🚫 Blockers: [Any issues/questions]
```

**Example**:
```
📅 2025-11-11
✅ Yesterday: Implemented BaseBackend abstract class
🔄 Today: Working on FastAPI IPC server
🚫 Blockers: Need clarification on action response format
```

### Weekly Sync

**Every Monday** (30 mins):
- Review project board
- Demo progress from last week
- Discuss blockers
- Assign issues for current week
- Update milestones

**Every Friday** (15 mins):
- Quick retrospective
- Celebrate wins
- Note improvements for next week

### Pull Request Protocol

1. **Create PR early** (can be draft)
2. **Tag relevant person** for review
3. **Respond to feedback** within 24 hours
4. **Merge** once approved

**Review SLA**: 24-48 hours for PR review

## Integration Checkpoints

### Week 1 Checkpoint: Basic IPC
**Goal**: Godot and Python can communicate

**Success Criteria**:
- [ ] Python IPC server running
- [ ] Godot can send perception data
- [ ] Python returns action response
- [ ] No errors in communication

**Test**: Run [scenes/test_IPC.tscn](../scenes/test_IPC.tscn)

---

### Week 2 Checkpoint: Agent Runtime
**Goal**: Agent can process observations

**Success Criteria**:
- [ ] AgentRuntime processes observations
- [ ] Short-term memory stores recent data
- [ ] ToolDispatcher validates tool calls
- [ ] Unit tests pass (>80% coverage)

**Test**: Send mock perception, verify memory and tool parsing

---

### Week 3 Checkpoint: LLM Integration
**Goal**: Real LLM controls agent

**Success Criteria**:
- [ ] LlamaCppBackend loads model
- [ ] LLM generates valid tool calls
- [ ] Foraging scene works end-to-end
- [ ] Performance acceptable (<1s per action)

**Test**: Agent collects resources in foraging scene using LLM decisions

---

### Week 4 Checkpoint: All Scenes
**Goal**: All benchmarks functional

**Success Criteria**:
- [ ] Foraging scene complete ✓
- [ ] Crafting chain scene complete
- [ ] Team capture scene complete
- [ ] Metrics tracked correctly
- [ ] Documentation updated

**Test**: Run all three scenes with LLM agents, collect metrics

## Troubleshooting

### IPC Connection Issues

**Problem**: Python server not responding

**Check**:
1. Is server running? `python python/run_ipc_server.py`
2. Correct port? Default is 5000
3. Firewall blocking? Check Windows Firewall
4. Check server logs for errors

**Solution**: See [ipc_protocol.md - Testing & Debugging](ipc_protocol.md#6-testing--debugging)

---

### Merge Conflicts

**Problem**: Can't merge due to conflicts

**Solution**:
```bash
# Update main
git checkout main
git pull origin main

# Rebase your branch
git checkout your-branch
git rebase main

# Resolve conflicts in editor
# Then continue rebase
git add .
git rebase --continue

# Force push (with lease for safety)
git push origin your-branch --force-with-lease
```

---

### Python Import Errors

**Problem**: Module not found when running Python code

**Solution**:
```bash
# Make sure venv is activated
cd python
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt

# Add python directory to PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

---

### Godot Extension Not Loading

**Problem**: C++ extension not showing in Godot

**Solution**:
1. Rebuild extension:
   ```bash
   cd godot/build
   cmake --build . --config Debug
   ```
2. Check DLL is in `bin/windows/`
3. Verify `agent_arena.gdextension` paths are correct
4. Restart Godot editor
5. Check Godot console for error messages

## Resources

### Documentation
- [Architecture Overview](architecture.md)
- [IPC Protocol](ipc_protocol.md)
- [Quickstart Guide](quickstart.md)
- [Testing Guide](../TESTING.md)

### External Resources
- [Godot Documentation](https://docs.godotengine.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [llama-cpp-python](https://github.com/abetlen/llama-cpp-python)
- [Hydra Configuration](https://hydra.cc/)

### GitHub
- [Repository](https://github.com/JustInternetAI/AgentArena)
- [Issues](https://github.com/JustInternetAI/AgentArena/issues)
- [Pull Requests](https://github.com/JustInternetAI/AgentArena/pulls)
- [Discussions](https://github.com/JustInternetAI/AgentArena/discussions)

## First Week Action Items

### Your Colleague's Week 1

**Monday-Tuesday**:
- [ ] Read architecture.md and ipc_protocol.md
- [ ] Setup development environment
- [ ] Create Issue #1 branch
- [ ] Complete Python environment setup
- [ ] Create PR for requirements.txt

**Wednesday-Thursday**:
- [ ] Implement BaseBackend (Issue #2)
- [ ] Write unit tests
- [ ] Create PR

**Friday**:
- [ ] Implement FastAPI IPC server (Issue #3)
- [ ] Test with mock Godot client
- [ ] Demo in weekly sync

---

### Your Week 1

**Monday-Tuesday**:
- [ ] Debug foraging scene collision detection
- [ ] Fix resource collection radius
- [ ] Test hazard damage system

**Wednesday-Thursday**:
- [ ] Implement move_to tool in C++
- [ ] Add pathfinding basics
- [ ] Test tool execution

**Friday**:
- [ ] Visual improvements (colors, shapes)
- [ ] Test IPC with colleague's server
- [ ] Demo in weekly sync

## Questions?

- **Technical questions**: Open GitHub Discussion
- **Bugs**: Create GitHub Issue
- **Urgent blockers**: Direct message
- **General chat**: Team channel

## Next Steps

1. **Review all 4 documents**:
   - [ipc_protocol.md](ipc_protocol.md)
   - [github_issues.md](github_issues.md)
   - [CONTRIBUTING.md](../CONTRIBUTING.md)
   - [project_board.md](project_board.md)

2. **Set up GitHub Project Board**:
   - Create board via web interface
   - Add columns and custom fields
   - Populate with issues

3. **Create initial issues**:
   - Copy from [github_issues.md](github_issues.md)
   - Assign to appropriate person
   - Add to project board

4. **Schedule first sync**:
   - Pick a recurring time
   - Add to calendars
   - Set up call link

5. **Start developing**!
   - Create feature branches
   - Make commits
   - Push regularly
   - Open PRs

---

**Welcome aboard! Let's build something amazing together! 🚀🤖**
