from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator


CONFIG = Path("config/sies-pbip.yml")
SENTINEL = ".sies-workspace.json"
LOCAL_DIRS = {
    ".git",
    ".pbi",
    ".venv",
    ".sies-local",
    ".sies-work",
    ".pytest_cache",
    ".uv-cache",
    "dist",
    "__pycache__",
}
PERSONAL_PATH = re.compile(r"(?i)([A-Z]:[\\/](?:Users|Documents and Settings)[\\/]|/Users/|/home/)")


class SiesPbipError(RuntimeError):
    """Error controlado que debe mostrarse sin traceback desde la CLI."""


def find_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / CONFIG).is_file():
            return candidate
    raise SiesPbipError(f"No se encontró {CONFIG.as_posix()} desde {current}")


def load_config(root: Path) -> dict[str, Any]:
    payload = yaml.safe_load((root / CONFIG).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SiesPbipError("La configuración SIES no es un objeto YAML")
    schema_path = root / "schemas" / "sies-pbip.schema.json"
    if schema_path.is_file():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.path))
        if errors:
            details = "; ".join(
                f"{'.'.join(str(part) for part in error.path) or '<raíz>'}: {error.message}" for error in errors
            )
            raise SiesPbipError("Configuración fuera de esquema: " + details)
    required = {"schema_version", "project", "sies", "analysis", "artifacts", "publication"}
    missing = sorted(required - payload.keys())
    if missing:
        raise SiesPbipError("Faltan secciones de configuración: " + ", ".join(missing))
    if payload["schema_version"] != "sies-pbip/v1":
        raise SiesPbipError("schema_version debe ser sies-pbip/v1")
    identity = payload["sies"]["identity"]
    if identity != {"field": "MRUN", "type": "string", "rut_forbidden": True}:
        raise SiesPbipError("SIES PBIP exige MRUN textual y prohíbe RUT")
    publication = payload["publication"]
    if publication["mode"] != "external_mrun" or publication["minimum_cell_size"] != 10:
        raise SiesPbipError("v1 exige external_mrun y umbral público 10")
    for source in ("matricula", "titulados"):
        years = payload["sies"]["sources"][source]
        if int(years["first_year"]) > int(years["last_year"]):
            raise SiesPbipError(f"Rango de años inválido para {source}")
    return payload


