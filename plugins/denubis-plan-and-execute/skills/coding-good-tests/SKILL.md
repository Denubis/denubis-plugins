---
name: coding-good-tests
family: coding-effectively
description: Use when writing or reviewing tests - covers pytest patterns, mock strategy, condition-based waiting, and test isolation with focus on testing behavior not implementation
---

# Writing Good Tests

## Philosophy

**"Write tests. Not too many. Mostly integration."** — Kent C. Dodds

Tests verify real behaviour, not implementation details. The goal is confidence that code works, not coverage numbers.

**Core principles:**
1. Test behaviour, not implementation — refactoring shouldn't break tests
2. Integration tests provide better confidence-to-cost ratio than unit tests
3. Wait for actual conditions, not arbitrary timeouts
4. Mock strategically — real dependencies when feasible
5. Don't pollute production code with test-only methods

## No change-detection tests

Do not read source or prose, assert that an exact phrase is present or absent, and then
write that phrase to make the test pass. That test observes the edit itself, not whether
the system is correct. Renaming or rewriting without changing behaviour should not create
a failure.

An automated gate needs an independent observation. Exercise the public behaviour, parse
a declared structure, compare a recomputable property, or use syntax/AST analysis that
classifies the defect without sharing the implementation's chosen wording. Include a
positive control whenever success is otherwise an empty result.

If the subject is prose and its quality cannot be distinguished mechanically, do not
manufacture automation. Write a review rubric containing the expectations, scenarios,
and evidence a human or reviewing agent must inspect. The review reports exact findings;
the rubric does not become an approval certificate.

## Test Invocation

Standard pytest command:

```bash
uv run pytest --depper --depper-run-all-on-error -n auto --dist=loadfile -x --ff --durations=10 --tb=short
```

**Flags explained:**
- `--depper`: Track test dependencies
- `-n auto`: Parallel execution (xdist)
- `--dist=loadfile`: Group tests by file for parallel
- `-x`: Stop on first failure
- `--ff`: Run failed tests first
- `--durations=10`: Show 10 slowest tests
- `--tb=short`: Concise tracebacks

## Test Structure

Use **Arrange-Act-Assert**:

```python
def test_user_can_cancel_reservation():
    # Arrange
    reservation = create_reservation(user_id="user-1", room_id="room-1")

    # Act
    result = cancel_reservation(reservation.id)

    # Assert
    assert result.status == "cancelled"
    assert get_reservation(reservation.id) is None
```

**One action per test.** Multiple assertions are fine if they verify the same behaviour.

## Parametrisation

Use `pytest.mark.parametrize` for testing multiple cases:

```python
@pytest.mark.parametrize("input_value,expected", [
    ("hello", "HELLO"),
    ("World", "WORLD"),
    ("", ""),
    ("123", "123"),
])
def test_uppercase(input_value: str, expected: str):
    assert uppercase(input_value) == expected
```

## Fixtures

### Reusable Setup

```python
@pytest.fixture
def db_session():
    """Provide a database session that rolls back after test."""
    session = create_session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_user(db_session):
    """Create a sample user for tests."""
    user = User(name="Test User", email="test@example.com")
    db_session.add(user)
    db_session.flush()
    return user
```

### HTTP Mocking with pytest-httpx

```python
@pytest.fixture
def mock_api(httpx_mock):
    """Mock external API responses."""
    httpx_mock.add_response(
        url="https://api.example.com/users/1",
        json={"id": 1, "name": "Alice"},
    )
    return httpx_mock

async def test_fetch_user(mock_api):
    user = await fetch_user(1)
    assert user.name == "Alice"
```

## Condition-Based Waiting

Flaky tests often guess at timing. Wait for conditions, not time:

```python
# BAD: guessing at timing
await asyncio.sleep(0.5)
result = get_result()

# GOOD: waiting for condition
async def wait_for(condition, timeout=5.0, interval=0.01):
    """Wait for condition to be truthy."""
    start = time.monotonic()
    while True:
        result = condition()
        if result:
            return result
        if time.monotonic() - start > timeout:
            raise TimeoutError(f"Condition not met within {timeout}s")
        await asyncio.sleep(interval)

result = await wait_for(lambda: get_result() is not None)
```

### When Arbitrary Timeout IS Correct

Only when testing actual timing behaviour:

