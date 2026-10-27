import re
import subprocess

from core.paths import ROOT

SECRET = re.compile(r"(gsk_[A-Za-z0-9]{20,}|sk-(ant-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,})")


def test_no_api_keys_in_files_git_would_commit():
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split()
    leaks = []
    for name in files:
        path = ROOT / name
        if path.suffix in {".png", ".pdf", ".zip", ".npy"} or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET.search(text):
            leaks.append(name)
    assert leaks == [], f"possible API keys in: {leaks}"
