"""Construct argument vectors. Never invoke a shell or interpolate user input."""

from .platforms import executable


SYSTEM_MANAGERS = {"apt", "dnf", "yum", "pacman", "zypper", "apk", "xbps", "emerge"}


def refresh_command(manager):
    # Pacman must never refresh its databases without a full upgrade.
    args = {
        "apt": ["update"], "dnf": ["makecache"], "yum": ["makecache"],
        "pacman": ["-Syu", "--noconfirm"], "zypper": ["--non-interactive", "refresh"],
        "apk": ["update"], "xbps": ["-S"], "emerge": ["--sync"],
        "brew": ["update"], "winget": ["source", "update", "--disable-interactivity"],
    }.get(manager)
    return [executable(manager)] + args if args else None


def install_commands(manager, packages, *, cask=False, overrides=None):
    exe = executable(manager)
    if manager == "winget":
        commands = []
        for package in packages:
            command = [exe, "install", "--id", package, "--exact", "--source", "winget",
                       "--silent", "--no-upgrade", "--accept-package-agreements",
                       "--accept-source-agreements", "--disable-interactivity"]
            if overrides:
                command += ["--override", overrides]
            commands.append(command)
        return commands
    if manager == "nix":
        return [[exe, "--extra-experimental-features", "nix-command flakes", "profile", "install"] +
                ["nixpkgs#" + p for p in packages]]
    args = {
        "apt": ["install", "-y"], "dnf": ["install", "-y"], "yum": ["install", "-y"],
        "pacman": ["-S", "--needed", "--noconfirm"],
        "zypper": ["--non-interactive", "install"], "apk": ["add"],
        "xbps": ["-y"], "emerge": ["--noreplace", "--ask=n"],
        "brew": ["install"] + (["--cask"] if cask else []),
    }[manager]
    return [[exe] + args + list(packages)]


def successful(manager, returncode):
    # WinGet's no-upgrade path reports UPDATE_NOT_APPLICABLE for existing packages.
    return returncode == 0 or (manager == "winget" and returncode & 0xFFFFFFFF == 0x8A15002B)
