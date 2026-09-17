# Retención Académica SIES

[![CI](https://github.com/amuletofloss/RETENCION_IPLA/actions/workflows/ci.yml/badge.svg)](https://github.com/amuletofloss/RETENCION_IPLA/actions/workflows/ci.yml)
[![Licencia MIT](https://img.shields.io/badge/código-MIT-blue.svg)](LICENSE)
[![Estándar](https://img.shields.io/badge/SIES--PBIP-v1-173277.svg)](config/sies-pbip.yml)

Proyecto Power BI Project (PBIP) para analizar continuidad académica en Institutos Profesionales y Centros de Formación Técnica usando exclusivamente Datos Abiertos SIES de **Matrícula** y **Titulados**.

> Estado: **3.3.1 publicada**. La distribución excluye microdatos reales y rutas personales; el PBIP contiene 16 páginas.

## Indicadores

Para una cohorte y horizonte observables, el modelo calcula:

1. retención académica: continuidad en la carrera e institución de origen;
2. retención institucional: continuidad en la institución jurídica de origen;
3. continuidad en educación superior: matrícula posterior en cualquier institución;
4. titulación acumulada según registros SIES de Titulados.

La metodología es una reconstrucción analítica propia y no un indicador oficial certificado por SIES.

## Política de datos

MRUN es el identificador enmascarado publicado por SIES y se usa localmente, como texto, para cruces longitudinales y conteos distintos. No es RUT y el estándar prohíbe incorporar una columna RUT.

Este repositorio aplica `external_mrun`:

- no versiona filas reales con MRUN;
- no incluye las bases oficiales completas;
- publica código, definiciones PBIP, catálogo de fuentes, hashes y controles agregados;
- suprime conteos públicos entre 1 y 9 y aplica supresión complementaria;
- utiliza únicamente `MRUN_TEST_*` inventados en pruebas.

La publicación histórica anterior a 3.3.1 está documentada en [la revisión de MRUN](governance/MRUN_PUBLICATION_REVIEW.md).

## Consultar sin reconstruir

GitHub permite revisar el modelo TMDL, las medidas DAX, el reporte PBIR, la metodología y los [controles públicos](datos/controles_publicos/). El repositorio no promete un refresh inmediato después de clonar porque los microdatos necesarios permanecen fuera de Git.

Resultados de referencia para cohorte 2025 y horizonte 2:

| Ámbito | Base | Académica | Institucional | Educación superior |
|---|---:|---:|---:|---:|
| IP+CFT | 50.233 | 31.349 | 32.153 | 35.339 |
| ECS | 2.299 | 1.621 | 1.655 | 1.767 |

## Reconstruir con fuentes SIES

Requisitos: Power BI Desktop compatible con PBIP/TMDL, Python 3.12, Node.js 22, Git y espacio suficiente para las fuentes. Los 29 archivos oficiales registrados suman aproximadamente 13,55 GB, sin considerar temporales.

1. Descargue Matrícula 2011–2026 y Titulados 2011–2025 desde el [portal oficial](https://centroestudios.mineduc.cl/datos-abiertos/).
2. Organícelos bajo una carpeta local, fuera del repositorio.
3. Instale y valide:

```powershell
uv sync --extra dev --locked
uv run python -m siespbip doctor
uv run python -m siespbip sources verify --root D:\datos_sies
uv run python -m siespbip materialize --source-root D:\datos_sies
```

Los derivados con MRUN quedan en `.sies-local/derived/`, excluidos de Git.

## Editar en Power BI Desktop

```powershell
uv run python -m siespbip prepare --profile author
```

Abra el `.pbip` informado dentro de `.sies-work/`. Al terminar:

```powershell
uv run python -m siespbip capture --check
uv run python -m siespbip capture --apply
uv run python -m siespbip validate --profile source
```

`prepare` evita escribir rutas personales en el PBIP canónico. `capture` solo admite los tres artefactos PBIP declarados, restaura `__PBIP_DATA_PATH__` y nunca opera sobre `.git`.

## Crear otro PBIP SIES

El generador `crear_pbip_github` crea una base nueva a partir de esta semilla,
sin inicializar Git y sin copiar fuentes ni derivados:

```powershell
uv run python -m siespbip init-sies `
  --name "Nuevo análisis SIES" `
  --slug nuevo_analisis_sies `
  --destination ..\nuevo-analisis-sies `
  --github-owner mi-organizacion
```

El resultado conserva el contrato Matrícula + Titulados, MRUN textual local,
prohibición de RUT, umbral público 10, workspace seguro y CI multiplataforma.
Incluye este proyecto como semilla funcional; antes de liberar se deben adaptar
el universo, las transformaciones, las medidas, el reporte y los controles.
Vea el [estándar reutilizable](docs/12-estandar-reutilizable.md).

## Estructura

```text
config/sies-pbip.yml                   contrato operativo
Retencion_Academica_SIES.pbip          entrada del proyecto
Retencion_Academica_SIES.Report/       reporte PBIR
Retencion_Academica_SIES.SemanticModel modelo TMDL
siespbip/                               CLI segura
scripts/                               materialización y auditoría
datos/controles_publicos/              agregados publicables
tests/                                 estándar, privacidad y proyecto
docs/                                  metodología y decisiones
governance/                            gates y evidencia
```

El índice técnico está en [docs/README.md](docs/README.md), el flujo de mantenimiento en [PUBLICACION_GITHUB.md](PUBLICACION_GITHUB.md) y las reglas de contribución en [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencias y seguridad

El código y la documentación se distribuyen bajo [MIT](LICENSE). Matrícula y Titulados conservan sus condiciones de origen, detalladas en [LICENCIA_DATOS.md](LICENCIA_DATOS.md). No publique microdatos, rutas, secretos ni evidencia sensible en issues; consulte [SECURITY.md](SECURITY.md).