def inside(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise SiesPbipError(f"Ruta fuera del repositorio: {resolved}") from exc
    if ".git" in relative.parts:
        raise SiesPbipError("Ninguna operación puede leer o escribir dentro de .git")
    cursor = resolved_root
    for part in relative.parts:
        cursor /= part
        if cursor.exists() and cursor.is_symlink():
            raise SiesPbipError(f"No se admiten symlinks en rutas operativas: {cursor}")
    return resolved


def artifact_paths(root: Path, config: dict[str, Any]) -> list[Path]:
    artifacts = config["artifacts"]
    return [inside(root, root / artifacts[name]) for name in ("pbip", "report", "semantic_model")]


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(item for item in path.rglob("*") if item.is_file())


def digest_artifacts(root: Path, config: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for artifact in artifact_paths(root, config):
        for path in iter_files(artifact):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest().upper()


def expressions_path(base: Path, config: dict[str, Any]) -> Path:
    return base / config["artifacts"]["semantic_model"] / "definition" / "expressions.tmdl"


def replace_data_path(path: Path, value: str, expected_parameter: str = "Ruta datos") -> None:
    # Leer y escribir bytes evita que Python convierta CRLF/LF en Windows. La
    # captura debe cambiar solo el parametro, no todo el archivo por sus EOL.
    source = path.read_bytes().decode("utf-8")
    escaped = value.replace('"', '""')
    pattern = rf'(?m)^(expression \'{re.escape(expected_parameter)}\'\s*=\s*")[^"]*("\s+meta\s+\[)'
    updated, count = re.subn(pattern, lambda match: match.group(1) + escaped + match.group(2), source, count=1)
    if count != 1:
        raise SiesPbipError(f"No se encontró una única expresión {expected_parameter} en {path}")
    path.write_bytes(updated.encode("utf-8"))


def doctor(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    pbips = [path for path in root.glob("*.pbip") if path.is_file()]
    if len(pbips) != 1:
        problems.append(f"se esperaba un PBIP y se encontraron {len(pbips)}")
    for path in artifact_paths(root, config):
        if not path.exists():
            problems.append(f"falta {path.relative_to(root)}")
    ignored_nested_parents = {".sies-work", ".venv", ".pytest_cache", ".uv-cache"}
    nested = [
        p
        for p in root.rglob(".git")
        if p != root / ".git"
        and not ignored_nested_parents.intersection(p.relative_to(root).parent.parts)
    ]
    if nested:
        problems.append("hay repositorios Git anidados: " + ", ".join(str(p.relative_to(root)) for p in nested))
    expression = expressions_path(root, config)
    if expression.exists() and config["artifacts"]["data_placeholder"] not in expression.read_text(encoding="utf-8"):
        problems.append("el PBIP canónico no conserva el marcador de datos")
    return {"ok": not problems, "problems": problems, "root": str(root), "version": config["project"]["version"]}


def _header(path: Path) -> list[str]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8-sig", errors="strict", newline="") as handle:
            first = handle.readline()
    except UnicodeDecodeError:
        with opener(path, "rt", encoding="latin-1", errors="strict", newline="") as handle:
            first = handle.readline()
    delimiter = ";" if first.count(";") >= first.count(",") else ","
    return [value.strip().strip('"') for value in next(csv.reader([first], delimiter=delimiter))]


def _fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").casefold()


def _source_year(path: Path) -> int | None:
    # Evita confundir fechas de publicación como 20250729 con el año del corte.
    matches = re.findall(r"(?<!\d)(20\d{2})(?!\d)", path.as_posix())
    return int(matches[-1]) if matches else None


def verify_sources(root: Path, config: dict[str, Any], source_root: Path) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    if not source_root.is_dir():
        raise SiesPbipError(f"No existe la carpeta de fuentes: {source_root}")
    checked: list[str] = []
    failures: list[str] = []
    candidates = [p for p in source_root.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".gz"}]
    for source in ("matricula", "titulados"):
        spec = config["sies"]["sources"][source]
        for year in range(int(spec["first_year"]), int(spec["last_year"]) + 1):
            matches = [p for p in candidates if _source_year(p) == year and source in _fold(p.as_posix())]
            if len(matches) != 1:
                failures.append(f"{source} {year}: se esperaba un archivo y se encontraron {len(matches)}")
                continue
            columns = {column.upper() for column in _header(matches[0])}
            if "MRUN" not in columns:
                failures.append(f"{matches[0].name}: falta MRUN")
            if "RUT" in columns:
                failures.append(f"{matches[0].name}: contiene RUT prohibido")
            checked.append(str(matches[0]))
    return {"ok": not failures, "checked": checked, "failures": failures}


def materialize(root: Path, config: dict[str, Any], source_root: Path) -> dict[str, Any]:
    verified = verify_sources(root, config, source_root)
    if not verified["ok"]:
        raise SiesPbipError("Fuentes SIES inválidas:\n" + "\n".join(verified["failures"]))
    output = inside(root, root / ".sies-local" / "derived" / config["project"]["slug"])
    output.mkdir(parents=True, exist_ok=True)
    script = root / "scripts" / "materializar_datos.py"
    subprocess.run([sys.executable, str(script), "--source-root", str(source_root), "--output", str(output)], cwd=root, check=True)
    return {"ok": True, "output": str(output), "sources": len(verified["checked"])}


def prepare(root: Path, config: dict[str, Any], data_root: Path | None = None) -> dict[str, Any]:
    slug = config["project"]["slug"]
    work = inside(root, root / ".sies-work" / slug)
    derived = (data_root or root / ".sies-local" / "derived" / slug).expanduser().resolve()
    if not derived.is_dir():
        raise SiesPbipError(f"Primero materialice los datos SIES: {derived}")
    if work.exists() and not (work / SENTINEL).is_file():
        raise SiesPbipError(f"Se rehusa reemplazar un directorio sin sentinel: {work}")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for source in artifact_paths(root, config):
        target = work / source.name
        shutil.copytree(source, target) if source.is_dir() else shutil.copy2(source, target)
    replace_data_path(expressions_path(work, config), str(derived), config["artifacts"]["data_parameter"])
    sentinel = {"schema": 1, "root": str(root), "source_fingerprint": digest_artifacts(root, config), "data_root": str(derived)}
    (work / SENTINEL).write_text(json.dumps(sentinel, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "workspace": str(work), "pbip": str(work / config["artifacts"]["pbip"])}


def _artifact_prefix(slug: str) -> str:
    normalized = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode("ascii")
    return "_".join(part.capitalize() for part in normalized.split("_") if part)


def init_sies(root: Path, destination: Path, name: str, slug: str, github_owner: str) -> dict[str, Any]:
    """Crea una copia inicial SIES sin Git, fuentes ni derivados locales."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", slug):
        raise SiesPbipError("slug debe cumplir ^[a-z][a-z0-9_]*$")
    destination = destination.expanduser().resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise SiesPbipError("El destino debe estar fuera del repositorio plantilla para evitar Git anidado")
    if destination.exists():
        raise SiesPbipError(f"El destino ya existe; no se sobrescribe: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    prefix = _artifact_prefix(slug)
    stage = Path(tempfile.mkdtemp(prefix=f".{slug}-", dir=destination.parent))
    try:
        source_config = load_config(root)
        generated_config = json.loads(json.dumps(source_config))
        generated_config["project"].update(
            {"slug": slug, "display_name": name, "version": "0.1.0", "release_status": "development"}
        )
        generated_config["analysis"]["universe_id"] = "definir_universo_sies"
        generated_config["artifacts"].update(
            {
                "pbip": f"{prefix}.pbip",
                "report": f"{prefix}.Report",
                "semantic_model": f"{prefix}.SemanticModel",
            }
        )

        artifacts = source_config["artifacts"]
        shutil.copy2(root / artifacts["pbip"], stage / generated_config["artifacts"]["pbip"])
        shutil.copytree(root / artifacts["report"], stage / generated_config["artifacts"]["report"])
        shutil.copytree(root / artifacts["semantic_model"], stage / generated_config["artifacts"]["semantic_model"])

        pbip_path = stage / generated_config["artifacts"]["pbip"]
        pbip = json.loads(pbip_path.read_text(encoding="utf-8-sig"))
        pbip["artifacts"][0]["report"]["path"] = generated_config["artifacts"]["report"]
        pbip_path.write_text(json.dumps(pbip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pbir_path = stage / generated_config["artifacts"]["report"] / "definition.pbir"
        pbir = json.loads(pbir_path.read_text(encoding="utf-8-sig"))
        pbir["datasetReference"]["byPath"]["path"] = f"../{generated_config['artifacts']['semantic_model']}"
        pbir_path.write_text(json.dumps(pbir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        for directory in (".github", "schemas", "siespbip", "scripts"):
            shutil.copytree(
                root / directory,
                stage / directory,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
            )
        (stage / ".github" / "CODEOWNERS").write_text(
            f"* @{github_owner.lstrip('@')}\n", encoding="utf-8"
        )
        (stage / "tests" / "standard").mkdir(parents=True)
        for test in (root / "tests" / "standard").glob("*.py"):
            shutil.copy2(test, stage / "tests" / "standard" / test.name)
        for filename in (
            ".gitattributes",
            ".gitignore",
            ".pbip.local.yml.example",
            "CONTRIBUTING.md",
            "LICENCIA_DATOS.md",
            "LICENSE",
            "SECURITY.md",
            "pyproject.toml",
            "uv.lock",
        ):
            shutil.copy2(root / filename, stage / filename)

        (stage / "config").mkdir()
        (stage / "config" / "sies-pbip.yml").write_text(
            yaml.safe_dump(generated_config, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        (stage / "governance").mkdir()
        publication = yaml.safe_load((root / "governance" / "data-publication.yml").read_text(encoding="utf-8"))
        publication["project"] = slug
        publication["historical_publication_review"] = {
            "status": "not_applicable",
            "scope": "proyecto nuevo sin historial",
            "action_in_v4": "no_aplica",
            "history_rewrite_authorized": False,
        }
        (stage / "governance" / "data-publication.yml").write_text(
            yaml.safe_dump(publication, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        shutil.copy2(
            root / "governance" / "desktop-validation.example.yml",
            stage / "governance" / "desktop-validation.example.yml",
        )
        (stage / "governance" / "MRUN_PUBLICATION_REVIEW.md").write_text(
            "# Revisión de publicación MRUN\n\n"
            "Estado inicial: no se han publicado microdatos desde este proyecto generado. "
            "MRUN se procesa solamente en `.sies-local/`.\n",
            encoding="utf-8",
        )
        controls = stage / "datos" / "controles_publicos"
        controls.mkdir(parents=True)
        example = controls / "ejemplo.csv"
        example.write_text("Periodo;Total\nEJEMPLO;10\n", encoding="utf-8")
        example_hash = hashlib.sha256(example.read_bytes()).hexdigest().upper()
        (stage / "datos" / "archivos_publicos.sha256").write_text(
            f"{example_hash}  controles_publicos/ejemplo.csv\n", encoding="utf-8"
        )
        for script_path in (stage / "scripts").glob("*"):
            if script_path.is_file() and script_path.suffix in {".py", ".mjs"}:
                text = script_path.read_text(encoding="utf-8")
                text = text.replace("Retencion_Academica_SIES", prefix).replace(
                    "retencion_academica_sies", slug
                )
                script_path.write_text(text, encoding="utf-8")
        (stage / "docs").mkdir()
        (stage / "docs" / "06-seguridad.md").write_text(
            "# Seguridad\n\nMRUN se procesa únicamente en `.sies-local/`; RUT está prohibido. "
            "No publique microdatos, rutas personales, secretos ni celdas entre 1 y 9.\n",
            encoding="utf-8",
        )
        (stage / "docs" / "11-checklists.md").write_text(
            "# Checklist mínimo\n\n- [ ] `pytest -q` aprobado.\n"
            "- [ ] `siespbip validate --profile source` aprobado.\n"
            "- [ ] Validación en Power BI Desktop registrada.\n"
            "- [ ] Control `EJEMPLO` reemplazado por agregados reales.\n",
            encoding="utf-8",
        )
        manifest = {
            "name": prefix,
            "version": "0.1.0",
            "status": "development",
            "standard": "sies-pbip/v1",
            "publicationMode": "external_mrun",
        }
        (stage / "pbip.manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (stage / "CHANGELOG.md").write_text(
            f"# Changelog\n\n## [0.1.0] - sin liberar\n\n- Base de {name} generada con crear_pbip_github.\n",
            encoding="utf-8",
        )
        (stage / "README.md").write_text(
            f"# {name}\n\n"
            "Proyecto PBIP generado con `crear_pbip_github` y el contrato `sies-pbip/v1`. "
            "Solo admite Matrícula y Titulados de Datos Abiertos SIES.\n\n"
            "MRUN se conserva como texto y se procesa localmente; nunca se versionan filas con MRUN ni RUT. "
            "Reemplace el control sintético `EJEMPLO` antes de liberar una versión.\n\n"
            "El reporte y modelo iniciales son una semilla funcional de retención académica. "
            "Adapte universo, transformaciones, medidas y páginas, manteniendo los gates del estándar.\n",
            encoding="utf-8",
        )
        os.replace(stage, destination)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    return {
        "ok": True,
        "destination": str(destination),
        "pbip": str(destination / generated_config["artifacts"]["pbip"]),
        "git_initialized": False,
        "next": ["revisar config/sies-pbip.yml", "reemplazar datos sintéticos", "inicializar Git cuando esté listo"],
    }


def _snapshot(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    base = path.parent if path.is_file() else path
    for file in iter_files(path):
        key = file.name if path.is_file() else file.relative_to(base).as_posix()
        result[key] = hashlib.sha256(file.read_bytes()).hexdigest()
    return result


def capture(root: Path, config: dict[str, Any], apply: bool = False) -> dict[str, Any]:
    work = inside(root, root / ".sies-work" / config["project"]["slug"])
    sentinel_path = work / SENTINEL
    if not sentinel_path.is_file():
        raise SiesPbipError("Workspace sin sentinel; ejecute prepare")
    sentinel = json.loads(sentinel_path.read_text(encoding="utf-8"))
    if Path(sentinel["root"]).resolve() != root.resolve():
        raise SiesPbipError("El workspace pertenece a otro repositorio")
    if sentinel["source_fingerprint"] != digest_artifacts(root, config):
        raise SiesPbipError("El PBIP canónico cambió después de prepare; cree otro workspace")
    stage_parent = inside(root, root / ".sies-work")
    stage = Path(tempfile.mkdtemp(prefix="capture-stage-", dir=stage_parent))
    changes: list[str] = []
    try:
        staged: list[tuple[Path, Path]] = []
        for canonical in artifact_paths(root, config):
            source = work / canonical.name
            target = stage / canonical.name
            shutil.copytree(source, target) if source.is_dir() else shutil.copy2(source, target)
            staged.append((target, canonical))
        replace_data_path(expressions_path(stage, config), config["artifacts"]["data_placeholder"], config["artifacts"]["data_parameter"])
        for staged_path, canonical in staged:
            before, after = _snapshot(canonical), _snapshot(staged_path)
            for key in sorted(set(before) | set(after)):
                if before.get(key) != after.get(key):
                    changes.append(f"{canonical.name}/{key}" if canonical.is_dir() else canonical.name)
            for file in iter_files(staged_path):
                if PERSONAL_PATH.search(file.read_text(encoding="utf-8", errors="ignore")):
                    raise SiesPbipError(f"Ruta personal detectada en {file}")
        if not apply or not changes:
            return {"ok": True, "applied": False, "changes": changes}
        backup = stage_parent / "backups" / sentinel["source_fingerprint"]
        backup.mkdir(parents=True, exist_ok=True)
        replaced: list[tuple[Path, Path]] = []
        try:
            for staged_path, canonical in staged:
                saved = backup / canonical.name
                if saved.exists():
                    shutil.rmtree(saved) if saved.is_dir() else saved.unlink()
                os.replace(canonical, saved)
                os.replace(staged_path, canonical)
                replaced.append((canonical, saved))
        except Exception:
            for canonical, saved in reversed(replaced):
                if canonical.exists():
                    shutil.rmtree(canonical) if canonical.is_dir() else canonical.unlink()
                os.replace(saved, canonical)
            raise
        return {"ok": True, "applied": True, "changes": changes, "backup": str(backup)}
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def validate_public_controls(root: Path, config: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    public = inside(root, root / config["publication"]["public_controls"])
    threshold = int(config["publication"]["minimum_cell_size"])
    if not public.is_dir():
        return [f"falta {public.relative_to(root)}"]
    count_name = re.compile(r"(?i)(base|total|conteo|personas|retenidos|numerador|cantidad)")
    for path in public.rglob("*.csv"):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            sample = handle.readline()
            delimiter = ";" if sample.count(";") >= sample.count(",") else ","
            handle.seek(0)
            for row_number, row in enumerate(csv.DictReader(handle, delimiter=delimiter), 2):
                if any(key.upper() == "MRUN" for key in row):
                    failures.append(f"{path}: columna MRUN prohibida")
                for key, value in row.items():
                    if count_name.search(key or "") and (value or "").strip().isdigit():
                        number = int(value)
                        if 0 < number < threshold:
                            failures.append(f"{path}:{row_number} {key}={number} viola umbral {threshold}")
    return failures


def validate_public_hashes(root: Path, config: dict[str, Any]) -> list[str]:
    if not config["publication"].get("require_source_hashes"):
        return []
    public = inside(root, root / config["publication"]["public_controls"])
    manifest = public.parent / "archivos_publicos.sha256"
    if not manifest.is_file():
        return [f"falta {manifest.relative_to(root)}"]
    expected: dict[str, str] = {}
    failures: list[str] = []
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not re.fullmatch(r"[A-Fa-f0-9]{64}", parts[0]):
            failures.append(f"{manifest}:{line_number} formato inválido")
            continue
        expected[parts[1].strip().replace("\\", "/")] = parts[0].upper()
    actual_files = sorted(path for path in public.rglob("*.csv") if path.is_file())
    actual_names = {path.relative_to(public.parent).as_posix() for path in actual_files}
    if set(expected) != actual_names:
        failures.append("archivos_publicos.sha256 no enumera exactamente los CSV públicos")
    for path in actual_files:
        name = path.relative_to(public.parent).as_posix()
        actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        if expected.get(name) != actual:
            failures.append(f"hash público inválido: {name}")
    return failures


def tracked_microdata(root: Path) -> list[str]:
    # Incluye archivos rastreados y no rastreados que Git sí consideraría; los
    # ignorados bajo .sies-local permanecen fuera del alcance público.
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    failures: list[str] = []
    for relative in result.stdout.splitlines():
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in {".csv", ".gz", ".parquet"}:
            continue
        if "fixtures" in path.parts:
            continue
        try:
            columns = {value.upper() for value in _header(path)}
        except (OSError, StopIteration, UnicodeError):
            continue
        if "MRUN" in columns:
            failures.append(relative)
        if "RUT" in columns:
            failures.append(relative + " (RUT)")
    return failures


def validate_release_governance(root: Path, config: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    publication_path = root / "governance" / "data-publication.yml"
    if not publication_path.is_file():
        failures.append("falta governance/data-publication.yml")
    else:
        publication = yaml.safe_load(publication_path.read_text(encoding="utf-8")) or {}
        approvals = publication.get("approvals", {})
        for owner in ("legal", "privacy", "data_owner"):
            if approvals.get(owner) != "approved":
                failures.append(f"aprobación {owner} pendiente")
        historical = publication.get("historical_publication_review", {}).get("status")
        if historical not in {"approved", "completed", "not_applicable"}:
            failures.append("revisión histórica de publicación MRUN pendiente")

    desktop_path = root / "governance" / "desktop-validation.yml"
    if not desktop_path.is_file():
        failures.append("falta governance/desktop-validation.yml completado")
    else:
        desktop = yaml.safe_load(desktop_path.read_text(encoding="utf-8")) or {}
        if desktop.get("status") != "approved":
            failures.append("validación Power BI Desktop no aprobada")
        for name, value in (desktop.get("checks") or {}).items():
            if value is not True:
                failures.append(f"validación Desktop pendiente: {name}")
        if desktop.get("project_version") != config["project"]["version"]:
            failures.append("versión de evidencia Desktop no coincide")

    if config["publication"].get("require_data_license") and not (root / "LICENCIA_DATOS.md").is_file():
        failures.append("falta LICENCIA_DATOS.md")
    manifest_path = root / "pbip.manifest.json"
    if not manifest_path.is_file():
        failures.append("falta pbip.manifest.json")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("version") != config["project"]["version"] or manifest.get("status") != "released":
            failures.append("pbip.manifest.json no está sincronizado como released")
    return failures


def validate(root: Path, config: dict[str, Any], profile: str) -> dict[str, Any]:
    failures: list[str] = []
    if profile in {"source", "release"}:
        failures.extend(doctor(root, config)["problems"])
        failures.extend(f"microdatos rastreados: {value}" for value in tracked_microdata(root))
        failures.extend(validate_public_controls(root, config))
        failures.extend(validate_public_hashes(root, config))
    if profile == "runtime":
        work = root / ".sies-work" / config["project"]["slug"]
        if not (work / SENTINEL).is_file():
            failures.append("falta workspace; ejecute prepare")
    if profile == "release":
        failures.extend(validate_release_governance(root, config))
        status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=True)
        if status.stdout.strip():
            failures.append("el working tree no está limpio")
        if config["project"]["release_status"] != "released":
            failures.append("release_status no es released")
        public = root / config["publication"]["public_controls"]
        if any("EJEMPLO" in path.read_text(encoding="utf-8", errors="ignore") for path in public.rglob("*.csv")):
            failures.append("los controles públicos todavía contienen datos de ejemplo")
    return {"ok": not failures, "profile": profile, "failures": failures}


def bundle(root: Path, config: dict[str, Any], check_only: bool = False) -> dict[str, Any]:
    validation = validate(root, config, "release")
    if not validation["ok"]:
        raise SiesPbipError("Release bloqueada:\n" + "\n".join(validation["failures"]))
    if check_only:
        return validation
    dist = inside(root, root / "dist")
    dist.mkdir(exist_ok=True)
    version = config["project"]["version"]
    output = dist / f"{config['project']['slug']}-v{version}.zip"
    subprocess.run(["git", "archive", "--format=zip", f"--output={output}", "HEAD"], cwd=root, check=True)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    (dist / "SHA256SUMS").write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    return {"ok": True, "bundle": str(output), "sha256": checksum}
