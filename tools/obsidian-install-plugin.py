#!/usr/bin/env python3
"""Install an Obsidian plugin into one or more vaults, from a GitHub repo or a zip.

    obsidian-install-plugin.py first-digital-finance/obsidian-openapi-renderer --yes

Works with any plugin that publishes main.js / manifest.json (/ styles.css) as
GitHub release assets, or ships a zip of those files. Stdlib only - no pip, no jq.

SOURCE may be:
    owner/repo                latest GitHub release
    owner/repo@4.5.2          a specific release tag
    https://host/thing.zip    a zip containing the plugin files
    ./thing.zip               a local zip
    ./some-dir               a local directory holding manifest.json

Vaults are discovered from Obsidian's own registry, so you never type paths.
Existing data.json (your plugin settings) is never touched.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

WANTED = ("main.js", "manifest.json", "styles.css")  # styles.css is optional
UA = {"User-Agent": "obsidian-install-plugin"}


def die(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def note(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# vault discovery
# --------------------------------------------------------------------------- #

def registry_paths() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Library/Application Support/obsidian/obsidian.json",       # macOS
        home / ".config/obsidian/obsidian.json",                           # Linux
        home / ".var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json",  # Flatpak
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "obsidian/obsidian.json")        # Windows
    return [p for p in candidates if p.is_file()]


def discover_vaults() -> list[Path]:
    found: list[Path] = []
    for reg in registry_paths():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            note(f"warning: could not read {reg}: {exc}")
            continue
        for entry in (data.get("vaults") or {}).values():
            path = entry.get("path")
            if path and Path(path).is_dir() and Path(path) not in found:
                found.append(Path(path))
    return found


# --------------------------------------------------------------------------- #
# fetching the plugin payload
# --------------------------------------------------------------------------- #

def http_get(url: str, label: str | None = None) -> bytes:
    """Fetch a URL. With a label, report progress - main.js is ~2.8 MB and the
    wait is long enough to look like a hang if nothing is printed."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            if label is None:
                return resp.read()
            total = int(resp.headers.get("Content-Length") or 0)
            live = sys.stdout.isatty()
            chunks: list[bytes] = []
            got = 0
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
                got += len(chunk)
                if live:
                    of = f"/{total:,}" if total else ""
                    pct = f" ({got * 100 // total}%)" if total else ""
                    print(f"\r  {label}: {got:,}{of} bytes{pct}   ", end="", flush=True)
            if live:
                print("\r" + " " * 64 + "\r", end="")
            print(f"  {label}: {got:,} bytes", flush=True)
            return b"".join(chunks)
    except urllib.error.HTTPError as exc:
        die(f"{url} returned HTTP {exc.code} {exc.reason}")
    except urllib.error.URLError as exc:
        die(f"could not reach {url}: {exc.reason}")


def files_from_zip(blob: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        manifests = [n for n in names if Path(n).name == "manifest.json"]
        if not manifests:
            die("zip contains no manifest.json")
        # shallowest manifest.json wins; take everything beside it
        root = min(manifests, key=lambda n: n.count("/"))
        prefix = root[: -len("manifest.json")]
        out: dict[str, bytes] = {}
        for name in names:
            if name.startswith(prefix) and "/" not in name[len(prefix):]:
                out[name[len(prefix):]] = zf.read(name)
    return out


def files_from_github(repo: str, tag: str | None, manifest_only: bool = False) -> dict[str, bytes]:
    api = f"https://api.github.com/repos/{repo}/releases/"
    api += f"tags/{tag}" if tag else "latest"
    try:
        release = json.loads(http_get(api))
    except json.JSONDecodeError:
        die(f"unexpected response from {api}")
    resolved = release.get("tag_name", "?")
    assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    note(f"  release {resolved}: {', '.join(sorted(assets)) or '(no assets)'}")

    if "manifest.json" in assets:
        # smallest first: two instant lines before the multi-megabyte main.js
        names = ("manifest.json",) if manifest_only else ("manifest.json", "styles.css", "main.js")
        return {n: http_get(assets[n], label=n) for n in names if n in assets}

    zips = [n for n in assets if n.endswith(".zip")]
    if zips:
        return files_from_zip(http_get(assets[zips[0]], label=zips[0]))

    die(f"release {resolved} of {repo} has neither manifest.json nor a .zip asset")


def files_from_dir(path: Path) -> dict[str, bytes]:
    if not (path / "manifest.json").is_file():
        die(f"{path} has no manifest.json")
    return {
        name: (path / name).read_bytes()
        for name in WANTED
        if (path / name).is_file()
    }


def resolve_source(source: str, manifest_only: bool = False) -> dict[str, bytes]:
    note(f"source: {source}")
    if source.startswith(("http://", "https://")):
        if not source.endswith(".zip"):
            die("a URL source must point at a .zip")
        return files_from_zip(http_get(source, label=Path(source).name))

    local = Path(source).expanduser()
    if local.is_dir():
        return files_from_dir(local)
    if local.is_file():
        return files_from_zip(local.read_bytes())

    if source.count("/") == 1 and " " not in source:
        repo, _, tag = source.partition("@")
        return files_from_github(repo, tag or None, manifest_only)

    die(f"cannot interpret source {source!r}")


# --------------------------------------------------------------------------- #
# install
# --------------------------------------------------------------------------- #

def installed_version(vault: Path, plugin_id: str) -> str | None:
    manifest = vault / ".obsidian/plugins" / plugin_id / "manifest.json"
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, json.JSONDecodeError):
        return None


