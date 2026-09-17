# Preparar la ruta de datos SIES

La ruta absoluta de los derivados con MRUN nunca se escribe en los archivos canónicos. El modelo versionado conserva `__PBIP_DATA_PATH__`.

Después de verificar y materializar Matrícula y Titulados, ejecute:

```powershell
uv run python -m siespbip prepare --profile author
```

La herramienta crea una copia descartable bajo `.sies-work/<proyecto>`, inyecta allí la ruta de `.sies-local/derived/<proyecto>` y devuelve el `.pbip` que debe abrirse.

Para usar otra ubicación local:

```powershell
uv run python -m siespbip prepare --profile author --sies-root D:\derivados_sies
```

Después de editar en Power BI Desktop use `capture --check` y `capture --apply`. Si la fuente canónica cambió desde `prepare`, la captura se bloquea para evitar sobrescrituras.

`prepare --profile public` falla intencionalmente: el modo `external_mrun` no publica los microdatos requeridos para actualizar.
