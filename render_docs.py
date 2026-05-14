#!/usr/bin/env python3
"""
render_docs.py
Renders a design document YAML file into a Docsify-compatible Markdown file.

Usage:
    python render_docs.py design.yaml
    python render_docs.py design.yaml --output docs/DESIGN.md
    python render_docs.py design.yaml --output docs/DESIGN.md --no-skip-placeholders
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

PLACEHOLDER_PATTERNS = [
    re.compile(r"^\[.*\]$"),  # [Some placeholder text]
    re.compile(r"^YYYY-MM-DD$"),  # date placeholders
    re.compile(r"^\[.*\]\s*$"),  # [placeholder] with trailing space
]


def is_placeholder(value: str) -> bool:
    """Return True if a string looks like an unfilled template placeholder."""
    if not isinstance(value, str):
        return False
    v = value.strip()
    return any(p.match(v) for p in PLACEHOLDER_PATTERNS)


def has_content(value) -> bool:
    """Return True if a value is present and not a placeholder."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not is_placeholder(value)
    if isinstance(value, list):
        return any(has_content(i) for i in value)
    if isinstance(value, dict):
        return any(has_content(v) for v in value.values())
    return bool(value)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def h1(text):
    return f"# {text}\n"


def h2(text):
    return f"\n## {text}\n"


def h3(text):
    return f"\n### {text}\n"


def h4(text):
    return f"\n#### {text}\n"


def badge(label, value, color="blue"):
    label_enc = label.replace(" ", "_").replace("-", "--")
    value_enc = str(value).replace(" ", "_").replace("-", "--")
    return f"![{label}](https://img.shields.io/badge/{label_enc}-{value_enc}-{color})"


STATUS_COLORS = {
    "draft": "yellow",
    "review": "orange",
    "approved": "brightgreen",
}


def render_docs_url(docs_url) -> str:
    """Render docs_url whether it's a string, a list of strings,
    or a list of {label, url} dicts."""
    if not docs_url:
        return ""
    if isinstance(docs_url, str):
        return f" — [docs]({docs_url})"
    if isinstance(docs_url, list):
        parts = []
        for item in docs_url:
            if isinstance(item, dict):
                label = item.get("label", "link")
                url = item.get("url", "")
                parts.append(f"[{label}]({url})")
            elif isinstance(item, str):
                parts.append(f"[docs]({item})")
        return " — " + " · ".join(parts) if parts else ""
    return ""


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_metadata(meta: dict) -> str:
    out = []
    title = meta.get("title", "Design Document")
    out.append(h1(title))

    status = meta.get("status", "draft")
    color = STATUS_COLORS.get(status, "blue")
    version = meta.get("version", "")
    badges = [badge("status", status, color)]
    if version:
        badges.append(badge("version", version, "lightgrey"))
    out.append(" ".join(badges) + "\n")

    fields = [
        ("Author", meta.get("author", "")),
        ("Created", meta.get("created", "")),
        ("Updated", meta.get("updated", "") or meta.get("created", "")),
        ("Reviewers", ", ".join(meta.get("reviewers", [])) or "—"),
    ]
    rows = ["| | |", "|---|---|"]
    for label, value in fields:
        if has_content(value):
            rows.append(f"| **{label}** | {value} |")
    out.append("\n".join(rows) + "\n")
    return "\n".join(out)


def render_overview(data: dict) -> str:
    if not data:
        return ""
    out = [h2("1. Overview")]
    summary = data.get("summary", "")
    if has_content(summary):
        out.append(f"{summary.strip()}\n")

    goals = [g for g in data.get("goals", []) if has_content(g)]
    if goals:
        out.append(h3("Goals"))
        out.extend(f"- {g}" for g in goals)
        out.append("")

    non_goals = [g for g in data.get("non_goals", []) if has_content(g)]
    if non_goals:
        out.append(h3("Non-Goals"))
        out.extend(f"- {g}" for g in non_goals)
        out.append("")

    return "\n".join(out)


def render_context(data: dict) -> str:
    if not data:
        return ""
    out = [h2("2. Context & Motivation")]
    for key, label in [("background", "Background"), ("motivation", "Motivation")]:
        val = data.get(key, "")
        if has_content(val):
            out.append(h3(label))
            out.append(f"{val.strip()}\n")

    refs = [r for r in data.get("references", []) if has_content(r)]
    if refs:
        out.append(h3("References"))
        for ref in refs:
            label = ref.get("label", "Link")
            url = ref.get("url", "#")
            out.append(f"- [{label}]({url})")
        out.append("")
    return "\n".join(out)


