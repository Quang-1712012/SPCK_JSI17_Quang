#!/usr/bin/env python3
"""Sync MineOS data from PrismarineJS and fetch assets as one ZIP archive.

Run from the MineOS project root:
    python scripts/sync_prismarine_data.py

Assets are downloaded as one GitHub source archive, then only the selected
Minecraft version folder is extracted. This avoids thousands of HTTPS requests.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from socket import timeout as SocketTimeout

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ASSET_OUT = ROOT / "assets" / "minecraft-assets"
VERSION = "1.21.11"
DATA_REPO = "PrismarineJS/minecraft-data"
ASSET_REPO = "PrismarineJS/minecraft-assets"
USER_AGENT = "MineOS-Prismarine-Data-Sync/2.0"

FILES = {
    "biomes.js": ("biomes", "biomes.json"),
    "blocks.js": ("blocks", "blocks.json"),
    "items.js": ("items", "items.json"),
    "mobs.js": ("mobs", "entities.json"),
    "recipes.js": ("recipes", "recipes.json"),
    "enchantments.js": ("enchantments", "enchantments.json"),
    "effects.js": ("effects", "effects.json"),
}


def request(url: str, timeout: int = 60):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url: str):
    with request(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_bytes(url: str, attempts: int = 4) -> bytes:
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with request(url, timeout=60) as response:
                return response.read()
        except (urllib.error.HTTPError, URLError, SocketTimeout, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < attempts:
                delay = min(2 ** attempt, 15)
                print(f"    retry {attempt}/{attempts - 1} in {delay}s: {exc}")
                time.sleep(delay)
    raise RuntimeError(f"Could not download {url} after {attempts} attempts: {last_error}")


def write_js(filename: str, export_name: str, value, version: str, source_path: str):
    DATA.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    text = (
        f"// Source: https://github.com/{DATA_REPO}/blob/master/{source_path}\n"
        f"// Minecraft Java Edition data version: {version}\n"
        "// Generated automatically. Do not edit by hand.\n"
        f"export const {export_name} = {payload};\n"
        f"export const sourceStatus = {{ available: true, version: {json.dumps(version)}, source: {json.dumps(DATA_REPO)} }};\n"
        f"export default {export_name};\n"
    )
    (DATA / filename).write_text(text, encoding="utf-8")
    count = len(value) if isinstance(value, (list, dict)) else 1
    print(f"[OK] {filename}: {count} records")


def sync_data():
    print(f"Fetching {DATA_REPO} repository tree...")
    tree = get_json(f"https://api.github.com/repos/{DATA_REPO}/git/trees/master?recursive=1")
    paths = {entry["path"] for entry in tree.get("tree", []) if entry.get("type") == "blob"}
    base = f"data/pc/{VERSION}/"
    if not any(path.startswith(base) for path in paths):
        available = sorted({p.split("/")[2] for p in paths if p.startswith("data/pc/") and len(p.split("/")) > 2})
        raise RuntimeError(
            f"Java {VERSION} folder not found in {DATA_REPO}. "
            f"Available versions include: {', '.join(available[-15:])}"
        )

    for output, (export_name, upstream_file) in FILES.items():
        source_path = base + upstream_file
        if source_path not in paths:
            print(f"[SKIP] {source_path} is not present upstream")
            continue
        raw_url = f"https://raw.githubusercontent.com/{DATA_REPO}/master/{source_path}"
        value = json.loads(get_bytes(raw_url).decode("utf-8"))
        write_js(output, export_name, value, VERSION, source_path)
        time.sleep(0.1)


def choose_asset_version():
    tree = get_json(f"https://api.github.com/repos/{ASSET_REPO}/git/trees/master?recursive=1")
    paths = [entry["path"] for entry in tree.get("tree", []) if entry.get("type") == "blob"]
    versions = sorted({
        p.split("/")[1]
        for p in paths
        if p.startswith("data/") and len(p.split("/")) > 2 and p.split("/")[1][:1].isdigit()
    })
    if VERSION in versions:
        return VERSION
    if not versions:
        raise RuntimeError("No versioned asset folders were found in minecraft-assets.")
    # Use the closest available 1.21.x snapshot rather than silently selecting a newer major line.
    compatible = [v for v in versions if v.startswith("1.21.")]
    return compatible[-1] if compatible else versions[-1]


def download_archive(url: str, destination: Path, attempts: int = 4):
    """Download one repository ZIP. A failed partial file is discarded and retried."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            if destination.exists():
                destination.unlink()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as output:
                total = int(response.headers.get("Content-Length", "0") or 0)
                received = 0
                last_report = -1
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    received += len(chunk)
                    mb = received // (5 * 1024 * 1024)
                    if mb != last_report:
                        if total:
                            print(f"  archive downloaded: {received / 1048576:.1f}/{total / 1048576:.1f} MB")
                        else:
                            print(f"  archive downloaded: {received / 1048576:.1f} MB")
                        last_report = mb
            if destination.stat().st_size < 1024:
                raise RuntimeError("Downloaded archive is unexpectedly small.")
            return
        except (urllib.error.HTTPError, URLError, SocketTimeout, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
            if destination.exists():
                destination.unlink()
            if attempt < attempts:
                delay = min(2 ** attempt, 20)
                print(f"  archive retry {attempt}/{attempts - 1} in {delay}s: {exc}")
                time.sleep(delay)
    raise RuntimeError(f"Asset ZIP download failed after {attempts} attempts: {last_error}")


def extract_selected_assets(archive_path: Path, version: str):
    """Extract only data/<version>/ from the ZIP; keep the upstream subfolder layout."""
    prefix_suffix = f"/data/{version}/"
    out = ASSET_OUT / version
    extracted = 0
    total_bytes = 0
    out.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as archive:
        members = [name for name in archive.namelist() if prefix_suffix in name and not name.endswith("/")]
        if not members:
            raise RuntimeError(f"Archive does not contain data/{version}/")
        print(f"Extracting {len(members)} asset files for Minecraft {version}...")
        for index, member in enumerate(members, 1):
            pos = member.find(prefix_suffix)
            relative = PurePosixPath(member[pos + len(prefix_suffix):])
            if not relative.parts or any(part in ("..", "") for part in relative.parts):
                continue
            target = out.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, target.open("wb") as destination:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    destination.write(chunk)
                    total_bytes += len(chunk)
            extracted += 1
            if index % 500 == 0 or index == len(members):
                print(f"  extracted {index}/{len(members)} files")

    print(f"[OK] Assets {version}: {extracted} files, {total_bytes / 1048576:.1f} MB extracted")


def sync_assets():
    print(f"Checking compatible asset snapshot in {ASSET_REPO}...")
    asset_version = choose_asset_version()
    print(f"[INFO] Selected asset version: {asset_version}")
    if asset_version != VERSION:
        print(f"[NOTE] MineOS data target is {VERSION}, but this repository snapshot is {asset_version}.")

    archive_url = f"https://codeload.github.com/{ASSET_REPO}/zip/refs/heads/master"
    with tempfile.TemporaryDirectory(prefix="mineos_assets_") as temp_dir:
        archive_path = Path(temp_dir) / "minecraft-assets-master.zip"
        print("Downloading minecraft-assets as ONE ZIP archive (instead of thousands of individual requests)...")
        download_archive(archive_url, archive_path)
        extract_selected_assets(archive_path, asset_version)


def mark_unavailable_files():
    unavailable = {
        "structures.js": ("structures", "The selected PrismarineJS repositories do not provide a complete world-generation structure registry."),
        "loot_tables.js": ("lootTables", "The selected PrismarineJS repositories do not provide a complete loot-table registry."),
        "advancements.js": ("advancements", "The selected PrismarineJS repositories do not provide a complete advancements registry."),
    }
    for filename, (name, reason) in unavailable.items():
        path = DATA / filename
        if not path.exists():
            path.write_text(
                "// No upstream dataset found; no records are fabricated.\n"
                f"export const {name} = [];\n"
                f"export const sourceStatus = {{ available: false, reason: {json.dumps(reason)}, targetVersion: {json.dumps(VERSION)} }};\n"
                f"export default {name};\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    try:
        sync_data()
        sync_assets()
        mark_unavailable_files()
        print("\nMineOS data sync finished. Verify asset version and sourceStatus before integrating.")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"GitHub HTTP error: {exc}. Check connection or API limits.")
    except KeyboardInterrupt:
        raise SystemExit("\nStopped by user. Run the script again to retry the sync.")
    except Exception as exc:
        raise SystemExit(f"Sync failed: {exc}")
