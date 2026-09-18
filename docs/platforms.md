# Platform behavior and support boundaries

Family detection reads `ID` and `ID_LIKE` from `/etc/os-release`; it never executes that file. WSL is detected as its Linux distribution. Package-manager selection follows the distro identity rather than whichever unrelated package-manager binary happens to be on PATH.

| Adapter | Important details |
| --- | --- |
| APT | Uses existing signed repositories. Debian/Ubuntu releases differ: .NET, Compose v2, Kubernetes, Helm, Julia, and GUI database tools are not uniformly packaged. Missing packages return failures with the native diagnostic. Ubuntu universe or vendor repositories may need to be enabled by the operator. |
| DNF / YUM | Enterprise variants often need EPEL/CRB or vendor repositories for developer tools. devprep does not silently enable those repositories. Older YUM distributions may not provide the required Python 3.9+. |
| Pacman | Refresh is a full system upgrade. Uses repository packages and Code OSS; never installs an AUR helper or executes AUR build scripts. |
| Zypper | Uses enabled repositories and a noninteractive install. Leap, Tumbleweed, and SLE do not have identical package catalogs. Transactional hosts must use a development container. |
| APK | Python, Java, editors, and other tools can require the community repository. No glibc-only VS Code tarball. Scientific wheels may be unavailable on musl and may build from source; additional BLAS/Fortran dependencies may be necessary. |
| XBPS | Uses existing repository configuration. The user may need to update XBPS itself before a package transaction. |
| emerge | Syncs the configured repositories and uses `--noreplace`. Respects existing USE flags, masks, and license settings. Source builds can take hours; package configuration changes are left to the user. |
| Nix | Adds packages to the current user's profile using the `nixpkgs` flake registry, with `nix-command` and `flakes` enabled per invocation. Does not change `configuration.nix`, services, or user-wide Nix settings. Unfree VS Code needs an appropriate user configuration. Profile name/file collisions remain native Nix errors. |
| Homebrew | Standard `/opt/homebrew` and `/usr/local` installations are detected. Follow Homebrew's supported OS/hardware requirements. Bootstrap can install Apple Command Line Tools. Uses native casks for VS Code, Docker Desktop, DBeaver, and Julia. |
| WinGet | Requires Microsoft App Installer. Installs exact IDs from the community source. Visual Studio Build Tools requests the C++ workload on fresh installs. Existing Visual Studio installations may need that workload added in Visual Studio Installer. UAC, platform requirements, or pending reboots can still require interaction. |

## What is automatic and what needs activation

devprep installs tools. It does not invent Git identity, cloud credentials, SSH keys, database passwords, or organization settings.

- Docker Desktop: start the application and finish its initialization. Review its licensing for your use. Windows may require WSL2, virtualization, and a reboot. On Linux, enable the daemon using the distro's init system and choose an appropriate access policy.
- Podman on Windows/macOS: initialize and start a Podman machine. On Linux, rootless use may require subordinate UID/GID configuration supplied by your distribution.
- PostgreSQL: initialize the cluster if required by the package and configure authentication. Native installers may start services automatically. Redis and Ansible are Unix tools; run them in WSL when using Windows.
- Homebrew Java: consult `brew info openjdk` for `JAVA_HOME` and system Java registration. GDB on macOS requires code signing; LLVM includes LLDB as an alternative.
- Windows Maven/Gradle/Composer/pipx: add the printed installation directories to the user PATH. Native installer PATH changes are picked up in the devprep process after each successful command; open a new terminal for your shell.
- VS Code on Linux: the verified archive fallback installs per-user without modifying package repositories. It leaves an existing installation in place and does not auto-upgrade it on reruns. Package-managed editions retain native update behavior. Required desktop libraries must be installed by the distribution.
- Python science: the isolated environment uses the Python interpreter running devprep. PyPI resolves compatible package versions. This is a convenience environment, not a project dependency lockfile. Launch through `--launch-notebooks` or its environment's Python.

## Testing status

Unit tests cover every adapter's plan construction, distro detection, selection/dependency behavior, command failures, reports, and archive validation. The CI workflow runs those tests and plan previews on Linux, macOS, and Windows with Python 3.9 and 3.14. Its disposable-container smoke jobs bootstrap and install Git/CMake on Debian, Ubuntu, Fedora, Arch, Alpine, and openSUSE, then repeat the selection.

These checks do not provision a complete GUI workstation. Windows/macOS installs, uncommon architectures, enterprise repositories, Gentoo/Void/Nix end-to-end setup, and the complete catalog still require native-machine acceptance testing. Do not promote a package mapping to certified support solely because a dry run passes.

## Primary references

- [Homebrew installation](https://docs.brew.sh/Installation)
- [WinGet install behavior and options](https://learn.microsoft.com/windows/package-manager/winget/install)
- [WinGet manifests](https://github.com/microsoft/winget-pkgs)
- [Pacman manual](https://man.archlinux.org/man/pacman.8.en)
- [Void XBPS handbook](https://docs.voidlinux.org/xbps/index.html)
- [Gentoo Portage handbook](https://wiki.gentoo.org/wiki/Handbook:AMD64/Working/Portage)
- [Nix user profiles](https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-profile.html)
- [VS Code Linux setup](https://code.visualstudio.com/docs/setup/linux)
