from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import SiesPbipError, bundle, capture, doctor, find_root, init_sies, load_config, materialize, prepare, validate, verify_sources


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="siespbip", description="Estándar PBIP para Matrícula y Titulados SIES")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    sources = commands.add_parser("sources")
    sources_commands = sources.add_subparsers(dest="sources_command", required=True)
    verify = sources_commands.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    materialize_parser = commands.add_parser("materialize")
    materialize_parser.add_argument("--source-root", type=Path, required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--profile", choices=["author", "public"], default="author")
    prepare_parser.add_argument("--sies-root", type=Path)
    capture_parser = commands.add_parser("capture")
    capture_mode = capture_parser.add_mutually_exclusive_group(required=True)
    capture_mode.add_argument("--check", action="store_true")
    capture_mode.add_argument("--apply", action="store_true")
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--profile", choices=["source", "runtime", "release"], default="source")
    publish = commands.add_parser("publish-data")
    publish.add_argument("--check", action="store_true", default=True)
    release = commands.add_parser("release")
    release_mode = release.add_mutually_exclusive_group(required=True)
    release_mode.add_argument("--check", action="store_true")
    release_mode.add_argument("--bundle", action="store_true")
    init = commands.add_parser("init-sies")
    init.add_argument("--name", required=True)
    init.add_argument("--slug", required=True)
    init.add_argument("--destination", type=Path, required=True)
    init.add_argument("--github-owner", default="amuletofloss")
    return result


def run(args: argparse.Namespace) -> dict:
    root = find_root()
    config = load_config(root)
    if args.command == "doctor":
        return doctor(root, config)
    if args.command == "sources":
        return verify_sources(root, config, args.root)
    if args.command == "materialize":
        return materialize(root, config, args.source_root)
    if args.command == "prepare":
        if args.profile == "public":
            raise SiesPbipError("external_mrun no ofrece refresh público; use prepare --profile author con fuentes SIES locales")
        return prepare(root, config, args.sies_root)
    if args.command == "capture":
        return capture(root, config, apply=args.apply)
    if args.command == "validate":
        return validate(root, config, args.profile)
    if args.command == "publish-data":
        result = validate(root, config, "source")
        return {"ok": result["ok"], "applied": False, "failures": result["failures"]}
    if args.command == "release":
        return bundle(root, config, check_only=args.check)
    if args.command == "init-sies":
        return init_sies(root, args.destination, args.name, args.slug, args.github_owner)
    raise SiesPbipError("Comando no implementado")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = run(args)
    except (SiesPbipError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
