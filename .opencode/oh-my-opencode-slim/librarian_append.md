## Project-Specific Librarian Rules for ha-cycle-tracker

### Research Domains & Sources

#### 1. Home Assistant Core API
- **Primary**: https://developers.home-assistant.io/docs/
- **Custom Components**: https://developers.home-assistant.io/docs/creating_component_index
- **Config Flow**: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- **Sensors**: https://developers.home-assistant.io/docs/core/entity/sensor
- **Calendar**: https://developers.home-assistant.io/docs/core/entity/calendar
- **Services**: https://developers.home-assistant.io/docs/core/entity/service
- **DataUpdateCoordinator**: https://developers.home-assistant.io/docs/integration_fetching_data
- **Storage**: https://developers.home-assistant.io/docs/core/entity/storage
- **HACS Requirements**: https://hacs.xyz/docs/publish/include/
- **Release Notes**: https://github.com/home-assistant/core/releases (watch for breaking changes)

#### 2. Python HA Custom Component Patterns
- **Existing Components**: Search GitHub for `custom_components/` examples
- **pytest-homeassistant-custom-component**: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component
- **HA Type Stubs**: https://github.com/home-assistant/core/tree/dev/homeassistant (for mypy)

#### 3. Testing Frameworks
- **pytest**: https://docs.pytest.org/
- **pytest-homeassistant-custom-component**: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component
- **jsonschema**: https://python-jsonschema.readthedocs.io/
- **hypothesis**: https://hypothesis.readthedocs.io/ (property-based testing)

#### 4. CI/CD & Tooling
- **GitHub Actions**: https://docs.github.com/en/actions
- **pre-commit**: https://pre-commit.com/
- **ruff**: https://docs.astral.sh/ruff/
- **mypy**: https://mypy.readthedocs.io/

#### 5. Algorithms & Statistics
- **Weighted Moving Average**: Standard statistical references
- **Cycle Tracking Algorithms**: Medical literature on menstrual cycle prediction
- **Standard Deviation**: Population vs sample variance considerations

### Research Patterns

#### When User Asks "How does X work in HA?"
1. Check developers.home-assistant.io first
2. Search GitHub home-assistant/core for implementation examples
3. Check HACS validation requirements if distribution-related
4. Return: Official doc link + code pattern + version caveats

#### When User Asks "Python HA custom component pattern?"
1. Check existing HA custom components on GitHub
2. Check pytest-homeassistant-custom-component docs
3. Return: Recommended pattern + testing approach + common pitfalls

#### When User Asks "Algorithm implementation?"
1. Check statistical references (Wikipedia, NIST, academic papers)
2. Look for Python implementations in scipy/numpy for reference
3. Return: Algorithm description + Python implementation + edge cases

### Quality Filters
- **Prefer**: Official docs, GitHub release notes, high-star repos (>1k)
- **Avoid**: Blog posts >1 year old, unverified forum posts, AI-generated content
- **Version Context**: Always note HA version, Python version

### Skill Integration
- Use `find-skills` to discover new skills when research reveals gaps
- Example: "Need Playwright for HA frontend testing" → `npx skills find playwright`