```python
# Testing debounce behaviour
await trigger_event()
await asyncio.sleep(0.2)  # 200ms = debounce window
# Comment explains WHY: testing the debounce delay itself
assert was_debounced()
```

## Mocking Strategy

### Don't Mock What You Don't Own

Create wrappers around third-party libraries. Mock YOUR wrapper:

```python
# BAD: mock the HTTP client directly
with patch('httpx.AsyncClient.get') as mock:
    ...

# GOOD: create your own wrapper
class RegistryClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def get_repos(self) -> list[Repo]:
        response = await self.client.get(...)
        return [Repo(**r) for r in response.json()]

# Mock your wrapper
@pytest.fixture
def mock_registry(mocker):
    return mocker.patch.object(RegistryClient, 'get_repos')
```

### Internal vs External Boundaries

**Never mock internal code** — build scaffolding for isolation. **Always mock external boundaries** — network, shell, filesystem, third-party APIs. Tests must be isolated.

| Boundary | Example | Strategy |
|----------|---------|----------|
| **Internal** (your code) | Your database, your modules, your files | Use REAL instances — build scaffolding if needed |
| **External** (system boundary) | Third-party APIs, SMTP, network, shell | Use MOCKS |

### Anti-Pattern: Testing Mock Behaviour

```python
# BAD: testing that the mock exists
def test_renders_sidebar():
    render(Page())
    assert mock_sidebar.called  # tests mock, not behaviour

# GOOD: test real behaviour
def test_renders_sidebar():
    result = render(Page())
    assert "sidebar" in result.html
```

**Gate:** Before asserting on any mock, ask: "Am I testing real behaviour or mock existence?"

### Anti-Pattern: Mocking Without Understanding

```python
# BAD: mock breaks test logic
def test_detects_duplicate(mocker):
    # Mock prevents file write that test depends on!
    mocker.patch('config.save')
    add_server(config)
    add_server(config)  # Should raise - but won't!

# GOOD: mock at correct level
def test_detects_duplicate(mocker):
    mocker.patch('server.start')  # Just mock slow startup
    add_server(config)  # Config saved
    with pytest.raises(DuplicateError):
        add_server(config)
```

### When Mocks Become Too Complex

Warning signs:
- Mock setup longer than test logic
- Mocking everything to make test pass
- Test breaks when mock changes

Consider integration tests with real components — often simpler than elaborate mocks.

## Test-Only Methods

**Never add methods to production code just for tests:**

```python
# BAD: test-only method in production
class Session:
    def _test_reset(self):  # only used in tests
        ...

# GOOD: test utilities separate
# tests/helpers/session.py
def reset_session(session: Session) -> None:
    """Test helper to reset session state."""
    ...
```

## Test Isolation

Tests should not depend on execution order.

### What to Clean Up

**Long-lived resources MUST be cleaned up:**
- Processes, containers
- Temporary files in non-temp locations
- Database connections

```python
@pytest.fixture
def temp_server():
    server = start_server()
    yield server
    server.stop()  # Always clean up
```

### What's OK to Leave

- Database records (use unique IDs per test)
- Log entries
- Cached data that expires

```python
# Use unique identifiers
def test_create_user():
    unique_id = f"test-{uuid4()}"
    user = create_user(email=f"{unique_id}@test.com")
    ...
```

## FCIS and Testing

FCIS makes testing simple:

```python
# Functional Core: trivial to test
def test_calculate_tax():
    result = calculate_tax(Decimal("100"), Decimal("0.1"))
    assert result == Decimal("10.00")
    # No mocks needed!

# Imperative Shell: integration test
async def test_process_order(db_session, sample_order):
    result = await process_order(sample_order.id, db_session)
    assert result.status == "completed"
```

## Red Flags

**Stop and reconsider when you see:**

- Arbitrary `sleep()` without justification
- Assertions on mock objects
- Test-only methods in production code
- Mock setup >50% of test code
- Tests that depend on execution order
- Tests that fail intermittently

## Quick Reference

| Problem | Fix |
|---------|-----|
| Arbitrary sleep | Condition-based waiting |
| Asserting on mocks | Test real behaviour |
| Mocking third-party directly | Create wrapper, mock wrapper |
| Test-only production methods | Move to test utilities |
| Complex mock setup | Consider integration test |
| Order-dependent tests | Use unique identifiers |

## Property-Based Testing

For serialisation, validation, and pure functions, see `coding-property-testing` skill.
