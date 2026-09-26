"""A small YAML subset reader for Compass Config frontmatter.

Supports nested maps, lists of scalars, and lists of single-level maps.
It is not a general YAML parser.
"""

def parse_scalar(raw):
    text = raw.strip()
    if text == "" or text in ("null", "~", "Null", "NULL"):
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)
    return text


def split_kv(text):
    if ":" not in text:
        raise ValueError("expected key: value, got %r" % text)
    key, rest = text.split(":", 1)
    key = key.strip()
    if rest.strip() == "":
        return key, None
    return key, parse_scalar(rest)


def _next_content(lines, index):
    j = index + 1
    while j < len(lines):
        stripped = lines[j].strip()
        if stripped and not stripped.startswith("#"):
            return j
        j += 1
    return None


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def parse_yaml(text):
    lines = text.replace("\t", "  ").splitlines()
    root = {}
    # stack items: (indent, container)
    stack = [(-1, root)]

    def parent():
        return stack[-1][1]

    def pop_to(indent):
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

    for i, line in enumerate(lines):
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = _indent(line)
        content = line.strip()
        pop_to(indent)
        container = parent()

        if content.startswith("- "):
            if not isinstance(container, list):
                raise ValueError("list item outside a list: %s" % content)
            item = content[2:]
            if ":" in item:
                key, val = split_kv(item)
                node = {key: {} if val is None else val}
                container.append(node)
                if val is None:
                    nxt = _next_content(lines, i)
                    child = {}
                    if nxt is not None and _indent(lines[nxt]) > indent and lines[nxt].strip().startswith("- "):
                        child = []
                    node[key] = child
                    stack.append((indent, child))
                else:
                    stack.append((indent, node))
            else:
                container.append(parse_scalar(item))
            continue

        if not isinstance(container, dict):
            raise ValueError("key outside a map: %s" % content)
        key, val = split_kv(content)
        if val is not None:
            container[key] = val
            continue
        nxt = _next_content(lines, i)
        child = {}
        if nxt is not None and _indent(lines[nxt]) > indent and lines[nxt].strip().startswith("- "):
            child = []
        elif nxt is None or _indent(lines[nxt]) <= indent:
            child = None
        container[key] = child
        if isinstance(child, (dict, list)):
            stack.append((indent, child))
    return root


def frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    data = parse_yaml("\n".join(lines[1:end]))
    body = "\n".join(lines[end + 1:])
    if text.endswith("\n"):
        body = body + "\n" if body and not body.endswith("\n") else body
    return data, "\n".join(lines[end + 1:]) + ("\n" if text.endswith("\n") else "")
