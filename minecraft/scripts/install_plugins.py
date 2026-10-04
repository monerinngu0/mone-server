#!/usr/bin/env python3
from pathlib import Path
import sys
import urllib.request
import yaml

CONFIG = Path("/plugins.yml")
PLUGIN_DIR = Path("/data/plugins")


def download(url: str, out: Path):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "minecraft-plugin-installer/0.1"
        },
    )

    with urllib.request.urlopen(req, timeout=60) as res:
        data = res.read()

    out.write_bytes(data)


def main():
    if not CONFIG.exists():
        print(f"[ERROR] {CONFIG} がありません")
        sys.exit(1)

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    plugins = cfg.get("plugins", [])

    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    for p in plugins:
        name = p["name"]
        file = p["file"]
        url = p["url"]

        out = PLUGIN_DIR / file

        print(f"[INFO] {name} -> {out}")

        if out.exists():
            print(f"[SKIP] already exists: {file}")
            continue

        try:
            download(url, out)
            print(f"[OK] downloaded: {file}")
        except Exception as e:
            print(f"[ERROR] failed: {name}")
            print(e)

    print("[DONE]")


if __name__ == "__main__":
    main()
