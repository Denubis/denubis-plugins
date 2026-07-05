"""Test fixtures: functions that SHOULD trigger ast-grep smell rules."""
# ruff: noqa — ast-grep pattern fixtures: this file is deliberately full of smells
# (undefined names, no-timeout requests, bare open, unused args) as positive-match
# targets for the rules. It is matched structurally, never executed.


# === nesting-depth: >3 levels nested control flow ===
def deeply_nested(data, config, flags):
    for item in data:
        if item.is_valid:
            for sub in item.children:
                if sub.active:  # 4th level — should trigger
                    process(sub)


# === fcis-violation: I/O calls in functions ===
def reads_file(path):
    with open(path) as f:
        return f.read()


def calls_requests(url):
    import requests

    return requests.get(url).json()


def uses_pathlib(path):
    from pathlib import Path

    return Path(path).read_text()


def uses_db(query):
    return db.execute(query)


# === long-parameter-list: >=4 parameters ===
def too_many_params(a, b, c, d):
    return a + b + c + d


def even_more_params(a, b, c, d, e):
    return a + b + c + d + e


# === global-mutable-state: module-level non-constant assignments ===
cache = {}
default_config = {"debug": False}
_internal_state = []
