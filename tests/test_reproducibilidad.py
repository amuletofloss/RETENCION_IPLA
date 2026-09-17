import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml
from jsonschema import validate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datos"


def test_contrato_sies_es_valido_y_versionado():
    config = yaml.safe_load((ROOT / "config/sies-pbip.yml").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/sies-pbip.schema.json").read_text(encoding="utf-8"))
    validate(config, schema)
    assert config["schema_version"] == "sies-pbip/v1"
    assert config["project"]["version"] == "3.3.1"
    assert config["project"]["release_status"] == "released"
    assert config["sies"]["identity"] == {"field": "MRUN", "type": "string", "rut_forbidden": True}
    assert config["publication"]["mode"] == "external_mrun"
    assert config["publication"]["minimum_cell_size"] == 10


def test_un_solo_pbip_y_dieciseis_paginas():
    assert [path.name for path in ROOT.glob("*.pbip")] == ["Retencion_Academica_SIES.pbip"]
    pages = json.loads((ROOT / "Retencion_Academica_SIES.Report/definition/pages/pages.json").read_text(encoding="utf-8"))
    assert len(pages["pageOrder"]) == 16
    names = [json.loads((ROOT / f"Retencion_Academica_SIES.Report/definition/pages/{page}/page.json").read_text(encoding="utf-8"))["displayName"] for page in pages["pageOrder"]]
    assert names == ["Resumen nacional", "Cohortes", "Instituciones", "Modalidad y jornada", "ECS", "Titulación", "Metodología", "ret_carrera", "ret_carrera_ipla", "ret_carrera_ecs", "ret_institucion", "ret_ipla", "ret_ecs", "ret_educacion_superior", "ret_es_ipla", "ret_es_ecs"]


def test_json_y_limite_github():
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(
            part in {".git", ".pbi", ".venv", ".sies-local", ".sies-work", ".pytest_cache", ".uv-cache", "__pycache__"}
            for part in path.parts
        ):
            continue
        assert path.stat().st_size < 100 * 1024 * 1024, path
        if path.suffix in {".json", ".pbip", ".pbir", ".pbism"} or path.name == ".platform":
            json.loads(path.read_text(encoding="utf-8-sig"))


def test_git_no_rastrea_microdatos_reales():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.splitlines()
    assert not [name for name in tracked if re.match(r"datos/(seguimiento|transiciones)_.*\.csv\.gz$", name)]
    assert "datos/programas.csv" not in tracked
    assert "datos/resultados_control.csv" not in tracked
    for name in tracked:
        if not name.startswith("datos/") or not name.endswith(".csv"):
            continue
        path = ROOT / name
        first = path.read_text(encoding="utf-8-sig").splitlines()[0].split(";")
        assert "MRUN" not in first
        assert "RUT" not in first


def test_controles_publicos_aplican_umbral_diez():
    protected_names = re.compile(r"(?i)(base|total|conteo|personas|retenidos|numerador|cantidad)")
    for path in (DATA / "controles_publicos").glob("*.csv"):
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                assert "MRUN" not in row and "RUT" not in row
                for key, value in row.items():
                    if protected_names.search(key) and (value or "").isdigit():
                        assert int(value) == 0 or int(value) >= 10, (path, key, value)


def test_hashes_de_archivos_publicos():
    lines = [line for line in (DATA / "archivos_publicos.sha256").read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 2
    for line in lines:
        expected, name = line.split(maxsplit=1)
        actual = hashlib.sha256((DATA / name).read_bytes()).hexdigest().upper()
        assert actual == expected.upper(), name


def test_fuentes_sies_y_cobertura():
    manifest = json.loads((DATA / "fuentes.json").read_text(encoding="utf-8"))
    assert len(manifest["archivos"]) == 31
    assert [row["anio"] for row in manifest["archivos"] if row["fuente"] == "matricula"] == list(range(2011, 2027))
    assert [row["anio"] for row in manifest["archivos"] if row["fuente"] == "titulados"] == list(range(2011, 2026))
    assert all(len(row["sha256"]) == 64 for row in manifest["archivos"])


def test_modelo_usa_mrun_oculto_y_marcador_portable():
    definition = ROOT / "Retencion_Academica_SIES.SemanticModel/definition"
    text = "\n".join(path.read_text(encoding="utf-8") for path in definition.rglob("*.tmdl"))
    assert "DISTINCTCOUNT('Seguimiento'[MRUN])" in text
    seguimiento = (definition / "tables/Seguimiento.tmdl").read_text(encoding="utf-8")
    assert re.search(r"column MRUN\s+dataType: string\s+isHidden", seguimiento)
    expression = (definition / "expressions.tmdl").read_text(encoding="utf-8")
    assert 'expression \'Ruta datos\' = "__PBIP_DATA_PATH__"' in expression
    assert "C:" + "/Users/" not in expression
    assert "C:" + "\\Users\\" not in expression


def test_visuales_referencian_campos_y_estan_en_el_lienzo():
    table_dir = ROOT / "Retencion_Academica_SIES.SemanticModel/definition/tables"
    catalog = {}
    for path in table_dir.glob("*.tmdl"):
        source = path.read_text(encoding="utf-8")
        table_match = re.search(r"^table '?([^'\n]+)'?$", source, re.MULTILINE)
        assert table_match, path
        columns = re.findall(r"^\s*column\s+(?:'([^']+)'|([^\n]+?))\s*$", source, re.MULTILINE)
        measures = re.findall(r"^\s*measure\s+(?:'([^']+)'|([^=\n]+?))\s*=", source, re.MULTILINE)
        catalog[table_match.group(1)] = {"columns": {q or p.strip() for q, p in columns}, "measures": {q or p.strip() for q, p in measures}}

    def walk(node):
        if isinstance(node, dict):
            for kind, key in (("Column", "columns"), ("Measure", "measures")):
                item = node.get(kind)
                if item and item.get("Expression", {}).get("SourceRef", {}).get("Entity"):
                    entity = item["Expression"]["SourceRef"]["Entity"]
                    assert item["Property"] in catalog[entity][key]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    paths = list((ROOT / "Retencion_Academica_SIES.Report/definition/pages").glob("*/visuals/*/visual.json"))
    assert len(paths) == 211
    names = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        names.append(payload["name"])
        position = payload["position"]
        assert position["x"] >= 0 and position["y"] >= 0
        assert position["x"] + position["width"] <= 1600
        assert position["y"] + position["height"] <= 900
        walk(payload)
    assert len(names) == len(set(names))


def test_controles_publicos_conservan_resultados_aprobados():
    with (DATA / "controles_publicos/resumen_retencion.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert rows[0] == {"Ambito": "IP+CFT", "Cohorte": "2025", "AnioDesdeIngreso": "2", "BaseTrayectorias": "50233", "RetenidosCarrera": "31349", "RetenidosInstitucion": "32153", "RetenidosEducacionSuperior": "35339"}
    assert rows[1]["Ambito"] == "ECS" and rows[1]["BaseTrayectorias"] == "2299"
