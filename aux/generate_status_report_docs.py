"""Generate docs/status_report.md from the StatusReport Pydantic schema."""

import json
import pathlib

from ktp_controller.examomatic.schemas import StatusReport

OUTPUT = pathlib.Path("docs/status_report.md")


def _display_name(def_key: str) -> str:
    return def_key.lstrip("_")


def _anchor(def_key: str) -> str:
    return _display_name(def_key).lower()


def _collect_refs(prop: dict) -> list[str]:
    """Return all $ref keys reachable from a property definition."""
    refs = []
    if "$ref" in prop:
        refs.append(prop["$ref"].split("/")[-1])
    for sub in prop.get("anyOf", []):
        refs.extend(_collect_refs(sub))
    if "items" in prop:
        refs.extend(_collect_refs(prop["items"]))
    if "additionalProperties" in prop and isinstance(
        prop["additionalProperties"], dict
    ):
        refs.extend(_collect_refs(prop["additionalProperties"]))
    return refs


def _ordered_defs(schema: dict) -> list[tuple[str, dict, int]]:
    """Return (key, defn, depth) triples in depth-first, top-down order."""
    defs = schema.get("$defs", {})
    visited: list[str] = []
    depth_map: dict[str, int] = {}

    def visit(key: str, depth: int) -> None:
        if key not in defs:
            return
        if key in visited:
            return
        visited.append(key)
        depth_map[key] = depth
        defn = defs[key]
        for prop in defn.get("properties", {}).values():
            for ref_key in _collect_refs(prop):
                visit(ref_key, depth + 1)

    # Seed traversal from root properties in declaration order
    for prop in schema.get("properties", {}).values():
        for ref_key in _collect_refs(prop):
            visit(ref_key, 1)

    # Append any defs not reachable from root (shouldn't happen, but be safe)
    for key in defs:
        if key not in visited:
            visited.append(key)
            depth_map[key] = 1

    return [(key, defs[key], depth_map[key]) for key in visited]


def _resolve_type(prop: dict, defs: dict) -> str:
    if "$ref" in prop:
        key = prop["$ref"].split("/")[-1]
        return f"[{_display_name(key)}](#{_anchor(key)})"

    if "anyOf" in prop:
        non_null = [p for p in prop["anyOf"] if p.get("type") != "null"]
        nullable = len(non_null) < len(prop["anyOf"])
        inner = _resolve_type(non_null[0], defs) if non_null else "unknown"
        if nullable:
            wrapped = f"({inner})" if " " in inner else inner
            return f"{wrapped} or `null`"
        return inner

    ptype = prop.get("type", "unknown")

    if ptype == "array":
        items = prop.get("items", {})
        if items:
            item_type = _resolve_type(items, defs)
            return f"`array` of {item_type}"
        return "`array`"

    if ptype == "object":
        add_props = prop.get("additionalProperties")
        if isinstance(add_props, dict) and add_props:
            val_type = _resolve_type(add_props, defs)
            return f"`object` mapping `string` → {val_type}"
        return "`object`"

    fmt = prop.get("format")
    if fmt == "date-time":
        return "`datetime`"
    if ptype == "string":
        return "`string`"
    if ptype == "integer":
        return "`integer`"
    if ptype == "number":
        return "`number`"
    if ptype == "boolean":
        return "`boolean`"
    return f"`{ptype}`"


def _notes(prop: dict) -> str:
    parts = []
    if "const" in prop:
        parts.append(f"const: `{prop['const']}`")
    if "minimum" in prop:
        parts.append(f"minimum: `{prop['minimum']}`")
    if "enum" in prop:
        values = ", ".join(f"`{v}`" for v in prop["enum"])
        parts.append(f"one of {values}")
    if "anyOf" in prop:
        non_null = [p for p in prop["anyOf"] if p.get("type") != "null"]
        if non_null:
            inner = non_null[0]
            if "minimum" in inner:
                parts.append(f"minimum: `{inner['minimum']}`")
    return "; ".join(parts)


def _render_object(title: str, schema: dict, defs: dict, depth: int = 0) -> str:
    heading = "#" * (depth + 2)
    lines = [f"{heading} {title}\n"]

    if schema.get("enum"):
        values = ", ".join(f"`{v}`" for v in schema["enum"])
        lines.append(f"Enum — one of: {values}\n")
        return "\n".join(lines)

    props = schema.get("properties", {})
    required = set(schema.get("required", []))

    always_present_map = {
        field: (field in required or "default" in prop) for field, prop in props.items()
    }
    all_always_present = all(always_present_map.values())

    if all_always_present:
        lines.append("All fields are always present.\n")
        lines.append("| Field | Type | Description | Example | Notes |")
        lines.append("|-------|------|-------------|---------|-------|")
    else:
        lines.append(
            "| Field | Type | Always present | Description | Example | Notes |"
        )
        lines.append(
            "|-------|------|:--------------:|-------------|---------|-------|"
        )

    for field, prop in props.items():
        ftype = _resolve_type(prop, defs)
        description = prop.get("description", "")
        note = _notes(prop)
        examples = prop.get("examples", [])
        example = f"`{json.dumps(examples[0])}`" if examples else ""
        if all_always_present:
            lines.append(
                f"| `{field}` | {ftype} | {description} | {example} | {note} |"
            )
        else:
            always_present = "yes" if always_present_map[field] else "no"
            lines.append(
                f"| `{field}` | {ftype} | {always_present} | {description} | {example} | {note} |"
            )

    lines.append("")
    return "\n".join(lines)


def generate() -> str:
    schema = StatusReport.model_json_schema()
    defs = schema.get("$defs", {})

    ordered = _ordered_defs(schema)

    v = schema["properties"]["v"]["const"]
    example_files = sorted(OUTPUT.parent.glob(f"status_report_v{v}_example*.json"))

    sections = []

    header_parts = [
        "# StatusReport\n",
        "API documentation for the `StatusReport` schema.\n",
        "Auto-generated from `ktp_controller/examomatic/schemas.py`.\n"
        "Do not edit this file manually — run `make docs` to regenerate.\n",
    ]
    if example_files:
        header_parts.append(
            "Examples:\n\n"
            + "\n".join(f"- [{f.name}]({f.name})" for f in example_files)
            + "\n"
        )
    sections.append("\n".join(header_parts) + "\n")

    # Root object at depth 0 → ## heading
    sections.append(_render_object("StatusReport", schema, defs, depth=0))

    for key, defn, depth in ordered:
        sections.append(_render_object(_display_name(key), defn, defs, depth=depth))

    return "\n".join(sections)


if __name__ == "__main__":
    content = generate()
    OUTPUT.write_text(content)
    print(f"Written {OUTPUT}")
