# devprep

**A new machine, ready for development. Install the full toolkit by default; customize only when you want to.**

devprep prepares Linux, macOS, and Windows workstations with a curated set of tools for software development and computer science: programming languages, compilers, editors, containers, databases, infrastructure tools, and scientific computing environments.

Running devprep with no selection flags chooses **the entire catalog**. It shows the plan, then offers `Y`, `n`, or `custom`. Press Enter to install the full selection. Use `--yes` for unattended setup, or `--custom` to choose categories.

This is an initial implementation. Eleven package-manager adapters cover the major Linux families plus macOS and Windows. Package availability depends on the OS release, architecture, and enabled repositories. Known gaps are reported explicitly; the support matrix does not mean every package has been installation-tested on every distribution.

## Get started

Download and extract the [repository ZIP](https://github.com/chasebryan/devprep/archive/refs/heads/main.zip), then open a terminal in the extracted folder. If Git is already installed:

```sh
git clone https://github.com/chasebryan/devprep.git
cd devprep
```

### Linux or macOS

```sh
./install.sh
```

The launcher installs Python 3.9+ when needed. On macOS it also bootstraps Homebrew using its official installer. Run as your normal user; devprep uses `sudo` or `doas` only for system package-manager commands. Prerequisite installation has its own prompt if needed.

### Windows

In PowerShell, with [Microsoft App Installer / WinGet](https://learn.microsoft.com/windows/package-manager/winget/) available:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

The execution-policy setting applies to this invocation. The launcher installs Python if needed, then uses WinGet for native packages. Some installers may request elevation or require a reboot. Native Windows setup and Linux setup inside WSL are separate runs.

### Preview first

```sh
./install.sh --dry-run
```

Dry runs, JSON plans, help, and catalog listings never bootstrap prerequisites or run installers. They require an existing Python 3.9+ interpreter. With Python already installed, the core also runs directly with no third-party Python dependencies:

```sh
python3 -m devprep --dry-run
# Windows: py -3 -m devprep --dry-run
```

## Full and custom setup

```sh
./install.sh                                  # full catalog; review and accept
./install.sh --yes                            # full catalog, unattended
./install.sh --all --yes                      # explicit equivalent
./install.sh --custom                         # choose categories interactively
./install.sh --custom --categories core,build,languages
./install.sh --tools git,python,node,neovim --yes
./install.sh --categories core,science --exclude julia
./install.sh --list                           # all category names and tool IDs
```

The PowerShell launcher accepts the same flags. `--categories` and `--tools` imply a custom selection, and can be combined. Dependencies are included automatically: Maven includes Java, Rust includes native build tools, and notebooks include Python and build tools. An exclusion that conflicts with a required dependency is rejected before installation.

The full setup can take a long time and many gigabytes, especially with C++ tooling, containers, databases, and scientific packages. “Everything” means every tool in this maintained catalog that applies to the target platform. It does not mean every IDE, every historical runtime, or every vendor's SDK.

## What's included

| Category | Toolkit |
| --- | --- |
| `core` | Git, Git LFS, GitHub CLI, curl, wget, jq, ripgrep, fd, fzf, bat, tmux, direnv, ShellCheck |
| `build` | C/C++ toolchain and headers, Make, pkg-config, CMake, Ninja, LLVM/Clang/LLDB, GDB; Visual Studio C++ Build Tools on Windows |
| `languages` | Python/pip/venv/pipx, Node.js/npm, Go, Rust/Cargo, Java JDK, Maven, Gradle, .NET SDK, Ruby, PHP/Composer, Lua |
| `editors` | Visual Studio Code (Code OSS on Arch) and Neovim |
| `containers` | Docker Engine/Desktop, Compose, Podman, kubectl, Helm |
| `databases` | SQLite, PostgreSQL, Redis, DBeaver Community |
| `cloud` | AWS CLI, OpenTofu, Ansible |
| `science` | R, Julia, Octave, Graphviz, Pandoc, and an isolated Python notebook environment |

The notebook environment contains JupyterLab, NumPy, SciPy, pandas, matplotlib, SymPy, scikit-learn, pytest, and Ruff. It does not install into the OS-managed Python environment. Launch it with:

```sh
python3 -m devprep --launch-notebooks
```

Use project-local virtual environments, dependency lockfiles, and language version managers when a project needs specific versions. Native package versions follow the configured distribution repositories; devprep does not replace the system's language defaults with downloaded runtimes.

## Supported platforms

| Family | Adapter |
| --- | --- |
| Debian, Ubuntu, Mint, Pop!_OS, Kali, Raspberry Pi OS and derivatives | APT |
| Fedora, RHEL, Rocky, AlmaLinux, CentOS, Amazon Linux and derivatives | DNF / YUM |
| Arch, Manjaro, EndeavourOS and derivatives | Pacman |
| openSUSE, SUSE Linux Enterprise | Zypper |
| Alpine | APK |
| Void | XBPS |
| Gentoo, Funtoo | Portage / emerge |
| NixOS | Nix user profiles |
| macOS | Homebrew formulae and casks |
| Windows | WinGet, plus verified upstream archives for Maven/Gradle and the Composer installer |

See [platform details and limitations](docs/platforms.md) and the [generated catalog availability table](docs/catalog.md). Unsupported families fail with an actionable message. Fedora Atomic/Silverblue and transactional openSUSE hosts should run devprep inside a writable Toolbox or Distrobox container. Additional native families, including Slackware and Solus, need adapters; universal Linux coverage is the project's direction, not a claim of current certification.

## Installation behavior

- The plan is shown before installation. Native installers use their normal repository trust and signature checks. WinGet uses exact package IDs, skips upgrades to existing packages, and accepts package/source agreements after the plan is accepted.
- Indexes are refreshed once. **On Arch, this runs a full `pacman -Syu`** to avoid partial upgrades. Use `--no-refresh` only when the system and local indexes are already current.
- Re-running the same selection lets package managers reconcile installed packages. Selected packages may be upgraded on Linux. There is no automatic uninstall or rollback; earlier successful installs remain after an error.
- Failures do not stop unrelated tools. Failed dependencies block dependent tools. Each tool's status and each executed command's exit code are written to a JSON report.
- Exit `0` means the applicable selection completed, `1` means an installation failed, was blocked, or was unavailable, `2` means invalid input/prerequisites, and `130` means interruption. `--allow-unavailable` allows missing mappings but never hides actual installation failures.
- Native packages can enable/start services through their own installers. devprep does not add users to the Docker group, open firewall ports, initialize database passwords, or overwrite shell configuration. Container engines and databases have platform-specific next steps in the result.
- Linux VS Code fallback downloads from Microsoft's update service, verifies the published SHA-256, and creates `~/.local/bin/code`. It requires a desktop with the [upstream Linux prerequisites](https://code.visualstudio.com/docs/setup/linux). Alpine/musl and unsupported architectures do not use that glibc build.

Reports and user-local environments live under `${XDG_DATA_HOME:-~/.local/share}/devprep` on Linux/macOS, or `%LOCALAPPDATA%\devprep` on Windows. Pass `--report path/to/new-report.json` to choose another report file.

After installation, open a new terminal. Add `~/.local/bin` to PATH if your Linux distribution does not already include it. Windows archive-based tools print their installation `bin` directories; add these to your user PATH. Read the reported next steps for Java on Homebrew, direnv shell hooks, Docker/Podman, and database initialization.

## Inspect plans and contribute

```sh
python3 -m devprep --json > plan.json
python3 -m devprep --manager winget --dry-run
python3 -m devprep --manager apk --json
python3 -m unittest discover -s tests -v
```

`--manager` is only a preview override: it cannot install another platform's packages onto the current host. JSON output is also a preview. Report paths are execution-only.

The catalog is in [`devprep/catalog.json`](devprep/catalog.json). Keep new tools within the curated workstation scope, provide accurate package mappings, declare dependencies, and document any manual activation steps. Missing mappings must remain explicit. See [contributing](CONTRIBUTING.md) for architecture and validation.

Apache-2.0 licensed; see [LICENSE](LICENSE).
