def ensure_load_tag(content: str) -> str:
    if "institutional_media" in content:
        return content
    lines = content.splitlines()
    if lines and lines[0].startswith("{% extends"):
        lines.insert(1, "{% load institutional_media %}")
        return "\n".join(lines) + ("\n" if content.endswith("\n") else "")
    if content.startswith("{% load"):
        first_line_end = content.find("\n")
        first_line = content[:first_line_end]
        if "static" in first_line and "institutional_media" not in first_line:
            return content.replace(first_line, first_line + " institutional_media", 1)
        return first_line + " institutional_media\n" + content[first_line_end + 1 :]
    return "{% load institutional_media %}\n" + content