def write_atomic(target: Path, blob: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=f".{target.name}.")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def enable_plugin(vault: Path, plugin_id: str, dry_run: bool) -> str:
    cfg = vault / ".obsidian/community-plugins.json"
    try:
        enabled = json.loads(cfg.read_text(encoding="utf-8"))
        if not isinstance(enabled, list):
            raise ValueError
    except (OSError, json.JSONDecodeError, ValueError):
        enabled = []
    if plugin_id in enabled:
        return "already enabled"
    if dry_run:
        return "would enable"
    enabled.append(plugin_id)
    write_atomic(cfg, (json.dumps(enabled, indent=2) + "\n").encode("utf-8"))
    return "enabled"


def install(vault: Path, plugin_id: str, files: dict[str, bytes], dry_run: bool) -> None:
    dest = vault / ".obsidian/plugins" / plugin_id
    for name, blob in sorted(files.items()):
        if dry_run:
            print(f"      would write {name} ({len(blob):,} bytes)")
        else:
            write_atomic(dest / name, blob)
            print(f"      wrote {name} ({len(blob):,} bytes)")


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Install an Obsidian plugin into one or more vaults.",
        epilog="example: %(prog)s first-digital-finance/obsidian-openapi-renderer --yes",
    )
    ap.add_argument("source", nargs="?", help="owner/repo[@tag], zip URL, local zip, or directory")
    ap.add_argument("--vault", action="append", metavar="PATH", default=[],
                    help="target this vault (repeatable); default is every vault Obsidian knows")
    ap.add_argument("--only-upgrade", action="store_true",
                    help="skip vaults that do not already have this plugin")
    ap.add_argument("--list", action="store_true", help="show vaults and versions, change nothing")
    ap.add_argument("--dry-run", action="store_true", help="report what would change")
    ap.add_argument("--no-enable", action="store_true",
                    help="do not add the plugin to community-plugins.json")
    ap.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    args = ap.parse_args()

    if not args.source:
        ap.error("a SOURCE is required (try --help)")

    if args.vault:
        vaults = [Path(v).expanduser() for v in args.vault]
        for v in vaults:
            if not v.is_dir():
                die(f"not a directory: {v}")
    else:
        vaults = discover_vaults()
        if not vaults:
            die("no vaults found in Obsidian's registry; pass --vault PATH")

    files = resolve_source(args.source, manifest_only=args.list)
    if "manifest.json" not in files:
        die("no manifest.json in the resolved source")
    try:
        manifest = json.loads(files["manifest.json"])
        plugin_id = manifest["id"]
        version = manifest["version"]
    except (json.JSONDecodeError, KeyError) as exc:
        die(f"manifest.json is not a usable Obsidian manifest: {exc}")
    if "main.js" not in files and not args.list:
        die("no main.js in the resolved source - this is not an installable build")

    note(f"plugin: {manifest.get('name', plugin_id)}  id={plugin_id}  version={version}")

    rows = []
    for vault in vaults:
        have = installed_version(vault, plugin_id)
        skip = args.only_upgrade and have is None
        rows.append((vault, have, skip))

    width = max([len(str(v)) for v, _, _ in rows] + [len("vault")])
    print()
    print(f"{'vault':<{width}} {'installed':>10}   action")
    print("-" * (width + 40))
    for vault, have, skip in rows:
        if skip:
            action = "skip (--only-upgrade, not present)"
        elif have == version:
            action = f"reinstall {version}"
        elif have:
            action = f"upgrade {have} -> {version}"
        else:
            action = f"fresh install {version}"
        print(f"{str(vault):<{width}} {have or '-':>10}   {action}")
    print()

    targets = [v for v, _, skip in rows if not skip]
    if not targets:
        note("nothing to do")
        return 0

    if args.list:
        return 0

    if not args.yes and not args.dry_run:
        if not sys.stdin.isatty():  # e.g. curl ... | python3 -
            die("stdin is not a terminal, so I cannot ask: re-run with --yes (or --dry-run)")
        if input(f"install into {len(targets)} vault(s)? [y/N] ").strip().lower() not in ("y", "yes"):
            note("aborted")
            return 1

    for vault in targets:
        print(f"  {vault}")
        install(vault, plugin_id, files, args.dry_run)
        if not args.no_enable:
            print(f"      {enable_plugin(vault, plugin_id, args.dry_run)} in community-plugins.json")

    print()
    if args.dry_run:
        note("dry run - nothing was changed")
    else:
        note(f"done. In Obsidian, reload each vault (Cmd/Ctrl-R) to pick up {plugin_id} {version}.")
        note("Your plugin settings in data.json were left untouched.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
