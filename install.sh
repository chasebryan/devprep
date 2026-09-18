#!/bin/sh
# Run from a downloaded checkout. This script intentionally does not pipe remote code into a shell.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"
export PYTHONDONTWRITEBYTECODE=1
preview=0
assume_yes=0
for arg in "$@"; do
    case "$arg" in
        --dry-run|--json|--list|--help|-h|--version) preview=1 ;;
        --yes|-y) assume_yes=1 ;;
    esac
done

confirm_bootstrap() {
    if [ "$assume_yes" -eq 1 ]; then return; fi
    if [ ! -t 0 ]; then
        echo "devprep: prerequisite installation requires --yes without a terminal." >&2
        exit 2
    fi
    printf '%s' "devprep needs $1. Install the prerequisite? [Y/n] "
    read -r answer
    case "$answer" in ''|y|Y|yes|YES) ;; *) exit 0 ;; esac
}

as_root() {
    if [ "$(id -u)" -eq 0 ]; then "$@"
    elif command -v sudo >/dev/null 2>&1; then sudo "$@"
    elif command -v doas >/dev/null 2>&1; then doas "$@"
    else echo 'devprep: installing Python needs root, sudo, or doas.' >&2; exit 2
    fi
}

# Homebrew installations are often not on a fresh shell's PATH yet.
if [ "$(uname -s)" = Darwin ]; then
    for prefix in /opt/homebrew /usr/local; do
        if [ -x "$prefix/bin/brew" ]; then export PATH="$prefix/bin:$PATH"; break; fi
    done
    if ! command -v brew >/dev/null 2>&1 && [ "$preview" -eq 0 ]; then
        confirm_bootstrap 'Homebrew (including Apple Command Line Tools when required)'
        bootstrap_file=$(mktemp)
        trap 'rm -f "$bootstrap_file"' EXIT HUP INT TERM
        curl --fail --silent --show-error --location https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$bootstrap_file"
        if [ "$assume_yes" -eq 1 ]; then NONINTERACTIVE=1 /bin/bash "$bootstrap_file"
        else /bin/bash "$bootstrap_file"; fi
        rm -f "$bootstrap_file"
        trap - EXIT HUP INT TERM
        for prefix in /opt/homebrew /usr/local; do
            if [ -x "$prefix/bin/brew" ]; then export PATH="$prefix/bin:$PATH"; break; fi
        done
    fi
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
    if [ "$preview" -eq 1 ]; then
        echo 'devprep: Python 3.9+ is required to preview. Nothing was installed.' >&2
        exit 2
    fi
    if [ -e /run/ostree-booted ] || [ -x /sbin/transactional-update ]; then
        echo 'devprep: use a writable Toolbox/Distrobox development container on immutable Linux.' >&2
        exit 2
    fi
    confirm_bootstrap 'Python 3.9+'
    if [ "$(uname -s)" = Darwin ]; then brew install python
    elif command -v apt-get >/dev/null 2>&1; then as_root apt-get update; as_root apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then as_root dnf install -y python3
    elif command -v yum >/dev/null 2>&1; then as_root yum install -y python3
    elif command -v pacman >/dev/null 2>&1; then as_root pacman -Syu --needed --noconfirm python
    elif command -v zypper >/dev/null 2>&1; then as_root zypper --non-interactive install python3
    elif command -v apk >/dev/null 2>&1; then as_root apk add python3
    elif command -v xbps-install >/dev/null 2>&1; then as_root xbps-install -Sy python3
    elif command -v emerge >/dev/null 2>&1; then as_root emerge --noreplace dev-lang/python
    elif command -v nix >/dev/null 2>&1; then
        exec nix --extra-experimental-features 'nix-command flakes' shell nixpkgs#python3 --command python3 -m devprep "$@"
    else echo 'devprep: install Python 3.9+ using your package manager, then rerun.' >&2; exit 2
    fi
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else "devprep requires Python 3.9+")'
exec python3 -m devprep "$@"
