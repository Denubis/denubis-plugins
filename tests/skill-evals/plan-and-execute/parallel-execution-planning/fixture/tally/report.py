def render_text(rows: list[tuple[str, int]]) -> str:
    return "".join(f"{name}: {value}\n" for name, value in rows)
