# Contributing to Agent Arena

Thank you for your interest in contributing to Agent Arena! This project bridges gamedev and AI research, making it accessible to both communities.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (OS, Godot version, Python version)
   - Relevant logs

### Suggesting Features

1. Check existing feature requests
2. Clearly describe the use case
3. Explain how it fits the project goals
4. Consider implementation complexity

### Contributing Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Write/update tests
5. Update documentation
6. Submit a pull request

## Development Setup

See [docs/quickstart.md](docs/quickstart.md) for initial setup.

### Work Division Strategy

To minimize merge conflicts and maximize parallel development:

**C++/Godot Development**:
- `godot/**/*` - C++ GDExtension code
- `scenes/**/*.tscn` - Godot scenes
- `scripts/**/*.gd` - GDScript files
- Scene balancing and visual improvements

**Python Development**:
- `python/**/*.py` - Agent runtime, backends, tools
- `configs/**/*.yaml` - Configuration files
- `tests/**/*.py` - Python unit tests
- LLM integration and memory systems

**Shared** (coordinate before modifying):
- `README.md`, `docs/**/*.md`
- `.claude/project-context.md`
- `CONTRIBUTING.md` (this file)

### Development Workflow

1. **C++ Module Changes:**
   ```bash
   cd godot/build
   cmake --build . --config Debug
   # Test in Godot Editor
   ```

2. **Python Changes:**
   ```bash
   cd python
   # Make changes
   pytest tests/  # Run tests
   black .        # Format code
   ruff .         # Lint
   ```

3. **Documentation:**
   - Update relevant `.md` files
   - Keep examples working
   - Add diagrams if helpful

### Branch Strategy

Use feature branches with descriptive names:

```bash
# Create feature branch
git checkout -b feature/llama-cpp-backend

# Make changes and commit
git commit -m "feat(backend): implement llama.cpp integration"

# Push and create PR
git push origin feature/llama-cpp-backend
gh pr create --title "Add llama.cpp backend" --body "..."
```

**Branch naming**:
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test additions

### Daily Sync Pattern

**Morning** (async update):
- Post what you're working on today
- Mention any blockers

**Evening**:
- Push changes to your branch
- Tag teammates on PRs needing review
- Update issue status

**Weekly**:
- Integration checkpoint
- Demo progress
- Plan next week's work

## Code Standards

### Python

- **Style**: PEP 8, enforced by Black and Ruff
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Google-style docstrings
- **Testing**: pytest with >80% coverage

Example:
```python
def process_observation(
    observation: Dict[str, Any],
    agent_id: str,
) -> ProcessedObservation:
    """
    Process raw observation into structured format.

    Args:
        observation: Raw observation dictionary
        agent_id: ID of observing agent

    Returns:
        ProcessedObservation with normalized data

    Raises:
        ValueError: If observation format is invalid
    """
    # Implementation
    pass
```

### C++

- **Style**: Google C++ Style Guide
- **Standards**: C++17
- **Naming**: PascalCase for classes, snake_case for functions
- **Comments**: Doxygen-style

Example:
```cpp
/**
 * Process a simulation tick for the agent.
 *
 * @param delta Time since last tick in seconds
 * @return true if processing succeeded
 */
bool Agent::process_tick(double delta) {
    // Implementation
    return true;
}
```

## Project Structure

```
agent-arena/
├── godot/           # C++ GDExtension module
│   ├── src/        # Implementation files
│   ├── include/    # Header files
│   └── bindings/   # Godot bindings
├── python/          # Python runtime
│   ├── agent_runtime/  # Core agent logic
│   ├── backends/       # LLM backends
│   ├── memory/         # Memory systems
│   ├── tools/          # Agent tools
│   └── evals/          # Evaluation harness
├── scenes/          # Godot benchmark scenes
├── configs/         # Hydra configs
├── tests/           # Test suites
└── docs/            # Documentation
```

## Testing

### Python Tests

```bash
cd python
pytest tests/                    # Run all tests
pytest tests/test_agent.py       # Run specific test
pytest --cov=agent_runtime       # With coverage
pytest -v -s                     # Verbose with output
```

### C++ Tests

Coming soon - GDExtension unit testing framework.

### Integration Tests

```bash
# Run full simulation test
python python/evals/run_eval.py --scene foraging --trials 1
```

## Pull Request Process

1. **Before Submitting:**
   - Run all tests
   - Format code (Black for Python)
   - Update documentation
   - Rebase on main branch

2. **PR Description:**
   - Clear title summarizing change
   - Detailed description of what and why
   - Link related issues
   - Include screenshots/logs if relevant

3. **Review Process:**
   - Maintainers will review within 1 week
   - Address feedback promptly
   - Keep PR focused (avoid scope creep)

4. **After Merge:**
   - Delete your branch
   - Update your fork
   - Celebrate! 🎉

## Areas Needing Help

### High Priority

- [ ] Additional LLM backends (vLLM, TensorRT-LLM)
- [ ] Vector store integration (Milvus, ChromaDB)
- [ ] Benchmark scene implementations
- [ ] Evaluation metrics and harness
- [ ] Documentation and tutorials

### Medium Priority

- [ ] Additional tools (crafting, combat, etc.)
- [ ] Memory system improvements
- [ ] Multi-agent coordination examples
- [ ] Performance profiling and optimization
- [ ] CI/CD pipeline

### Low Priority

- [ ] Multi-modal support (vision encoders)
- [ ] RL fine-tuning infrastructure
- [ ] Curriculum learning system
- [ ] Distributed simulation

## Communication

- **GitHub Issues**: Bug reports, feature requests, task tracking
- **GitHub Discussions**: Questions, ideas, architecture decisions
- **Pull Requests**: Code contributions and reviews
- **Discord/Slack** (if configured): Quick questions, daily standups

### IPC Protocol Changes

If you need to modify the Godot ↔ Python communication protocol:

1. Update [docs/ipc_protocol.md](docs/ipc_protocol.md)
2. Implement changes on both sides (Godot C++ and Python)
3. Add integration tests
4. Notify team (breaking change)
5. Version the protocol if needed

See [IPC Protocol Documentation](docs/ipc_protocol.md) for message format details.

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on what's best for the community
- Show empathy

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

### Enforcement

Violations may result in temporary or permanent ban. Report issues to the maintainers.

## Recognition

Contributors are recognized in:
- README.md contributors section
- Release notes
- Documentation credits

Significant contributions may earn you:
- Collaborator status
- Project decision-making input
- Eternal gratitude 🙏

## Questions?

Feel free to:
- Open a GitHub Discussion
- Comment on related issues
- Reach out to maintainers

Thank you for making Agent Arena better!