def render_scope(data: dict) -> str:
    if not data:
        return ""
    out = [h2("3. Scope")]
    for key, label in [
        ("in_scope", "In Scope"),
        ("out_of_scope", "Out of Scope"),
        ("constraints", "Constraints"),
        ("assumptions", "Assumptions"),
    ]:
        items = [i for i in data.get(key, []) if has_content(i)]
        if items:
            out.append(h3(label))
            out.extend(f"- {i}" for i in items)
            out.append("")
    return "\n".join(out)


def render_stakeholders(data: list) -> str:
    if not data:
        return ""
    out = [h2("4. Stakeholders")]
    out.append("| Role | Name | Responsibilities |")
    out.append("|---|---|---|")
    for s in data:
        role = s.get("role", "")
        name = s.get("name", "")
        resps = "; ".join(s.get("responsibilities", []))
        if has_content(name) or has_content(role):
            out.append(f"| {role} | {name} | {resps} |")
    out.append("")
    return "\n".join(out)


def render_technical_design(data: dict) -> str:
    if not data:
        return ""
    out = [h2("5. Technical Design")]

    arch = data.get("architecture", {})
    if arch:
        out.append(h3("Architecture"))
        desc = arch.get("description", "")
        if has_content(desc):
            out.append(f"{desc.strip()}\n")
        components = arch.get("components", [])
        if components:
            out.append(h4("Components"))
            out.append("| Component | Technology | Description |")
            out.append("|---|---|---|")
            for c in components:
                out.append(
                    f"| **{c.get('name', '')}** | `{c.get('technology', '')}` | {c.get('description', '')} |"
                )
            out.append("")

    interfaces = data.get("interfaces", {})
    if interfaces:
        out.append(h3("Interfaces"))
        for direction in ["inputs", "outputs"]:
            items = interfaces.get(direction, [])
            if items:
                out.append(h4(direction.capitalize()))
                out.append("| Name | Format | Description |")
                out.append("|---|---|---|")
                for i in items:
                    out.append(
                        f"| `{i.get('name', '')}` | {i.get('format', '')} | {i.get('description', '')} |"
                    )
                out.append("")

    deps = data.get("dependencies", {})
    external = deps.get("external", [])
    if external:
        out.append(h3("Dependencies"))
        out.append("| Package | Version | Purpose | Docs |")
        out.append("|---|---|---|---|")
        for d in external:
            name = d.get("name", "")
            version = d.get("version", "") or "—"
            # handle the typo 'pupose' gracefully alongside 'purpose'
            purpose = d.get("purpose") or d.get("pupose") or ""
            docs = render_docs_url(d.get("docs_url"))
            out.append(f"| `{name}` | {version} | {purpose} | {docs} |")
        out.append("")

    return "\n".join(out)


def render_implementation(data: dict) -> str:
    if not data:
        return ""
    out = [h2("6. Implementation Approach")]

    strategy = data.get("strategy", "")
    if has_content(strategy):
        out.append(h3("Strategy"))
        out.append(f"{strategy.strip()}\n")

    notes = data.get("notes_for_developer", "")
    if has_content(notes):
        out.append(h3("Notes for Developer"))
        out.append(f"{notes.strip()}\n")

    phases = data.get("phases", [])
    if phases:
        out.append(h3("Phases"))
        for p in phases:
            name = p.get("name", f"Phase {p.get('phase', '')}")
            desc = p.get("description", "")
            out.append(f"**Phase {p.get('phase', '')} — {name}**\n")
            if has_content(desc):
                out.append(f"{desc}\n")

    error_handling = data.get("error_handling", "")
    if has_content(error_handling):
        out.append(h3("Error Handling"))
        out.append(f"{error_handling.strip()}\n")

    logging = data.get("logging", "")
    if has_content(logging):
        out.append(h3("Logging"))
        out.append(f"{logging.strip()}\n")

    return "\n".join(out)


def render_testing(data: dict) -> str:
    if not data:
        return ""
    out = [h2("7. Testing Strategy")]

    approach = data.get("approach", "")
    if has_content(approach):
        out.append(h3("Approach"))
        out.append(f"{approach.strip()}\n")

    cases = [c for c in data.get("test_cases", []) if has_content(c)]
    if cases:
        out.append(h3("Test Cases"))
        out.append("| ID | Description | Expected Result |")
        out.append("|---|---|---|")
        for c in cases:
            out.append(
                f"| {c.get('id', '')} | {c.get('description', '')} | {c.get('expected_result', '')} |"
            )
        out.append("")

    criteria = [c for c in data.get("acceptance_criteria", []) if has_content(c)]
    if criteria:
        out.append(h3("Acceptance Criteria"))
        out.extend(f"- {c}" for c in criteria)
        out.append("")

    return "\n".join(out)


