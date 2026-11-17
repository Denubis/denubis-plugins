def parse_lines(text: str) -> list[tuple[str, int]]:
    rows = []
    for line in text.splitlines():
        if line.strip():
            name, value = line.split()
            rows.append((name, int(value)))
    return rows
