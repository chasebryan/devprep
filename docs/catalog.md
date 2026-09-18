# Catalog mappings

Generated from `devprep/catalog.json` by `python scripts/update_catalog_docs.py`.

`native` = mapped package(s); `recipe` = maintained user-local installer; `included` = bundled with another selected tool; `n/a` = platform does not apply; `—` = no maintained mapping.

A native mapping is a candidate package name, not a guarantee for every OS release or configured repository. Download recipes also depend on upstream platform requirements. Linux previews use x86_64; architecture restrictions still apply.

| Tool | apt | dnf | yum | pacman | zypper | apk | xbps | emerge | nix | brew | winget |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `git` | native | native | native | native | native | native | native | native | native | native | native |
| `git-lfs` | native | native | native | native | native | native | native | native | native | native | native |
| `github-cli` | native | native | native | native | native | native | native | native | native | native | native |
| `curl` | native | native | native | native | native | native | native | native | native | native | native |
| `wget` | native | native | native | native | native | native | native | native | native | native | native |
| `jq` | native | native | native | native | native | native | native | native | native | native | native |
| `ripgrep` | native | native | native | native | native | native | native | native | native | native | native |
| `fd` | native | native | native | native | native | native | native | native | native | native | native |
| `fzf` | native | native | native | native | native | native | native | native | native | native | native |
| `bat` | native | native | native | native | native | native | native | native | native | native | native |
| `tmux` | native | native | native | native | native | native | native | native | native | native | n/a |
| `direnv` | native | native | native | native | native | native | native | native | native | native | native |
| `shellcheck` | native | native | native | native | native | native | native | native | native | native | native |
| `build-tools` | native | native | native | native | native | native | native | native | native | native | native |
| `cmake` | native | native | native | native | native | native | native | native | native | native | native |
| `ninja` | native | native | native | native | native | native | native | native | native | native | native |
| `llvm` | native | native | native | native | native | native | native | native | native | native | native |
| `debugger` | native | native | native | native | native | native | native | native | native | native | n/a |
| `python` | native | native | native | native | native | native | native | native | native | native | native |
| `pipx` | native | native | native | native | native | native | native | native | native | native | recipe |
| `node` | native | native | native | native | native | native | native | native | native | native | native |
| `go` | native | native | native | native | native | native | native | native | native | native | native |
| `rust` | native | native | native | native | native | native | native | native | native | native | native |
| `java` | native | native | native | native | native | native | native | native | native | native | native |
| `maven` | native | native | native | native | native | native | native | native | native | native | recipe |
| `gradle` | native | native | native | native | native | native | native | native | native | native | recipe |
| `dotnet` | native | native | native | native | native | native | — | native | native | native | native |
| `ruby` | native | native | native | native | native | native | native | native | native | native | native |
| `php` | native | native | native | native | native | native | native | native | native | native | native |
| `composer` | native | native | native | native | native | native | native | native | native | native | recipe |
| `lua` | native | native | native | native | native | native | native | native | native | native | native |
| `neovim` | native | native | native | native | native | native | native | native | native | native | native |
| `vscode` | recipe | recipe | recipe | native | recipe | — | recipe | native | native | native | native |
| `docker` | native | native | native | native | native | native | native | native | native | native | native |
| `compose` | native | native | native | native | native | native | native | native | native | included | included |
| `podman` | native | native | native | native | native | native | native | native | native | native | native |
| `kubectl` | native | native | native | native | native | native | native | native | native | native | native |
| `helm` | — | native | native | native | native | native | native | native | native | native | native |
| `sqlite` | native | native | native | native | native | native | native | native | native | native | native |
| `postgresql` | native | native | native | native | native | native | native | native | native | native | native |
| `redis` | native | native | native | native | native | native | native | native | native | native | n/a |
| `dbeaver` | — | — | — | native | — | — | — | native | native | native | native |
| `aws` | native | native | native | native | native | native | native | native | native | native | native |
| `opentofu` | — | — | — | native | — | native | — | native | native | native | native |
| `ansible` | native | native | native | native | native | native | native | native | native | native | n/a |
| `r` | native | native | native | native | native | native | native | native | native | native | native |
| `julia` | — | — | — | native | native | — | native | native | native | native | native |
| `octave` | native | native | native | native | native | native | native | native | native | native | native |
| `graphviz` | native | native | native | native | native | native | native | native | native | native | native |
| `pandoc` | native | native | native | native | native | native | native | native | native | native | native |
| `notebooks` | recipe | recipe | recipe | recipe | recipe | recipe | recipe | recipe | recipe | recipe | recipe |