def render_risks(data: list) -> str:
    if not data:
        return ""
    filtered = [r for r in data if has_content(r.get("description", ""))]
    if not filtered:
        return ""
    out = [h2("8. Risks & Mitigations")]
    out.append("| ID | Risk | Likelihood | Impact | Mitigation |")
    out.append("|---|---|---|---|---|")
    for r in filtered:
        out.append(
            f"| {r.get('id', '')} "
            f"| {r.get('description', '')} "
            f"| {r.get('likelihood', '')} "
            f"| {r.get('impact', '')} "
            f"| {r.get('mitigation', '')} |"
        )
    out.append("")
    return "\n".join(out)


def render_open_questions(data: list) -> str:
    if not data:
        return ""
    filtered = [q for q in data if has_content(q.get("question", ""))]
    if not filtered:
        return ""
    out = [h2("9. Open Questions")]
    out.append("| ID | Question | Owner | Due |")
    out.append("|---|---|---|---|")
    for q in filtered:
        owner = q.get("owner", "—")
        due = q.get("due", "—")
        owner = "—" if is_placeholder(str(owner)) else owner
        due = "—" if is_placeholder(str(due)) else due
        out.append(f"| {q.get('id', '')} | {q.get('question', '')} | {owner} | {due} |")
    out.append("")
    return "\n".join(out)


def render_decision_log(data: list) -> str:
    if not data:
        return ""
    filtered = [d for d in data if has_content(d.get("decision", ""))]
    if not filtered:
        return ""
    out = [h2("10. Decision Log")]
    for d in filtered:
        out.append(h3(f"{d.get('id', '')} — {d.get('decision', '')}"))
        out.append(f"**Date:** {d.get('date', '—')}  ")
        out.append(f"**Rationale:** {d.get('rationale', '')}\n")
        alts = [a for a in d.get("alternatives_considered", []) if has_content(a)]
        if alts:
            out.append("**Alternatives considered:**")
            out.extend(f"- {a}" for a in alts)
            out.append("")
    return "\n".join(out)


def render_appendix(data: dict) -> str:
    if not data:
        return ""
    out = [h2("11. Appendix")]

    glossary = [g for g in data.get("glossary", []) if has_content(g.get("term", ""))]
    if glossary:
        out.append(h3("Glossary"))
        out.append("| Term | Definition |")
        out.append("|---|---|")
        for g in glossary:
            out.append(f"| **{g.get('term', '')}** | {g.get('definition', '')} |")
        out.append("")

    notes = data.get("notes", "")
    if has_content(notes):
        out.append(h3("Notes"))
        out.append(f"{notes.strip()}\n")

    return "\n".join(out)


def render_footer(source_file: str) -> str:
    today = date.today().isoformat()
    return f"\n\n---\n*Generated from `{source_file}` on {today}*\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_markdown(doc: dict, source_file: str) -> str:
    sections = [
        render_metadata(doc.get("metadata", {})),
        render_overview(doc.get("overview", {})),
        render_context(doc.get("context", {})),
        render_scope(doc.get("scope", {})),
        render_stakeholders(doc.get("stakeholders", [])),
        render_technical_design(doc.get("technical_design", {})),
        render_implementation(doc.get("implementation", {})),
        render_testing(doc.get("testing", {})),
        render_risks(doc.get("risks", [])),
        render_open_questions(doc.get("open_questions", [])),
        render_decision_log(doc.get("decision_log", [])),
        render_appendix(doc.get("appendix", {})),
        render_footer(source_file),
    ]
    return "\n".join(s for s in sections if s)


def main():
    parser = argparse.ArgumentParser(
        description="Render a design document YAML file to Docsify-compatible Markdown."
    )
    parser.add_argument(
        "--template",
        help="Dumps the template YAML contents to stdout.",
        action="store_true",
    )
    parser.add_argument(
        "input",
        help="Path to the design YAML file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output Markdown file path (default: same name as input with .md extension)",
    )
    parser.add_argument(
        "--no-skip-placeholders",
        action="store_true",
        default=False,
        help="Include placeholder values in output instead of skipping them",
    )
    args = parser.parse_args()

    if args.template:
        print("hello")

    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: file not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        output_path = (
            Path(args.output) if args.output else input_path.with_suffix(".md")
        )

        with open(input_path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        if not isinstance(doc, dict):
            print("Error: YAML file did not parse to a mapping.", file=sys.stderr)
            sys.exit(1)

        markdown = build_markdown(doc, input_path.name)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"✓ Written to {output_path}")


if __name__ == "__main__":
    main()
