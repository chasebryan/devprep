from dataclasses import asdict, dataclass, field

from .managers import SYSTEM_MANAGERS, install_commands, refresh_command
from .recipes import recipe_description, recipe_for


@dataclass
class Step:
    id: str
    name: str
    category: str
    commands: list = field(default_factory=list)
    recipe: str = ""
    reason: str = ""
    requires: list = field(default_factory=list)
    notes: str = ""
    privileged: bool = False


@dataclass
class Plan:
    host: object
    refresh: list
    steps: list

    def to_dict(self):
        return asdict(self)


def build_plan(host, tools):
    steps = []
    for tool in tools:
        step = Step(tool["id"], tool["name"], tool["category"],
                    requires=tool.get("requires", []), notes=tool.get("notes", ""))
        recipe = recipe_for(tool, host)
        if host.system not in tool.get("platforms", ["linux", "macos", "windows"]):
            step.reason = "not applicable: use WSL for this Unix tool on Windows"
        elif recipe:
            step.recipe = recipe
            step.reason = recipe_description(recipe, host)
        elif host.manager in tool["packages"]:
            step.commands = install_commands(host.manager, tool["packages"][host.manager],
                                             cask=tool.get("cask", False),
                                             overrides=tool.get("winget_override"))
            step.privileged = host.manager in SYSTEM_MANAGERS
        elif tool["id"] == "compose" and host.system in {"windows", "macos"}:
            step.reason = "included with Docker Desktop"
        else:
            step.reason = "unavailable: no maintained package mapping for " + host.manager
        steps.append(step)
    return Plan(host, refresh_command(host.manager) if any(s.commands for s in steps) else None, steps)
