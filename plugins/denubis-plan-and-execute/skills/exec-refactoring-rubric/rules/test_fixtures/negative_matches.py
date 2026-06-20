"""Test fixtures: code that should NOT trigger ast-grep smell rules."""
# ruff: noqa: F821 — ast-grep pattern fixtures: names like `process` are
# intentionally undefined; these files are matched structurally, never executed.


# === nesting-depth: <=3 levels is fine ===
def shallow_nesting(data):
    for item in data:
        if item.is_valid:
            for sub in item.children:
                process(sub)  # Only 3 levels — should NOT trigger


# === fcis-violation: pure functions are fine ===
def pure_function(x, y):
    return x + y


def transforms_data(items):
    return [item.upper() for item in items]


# === long-parameter-list: <4 is fine ===
def three_params(a, b, c):
    return a + b + c


def two_params(a, b):
    return a + b


# === global-mutable-state: constants are fine ===
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"
_PRIVATE_CONSTANT = 42
