# Mantenimiento y releases en GitHub

Este repositorio ya está inicializado y conectado a GitHub. No ejecute `git init` ni genere otra copia anidada.

## Flujo de cambios

1. Cree una rama breve desde `main`.
2. Ejecute `uv sync --extra dev --locked`.
3. Trabaje mediante `siespbip prepare --profile author`.
4. Revise con `siespbip capture --check` antes de aplicar.
5. Ejecute `siespbip validate --profile source` y `pytest`.
6. Abra un pull request y espere el gate `CI / gate`.

## Release

Una release requiere configuración, manifiesto, changelog, evidencia Desktop, licencias y aprobaciones sin marcadores pendientes. Después de sincronizar `release_status` y `pbip.manifest.json` como `released`:

```powershell
uv run python -m siespbip release --check
uv run python -m siespbip release --bundle
```

El bundle se crea desde `HEAD` mediante `git archive`; no incorpora archivos locales o ignorados. Crear tags, publicar releases o hacer push sigue siendo una acción explícita del propietario.

No existe despliegue automático a Fabric en la versión 1 del estándar.
