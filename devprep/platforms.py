"""Detect the host without executing /etc/os-release as shell code."""

import platform
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path


MANAGERS = ("apt", "dnf", "yum", "pacman", "zypper", "apk", "xbps", "emerge", "nix", "brew", "winget")
EXECUTABLES = {"apt": "apt-get", "xbps": "xbps-install"}
FAMILIES = {
    "debian": "apt", "ubuntu": "apt", "linuxmint": "apt", "pop": "apt",
    "kali": "apt", "raspbian": "apt", "fedora": "dnf", "rhel": "dnf",
    "centos": "dnf", "rocky": "dnf", "almalinux": "dnf", "ol": "dnf",
    "amzn": "dnf", "arch": "pacman", "manjaro": "pacman", "endeavouros": "pacman",
    "opensuse": "zypper", "opensuse-leap": "zypper", "opensuse-tumbleweed": "zypper",
    "sles": "zypper", "suse": "zypper", "alpine": "apk", "void": "xbps",
    "gentoo": "emerge", "funtoo": "emerge", "nixos": "nix",
}


@dataclass(frozen=True)
class Host:
    system: str
    distro: str
    arch: str
    manager: str


def read_os_release(path=Path("/etc/os-release")):
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key in {"ID", "ID_LIKE", "PRETTY_NAME", "VARIANT_ID"}:
                try:
                    values[key] = " ".join(shlex.split(value))
                except ValueError:
                    raise ValueError("Malformed os-release field: " + key)
    return values


def detect(system=None, release=None, which=None, arch=None, immutable=None):
    system = system or platform.system()
    which = which or shutil.which
    arch = arch or platform.machine()
    if system == "Windows":
        return Host("windows", "windows", arch, "winget")
    if system == "Darwin":
        return Host("macos", "macos", arch, "brew")
    if system != "Linux":
        raise ValueError("Unsupported operating system: " + system)
    release = read_os_release() if release is None else release
    if immutable is None:
        immutable = Path("/run/ostree-booted").exists() or Path("/sbin/transactional-update").exists()
    if immutable:
        raise ValueError("Immutable Linux host detected. Run devprep inside a writable development "
                         "container (Toolbox or Distrobox); host package layering is not supported.")
    for distro in [release.get("ID", "")] + release.get("ID_LIKE", "").split():
        manager = FAMILIES.get(distro)
        if manager:
            if manager == "dnf" and not which("dnf") and which("yum"):
                manager = "yum"
            return Host("linux", release.get("ID", distro), arch, manager)
    raise ValueError("Unsupported Linux family: " + release.get("ID", "unknown") +
                     ". See docs/platforms.md for supported families.")


def preview_host(manager):
    return Host("windows" if manager == "winget" else "macos" if manager == "brew" else "linux",
                "preview", platform.machine(), manager)


def executable(manager):
    name = EXECUTABLES.get(manager, manager)
    found = shutil.which(name)
    if not found and manager == "brew":
        for prefix in ("/opt/homebrew", "/usr/local"):
            candidate = Path(prefix) / "bin/brew"
            if candidate.is_file():
                return str(candidate)
    return found or name
