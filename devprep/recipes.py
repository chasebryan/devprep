"""User-local environments and a verified upstream VS Code fallback."""

import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


SCIENCE_PACKAGES = ["jupyterlab", "numpy", "scipy", "pandas", "matplotlib", "sympy",
                    "scikit-learn", "pytest", "ruff"]
CODE_ARCHES = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64",
               "armv7l": "armhf"}


def data_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "devprep"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "devprep"


def notebook_python():
    return data_dir() / "notebooks" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def recipe_for(tool, host):
    if tool.get("recipe"):
        return tool["recipe"]
    if host.manager in tool.get("fallbacks", {}):
        return tool["fallbacks"][host.manager]
    if (tool["id"] == "vscode" and host.system == "linux" and host.manager not in tool["packages"]
            and host.manager != "apk" and host.arch.lower() in CODE_ARCHES):
        return "vscode"
    return None


def recipe_description(recipe, host):
    if recipe == "notebooks":
        return "Create isolated Python environment in " + str(data_dir() / "notebooks") + "; install " + ", ".join(SCIENCE_PACKAGES)
    if recipe == "pipx":
        return "Install pipx in an isolated Python environment under " + str(data_dir() / "pipx")
    if recipe in {"maven", "gradle", "composer"}:
        return "Download " + recipe + " from its official publisher, verify its checksum, and install under " + str(data_dir() / recipe)
    return ("Download stable VS Code from update.code.visualstudio.com, verify SHA-256, "
            "install in " + str(data_dir() / "vscode") + "; create ~/.local/bin/code")


def install_notebooks(run):
    interpreter = notebook_python()
    if not interpreter.exists():
        if not run([sys.executable, "-m", "venv", str(interpreter.parent.parent)]):
            return False
    return run([str(interpreter), "-m", "pip", "install"] + SCIENCE_PACKAGES)


def read_url(url):
    if not url.startswith("https://"):
        raise ValueError("Downloads must use HTTPS")
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def download_verified(url, path, checksum, algorithm="sha256"):
    if not url.startswith("https://"):
        raise ValueError("Downloads must use HTTPS")
    digest = hashlib.new(algorithm)
    with urllib.request.urlopen(url, timeout=60) as response, path.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest().lower() != checksum.strip().lower():
        raise ValueError("Download checksum verification failed: " + url)


def validate_zip(archive):
    for item in archive.infolist():
        path = PurePosixPath(item.filename.replace("\\", "/"))
        if (path.is_absolute() or ".." in path.parts or ":" in item.filename or
                (item.external_attr >> 16) & 0o170000 == 0o120000):
            raise ValueError("Unsafe archive entry: " + item.filename)


def install_java_tool(name):
    target = data_dir() / name
    launcher = "mvn.cmd" if name == "maven" else "gradle.bat"
    if (target / "bin" / launcher).exists():
        print("  PATH: " + str(target / "bin"))
        return True
    if target.exists():
        raise ValueError("Installation destination already exists: " + str(target))
    if name == "maven":
        base = "https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/"
        metadata = ET.fromstring(read_url(base + "maven-metadata.xml"))
        versions = [v.text for v in metadata.findall("./versioning/versions/version")
                    if re.fullmatch(r"3\.\d+\.\d+", v.text or "")]
        version = max(versions, key=lambda v: tuple(map(int, v.split("."))))
        url = base + version + "/apache-maven-" + version + "-bin.zip"
        checksum = read_url(url + ".sha512").decode().split()[0]
        algorithm = "sha512"
    else:
        metadata = json.loads(read_url("https://services.gradle.org/versions/current"))
        url, checksum = metadata["downloadUrl"], metadata["checksum"]
        algorithm = "sha256"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=name + "-", dir=target.parent) as temporary:
        archive_path = Path(temporary) / "download.zip"
        download_verified(url, archive_path, checksum, algorithm)
        extracted = Path(temporary) / "extracted"
        with zipfile.ZipFile(archive_path) as archive:
            validate_zip(archive)
            archive.extractall(extracted)
        roots = list(extracted.iterdir())
        if len(roots) != 1 or not (roots[0] / "bin" / launcher).is_file():
            raise ValueError("Unexpected " + name + " archive layout")
        shutil.move(str(roots[0]), target)
    print("  PATH: " + str(target / "bin"))
    return True


def install_composer(run):
    target = data_dir() / "composer"
    if not shutil.which("php"):
        raise ValueError("PHP is not on PATH yet. Open a new terminal and rerun --tools composer.")
    target.mkdir(parents=True, exist_ok=True)
    if not (target / "composer.phar").exists():
        with tempfile.TemporaryDirectory(prefix="composer-") as temporary:
            installer = Path(temporary) / "composer-setup.php"
            checksum = read_url("https://composer.github.io/installer.sig").decode().strip()
            download_verified("https://getcomposer.org/installer", installer, checksum, "sha384")
            if not run(["php", str(installer), "--install-dir=" + str(target), "--filename=composer.phar"]):
                return False
    launcher = target / "composer.cmd"
    launcher.write_text('@php "%~dp0composer.phar" %*\r\n', encoding="utf-8")
    print("  PATH: " + str(target))
    return True


def install_pipx(run):
    target = data_dir() / "pipx"
    interpreter = target / "Scripts/python.exe"
    if not interpreter.exists() and not run([sys.executable, "-m", "venv", str(target)]):
        return False
    result = run([str(interpreter), "-m", "pip", "install", "pipx"])
    print("  PATH: " + str(interpreter.parent))
    return result


def validate_archive(archive):
    """Reject traversal, links and devices before extracting upstream data."""
    for member in archive.getmembers():
        path = PurePosixPath(member.name.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or ":" in member.name or not (member.isfile() or member.isdir()):
            raise ValueError("Unsafe VS Code archive entry: " + member.name)


def install_vscode(host):
    target = data_dir() / "vscode"
    launcher = Path.home() / ".local/bin/code"
    if (target / "bin/code").is_file() and launcher.is_symlink() and launcher.resolve() == (target / "bin/code").resolve():
        return True
    if target.exists() or launcher.exists() or launcher.is_symlink():
        raise ValueError("VS Code destination already exists; preserve it and use its existing launcher: " + str(target))
    url = "https://update.code.visualstudio.com/api/update/linux-" + CODE_ARCHES[host.arch.lower()] + "/stable/latest"
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    download_url = metadata["url"]
    if not download_url.startswith("https://"):
        raise ValueError("VS Code download must use HTTPS")
    expected_hash = metadata["sha256hash"]
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vscode-", dir=target.parent) as temp:
        archive_path = Path(temp) / "code.tar.gz"
        digest = hashlib.sha256()
        with urllib.request.urlopen(download_url, timeout=60) as response, archive_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected_hash:
            raise ValueError("VS Code SHA-256 verification failed")
        extracted = Path(temp) / "extracted"
        with tarfile.open(archive_path, "r:gz") as archive:
            validate_archive(archive)
            archive.extractall(extracted)
        roots = list(extracted.iterdir())
        if len(roots) != 1 or not (roots[0] / "bin/code").is_file():
            raise ValueError("Unexpected VS Code archive layout")
        launcher.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(roots[0]), target)
        try:
            launcher.symlink_to(target / "bin/code")
        except OSError:
            shutil.rmtree(target)
            raise
    return True
