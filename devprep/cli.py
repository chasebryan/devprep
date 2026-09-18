import argparse
import json
import subprocess
import sys

from . import __version__
from .catalog import load_catalog, select_tools
from .planner import build_plan
from .platforms import MANAGERS, detect, preview_host
from .recipes import notebook_python
from .runner import display_command, execute


def csv(value):
    return [part.strip() for part in value.split(",") if part.strip()]


def selection_list(value):
    values = csv(value)
    if not values:
        raise argparse.ArgumentTypeError("Select at least one name; an empty selection is not the full catalog.")
    return values


def parser():
    result = argparse.ArgumentParser(
        prog="devprep", description="Prepare a development workstation. Default: install the entire curated catalog.")
    result.add_argument("--version", action="version", version="devprep " + __version__)
    result.add_argument("--all", action="store_true", help="explicitly select the full catalog (the default)")
    result.add_argument("--custom", action="store_true", help="choose categories interactively, or use --categories/--tools")
    result.add_argument("--categories", type=selection_list, default=[], metavar="LIST", help="comma-separated categories to install")
    result.add_argument("--tools", type=selection_list, default=[], metavar="LIST", help="comma-separated tool IDs to install")
    result.add_argument("--exclude", type=selection_list, default=[], metavar="LIST", help="tool IDs to exclude; required dependencies cannot be excluded")
    result.add_argument("--list", action="store_true", help="list categories and tools")
    result.add_argument("--dry-run", action="store_true", help="print the plan without installing or refreshing anything")
    result.add_argument("--json", action="store_true", help="output the plan as JSON; implies --dry-run")
    result.add_argument("--manager", choices=MANAGERS, help="preview another package manager; requires --dry-run or --json")
    result.add_argument("--yes", "-y", action="store_true", help="accept the install plan and package agreements without prompting")
    result.add_argument("--no-refresh", action="store_true", help="use existing package indexes; keep your system current yourself")
    result.add_argument("--allow-unavailable", action="store_true", help="allow success when mappings are unavailable; failures still return nonzero")
    result.add_argument("--report", help="write the execution report to this new JSON file")
    result.add_argument("--launch-notebooks", action="store_true", help="launch the installed JupyterLab environment")
    return result


def choose_categories(catalog):
    if not sys.stdin.isatty():
        raise ValueError("Interactive selection needs a terminal. Use --custom --categories core,build or --tools git,python.")
    names = list(catalog["categories"])
    print("\nChoose categories (comma-separated names or numbers):")
    for i, name in enumerate(names, 1):
        print("  " + str(i) + ". " + name + " - " + catalog["categories"][name])
    values = csv(input("Categories (blank cancels): "))
    if not values:
        raise ValueError("No categories selected; cancelled.")
    selected = []
    for value in values:
        if value.isdigit() and 1 <= int(value) <= len(names):
            value = names[int(value) - 1]
        if value not in names:
            raise ValueError("Unknown category: " + value)
        selected.append(value)
    return selected


def print_plan(plan, no_refresh=False):
    print("devprep - " + plan.host.distro + " / " + plan.host.arch + " / " + plan.host.manager)
    print("Selected " + str(len(plan.steps)) + " tools. Native packages come from your configured repositories.")
    if plan.refresh and not no_refresh:
        print("Prepare: " + display_command(plan.refresh))
    if plan.host.manager == "pacman" and not no_refresh:
        print("Arch: the preparation step upgrades the system to avoid a partial upgrade.")
    previous = None
    for step in plan.steps:
        if step.category != previous:
            print("\n" + step.category.upper())
            previous = step.category
        print("  " + step.id + " - " + step.name)
        for command in step.commands:
            print("    " + ("[root] " if step.privileged else "") + display_command(command))
        if step.reason:
            print("    " + step.reason)
    print("\nThis full workstation can require many GB and a lengthy download. Package installers may start services.")


def main(argv=None):
    argparser = parser()
    args = argparser.parse_args(argv)
    try:
        if args.manager and not (args.dry_run or args.json):
            raise ValueError("--manager is for previews only; add --dry-run or --json.")
        if args.all and (args.custom or args.categories or args.tools or args.exclude):
            raise ValueError("--all cannot be combined with custom selections or exclusions.")
        if args.launch_notebooks:
            if args.dry_run or args.json or args.list or args.custom or args.categories or args.tools or args.exclude or args.all:
                raise ValueError("--launch-notebooks cannot be combined with planning or selection options.")
            interpreter = notebook_python()
            if not interpreter.exists():
                raise ValueError("Install notebooks first: python -m devprep --tools notebooks")
            return subprocess.call([str(interpreter), "-m", "jupyterlab"])
        catalog = load_catalog()
        if args.list:
            for category, description in catalog["categories"].items():
                print(category + " - " + description)
                for tool in catalog["tools"]:
                    if tool["category"] == category:
                        print("  " + tool["id"] + " - " + tool["name"])
            return 0
        if args.custom and not args.categories and not args.tools:
            args.categories = choose_categories(catalog)
        host = preview_host(args.manager) if args.manager else detect()
        selected = select_tools(catalog, args.categories, args.tools, args.exclude)
        plan = build_plan(host, selected)
        if args.json:
            document = plan.to_dict()
            if args.no_refresh:
                document["refresh"] = None
            print(json.dumps(document, indent=2))
            return 0
        print_plan(plan, args.no_refresh)
        if args.dry_run:
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                raise ValueError("Non-interactive installation requires --yes. Use --dry-run to preview first.")
            answer = input("\nInstall this selection? [Y/n/custom] ").strip().lower()
            if answer in {"c", "custom"}:
                categories = choose_categories(catalog)
                plan = build_plan(host, select_tools(catalog, categories, [], args.exclude))
                print_plan(plan, args.no_refresh)
                answer = input("\nInstall this custom selection? [Y/n] ").strip().lower()
            if answer not in {"", "y", "yes"}:
                print("Cancelled.")
                return 0
        return execute(plan, no_refresh=args.no_refresh, report_path=args.report,
                       allow_unavailable=args.allow_unavailable)
    except (ValueError, OSError) as error:
        print("devprep: " + str(error), file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 130
