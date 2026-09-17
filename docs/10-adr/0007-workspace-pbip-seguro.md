# ADR-0007 · Workspace local seguro para Power BI Desktop

- Estado: Aceptado
- Fecha: 2026-09-13
- Decisor: `@amuletofloss`

## Contexto

Power Query requiere una ruta absoluta. Editar el parámetro dentro del proyecto versionado ensucia Git, filtra rutas personales e invalida las pruebas de portabilidad.

## Decisión

El PBIP canónico conserva `__PBIP_DATA_PATH__`. `siespbip prepare` crea `.sies-work/<slug>`, inyecta allí la ruta local y registra un fingerprint. `capture --check/--apply` acepta únicamente PBIP, Report y SemanticModel, restaura el marcador y rechaza cambios concurrentes o rutas externas.

## Consecuencias

- El trabajo normal en Desktop no modifica el repositorio hasta una captura explícita.
- `.git` nunca es un destino de la herramienta.
- Los fallos dejan una copia de respaldo dentro de `.sies-work/backups/`.

