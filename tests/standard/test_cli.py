import json
import subprocess
from pathlib import Path

import yaml

from siespbip.core import SiesPbipError, capture, doctor, init_sies, load_config, prepare, tracked_microdata, validate_public_hashes, verify_sources


def minimal_project(tmp_path: Path):
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "Demo.Report").mkdir()
    (root / "Demo.SemanticModel/definition").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "Demo.pbip").write_text("{}\n", encoding="utf-8")
    (root / "Demo.Report/definition.pbir").write_text("{}\n", encoding="utf-8")
    (root / "Demo.SemanticModel/definition/expressions.tmdl").write_text(
        'expression \'Ruta datos\' = "__PBIP_DATA_PATH__" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n', encoding="utf-8"
    )
    config = {
        "schema_version": "sies-pbip/v1",
        "project": {"slug": "demo", "display_name": "Demo", "version": "1.0.0", "release_status": "candidate"},
        "sies": {"portal": "https://centroestudios.mineduc.cl/datos-abiertos/", "sources": {"matricula": {"first_year": 2025, "last_year": 2025}, "titulados": {"first_year": 2024, "last_year": 2024}}, "identity": {"field": "MRUN", "type": "string", "rut_forbidden": True}},
        "analysis": {"universe_id": "test", "cohort_field": "Cohorte", "observation_horizon": 2},
        "artifacts": {"pbip": "Demo.pbip", "report": "Demo.Report", "semantic_model": "Demo.SemanticModel", "data_parameter": "Ruta datos", "data_placeholder": "__PBIP_DATA_PATH__"},
        "publication": {"mode": "external_mrun", "public_controls": "datos/controles_publicos", "minimum_cell_size": 10, "require_source_hashes": True, "require_data_license": True},
    }
    (root / "config/sies-pbip.yml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return root, config


def test_prepare_y_capture_no_tocan_git(tmp_path):
    root, config = minimal_project(tmp_path)
    derived = root / ".sies-local/derived/demo"
    derived.mkdir(parents=True)
    marker = root / ".git/NO_TOCAR"
    marker.write_text("intacto", encoding="utf-8")
    result = prepare(root, config, derived)
    assert Path(result["pbip"]).is_file()
    runtime = root / ".sies-work/demo/Demo.SemanticModel/definition/expressions.tmdl"
    assert str(derived.resolve()) in runtime.read_text(encoding="utf-8")
    check = capture(root, config, apply=False)
    assert check["changes"] == []
    assert marker.read_text(encoding="utf-8") == "intacto"


def test_capture_check_detecta_cambio_sin_escribir(tmp_path):
    root, config = minimal_project(tmp_path)
    derived = root / ".sies-local/derived/demo"
    derived.mkdir(parents=True)
    prepare(root, config, derived)
    runtime_pbip = root / ".sies-work/demo/Demo.pbip"
    runtime_pbip.write_text('{"version":"cambio"}\n', encoding="utf-8")
    before = (root / "Demo.pbip").read_text(encoding="utf-8")
    result = capture(root, config, apply=False)
    assert "Demo.pbip" in result["changes"]
    assert (root / "Demo.pbip").read_text(encoding="utf-8") == before


def test_prepare_no_reemplaza_directorio_ajeno_sin_sentinel(tmp_path):
    root, config = minimal_project(tmp_path)
    derived = root / ".sies-local/derived/demo"
    derived.mkdir(parents=True)
    work = root / ".sies-work/demo"
    work.mkdir(parents=True)
    marker = work / "archivo-del-usuario.txt"
    marker.write_text("conservar", encoding="utf-8")
    try:
        prepare(root, config, derived)
    except SiesPbipError as exc:
        assert "sin sentinel" in str(exc)
    else:
        raise AssertionError("prepare debió rechazar un directorio sin sentinel")
    assert marker.read_text(encoding="utf-8") == "conservar"


def test_sources_verify_exige_matricula_titulados_mrun_y_rechaza_rut(tmp_path):
    root, config = minimal_project(tmp_path)
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "20260729_Matrícula_Ed_Superior_2025_PUBL_MRUN.csv").write_text("MRUN;valor\nMRUN_TEST_001;1\n", encoding="utf-8")
    titulados = sources / "20260729_Titulados_Ed_Superior_2024_PUBL_MRUN.csv"
    titulados.write_text("MRUN;valor\nMRUN_TEST_001;1\n", encoding="utf-8")
    assert verify_sources(root, config, sources)["ok"]
    titulados.write_text("MRUN;RUT\nMRUN_TEST_001;1-9\n", encoding="utf-8")
    result = verify_sources(root, config, sources)
    assert not result["ok"] and any("RUT" in failure for failure in result["failures"])


def test_doctor_detecta_repositorio_anidado(tmp_path):
    root, config = minimal_project(tmp_path)
    assert doctor(root, config)["ok"]
    (root / "subproyecto/.git").mkdir(parents=True)
    assert not doctor(root, config)["ok"]


def test_privacidad_detecta_microdato_no_rastreado(tmp_path):
    root, _ = minimal_project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    candidate = root / "datos/candidato.csv"
    candidate.parent.mkdir()
    candidate.write_text("MRUN;valor\nMRUN_TEST_001;1\n", encoding="utf-8")
    assert "datos/candidato.csv" in tracked_microdata(root)


def test_init_sies_genera_proyecto_sin_git(tmp_path):
    template_root = Path(__file__).resolve().parents[2]
    destination = tmp_path / "nuevo-proyecto"
    result = init_sies(template_root, destination, "Nuevo análisis SIES", "nuevo_analisis_sies", "equipo-sies")
    generated = load_config(destination)
    assert result["git_initialized"] is False
    assert not (destination / ".git").exists()
    assert generated["project"]["slug"] == "nuevo_analisis_sies"
    assert generated["project"]["release_status"] == "development"
    assert doctor(destination, generated)["ok"]
    assert (destination / "Nuevo_Analisis_Sies.pbip").is_file()
    assert (destination / ".github/CODEOWNERS").read_text(encoding="utf-8") == "* @equipo-sies\n"
    expression = destination / "Nuevo_Analisis_Sies.SemanticModel/definition/expressions.tmdl"
    assert "__PBIP_DATA_PATH__" in expression.read_text(encoding="utf-8")
    build_script = (destination / "scripts/construir_pbip.mjs").read_text(encoding="utf-8")
    assert "Nuevo_Analisis_Sies.pbip" in build_script
    assert not validate_public_hashes(destination, generated)
