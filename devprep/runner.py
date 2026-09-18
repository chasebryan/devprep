"""Execute a reviewed plan and retain an honest, machine-readable outcome."""

import json
import os
import shlex
import shutil
import subprocess
import tarfile
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from .managers import SYSTEM_MANAGERS, successful
from .platforms import executable
from .recipes import (data_dir, install_notebooks, install_vscode, install_java_tool,
                      install_composer, install_pipx)


def display_command(command):
    return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


def privilege_prefix():
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    for command in ("sudo", "doas"):
        if shutil.which(command):
            return [command]
    raise ValueError("Installing system packages needs root, sudo, or doas. Run as your normal user with sudo/doas available.")


def refresh_windows_environment():
    """Pick up PATH/JAVA_HOME changes made by native installers in this process."""
    if os.name != "nt":
        return
    import winreg
    paths = [os.environ.get("PATH", "")]
    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, "Environment")):
        try:
            with winreg.OpenKey(hive, key) as handle:
                for name in ("PATH", "JAVA_HOME"):
                    try:
                        value = os.path.expandvars(winreg.QueryValueEx(handle, name)[0])
                        if name == "PATH":
                            paths.append(value)
                        else:
                            os.environ[name] = value
                    except OSError:
                        pass
        except OSError:
            pass
    os.environ["PATH"] = os.pathsep.join(dict.fromkeys(os.pathsep.join(paths).split(os.pathsep)))


def execute(plan, *, no_refresh=False, report_path=None, allow_unavailable=False):
    manager = plan.host.manager
    if any(step.commands for step in plan.steps) and not shutil.which(executable(manager)):
        raise ValueError("Package manager is missing: " + executable(manager) + ". Use install.sh/install.ps1 for prerequisites.")
    if manager == "brew" and hasattr(os, "geteuid") and os.geteuid() == 0:
        raise ValueError("Run Homebrew as your normal user, not root.")
    prefix = privilege_prefix() if any(s.privileged for s in plan.steps) else []
    report = {"host": plan.to_dict()["host"], "started": datetime.now(timezone.utc).isoformat(),
              "results": [], "commands": [], "error": None}
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive", HOMEBREW_NO_AUTO_UPDATE="1",
               HOMEBREW_NO_INSTALL_UPGRADE="1")
    path = Path(report_path) if report_path else data_dir() / "reports" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + ".json")
    # Check report writability before the first package-manager mutation.
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError("Report already exists; choose a new --report path: " + str(path))

    def save():
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    def run(command, privileged=False, native=False):
        args = (prefix if privileged else []) + command
        print("  $ " + display_command(args), flush=True)
        completed = subprocess.run(args, env=env, check=False)
        report["commands"].append({"args": args, "returncode": completed.returncode})
        if native:
            refresh_windows_environment()
            for name in ("PATH", "JAVA_HOME"):
                if name in os.environ:
                    env[name] = os.environ[name]
        return successful(manager, completed.returncode) if native else completed.returncode == 0

    status = {}
    save()
    try:
        if plan.refresh and not no_refresh:
            if not run(plan.refresh, manager in SYSTEM_MANAGERS):
                report["error"] = "Package index refresh failed; no tool installations attempted. Fix the package manager and rerun."
                return 1
        for step in plan.steps:
            print("\n[" + step.category + "] " + step.name, flush=True)
            reason = step.reason
            try:
                blocked = [d for d in step.requires if status.get(d) not in {"installed", "included"}]
                if blocked:
                    outcome, reason = "blocked", "Dependencies did not complete: " + ", ".join(blocked)
                elif reason.startswith("unavailable:"):
                    outcome = "unavailable"
                elif reason.startswith("not applicable:"):
                    outcome = "not-applicable"
                elif step.recipe == "notebooks":
                    outcome = "installed" if install_notebooks(run) else "failed"
                elif step.recipe == "vscode":
                    outcome = "installed" if install_vscode(plan.host) else "failed"
                elif step.recipe in {"maven", "gradle"}:
                    outcome = "installed" if install_java_tool(step.recipe) else "failed"
                elif step.recipe == "composer":
                    outcome = "installed" if install_composer(run) else "failed"
                elif step.recipe == "pipx":
                    outcome = "installed" if install_pipx(run) else "failed"
                elif step.commands:
                    outcome = "installed" if all(run(c, step.privileged, True) for c in step.commands) else "failed"
                else:
                    outcome = "included"
            except (OSError, ValueError, KeyError, tarfile.TarError, zipfile.BadZipFile, ET.ParseError) as error:
                outcome, reason = "failed", str(error)
            status[step.id] = outcome
            report["results"].append({"id": step.id, "status": outcome, "detail": reason, "notes": step.notes})
            print("  " + outcome.upper() + (": " + reason if reason else ""), flush=True)
            if step.notes and outcome in {"installed", "included"}:
                print("  Next: " + step.notes)
            save()
        failures = {"failed", "blocked"} | (set() if allow_unavailable else {"unavailable"})
        return int(any(value in failures for value in status.values()))
    except KeyboardInterrupt:
        report["error"] = "Interrupted. Completed installations remain in place; rerun to retry the selection."
        return 130
    except OSError as error:
        report["error"] = str(error)
        return 1
    finally:
        report["finished"] = datetime.now(timezone.utc).isoformat()
        save()
        print("\nResults: " + ", ".join(str(list(status.values()).count(s)) + " " + s for s in sorted(set(status.values()))))
        if report["error"]:
            print(report["error"])
        print("Report: " + str(path))
        print("Open a new terminal to pick up installed tools. Review the next steps above.")
