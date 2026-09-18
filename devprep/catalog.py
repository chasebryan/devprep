"""Load and validate the declarative catalog, then resolve selections."""

import json
from pathlib import Path

from .platforms import MANAGERS


def load_catalog():
    data = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
    tools = {tool["id"]: tool for tool in data["tools"]}
    if len(tools) != len(data["tools"]):
        raise ValueError("Duplicate tool ID in catalog")
    for tool in tools.values():
        if tool["category"] not in data["categories"]:
            raise ValueError("Unknown category: " + tool["category"])
        for manager, packages in tool["packages"].items():
            if manager not in MANAGERS or not packages:
                raise ValueError("Invalid package mapping for " + tool["id"])
            if any(not isinstance(p, str) or p.startswith("-") or any(c.isspace() for c in p)
                   for p in packages):
                raise ValueError("Invalid package name for " + tool["id"])
        for dependency in tool.get("requires", []):
            if dependency not in tools:
                raise ValueError("Unknown dependency: " + dependency)
    # Also validates the dependency graph for all tools.
    select_tools(data, [], [], [])
    return data


def select_tools(catalog, categories, selected, excluded):
    tools = {tool["id"]: tool for tool in catalog["tools"]}
    for category in categories:
        if category not in catalog["categories"]:
            raise ValueError("Unknown category: " + category)
    for tool in selected + excluded:
        if tool not in tools:
            raise ValueError("Unknown tool: " + tool)
    if not categories and not selected:
        wanted = list(tools)
    else:
        wanted = [t["id"] for t in tools.values() if t["category"] in categories or t["id"] in selected]
    result, visited, visiting = [], set(), set()

    def visit(ident):
        if ident in visited:
            return
        if ident in visiting:
            raise ValueError("Dependency cycle at " + ident)
        if ident in excluded:
            raise ValueError("Required tool is excluded: " + ident)
        visiting.add(ident)
        for dep in tools[ident].get("requires", []):
            visit(dep)
        visiting.remove(ident)
        visited.add(ident)
        result.append(tools[ident])

    for ident in wanted:
        if ident not in excluded:
            visit(ident)
    if not result:
        raise ValueError("No tools selected")
    return result
