# Contribuir

Toda modificación al PBIP debe conservar reproducibilidad, trazabilidad y coherencia entre datos, modelo, reporte y documentación.

## Flujo recomendado

Mientras la organización no defina otra convención, se adopta GitHub Flow:

1. Cree una rama corta desde `main`: `feature/descripcion`, `fix/descripcion`, `docs/descripcion` o `data/descripcion`.
2. Realice commits pequeños con Conventional Commits, por ejemplo `fix(dax): controla multiseleccion de cohorte`.
3. Ejecute las validaciones locales.
4. Abra un pull request usando la plantilla.
5. Obtenga revisión del propietario correspondiente y espere que CI finalice correctamente.
6. Integre mediante squash merge. No haga force-push sobre `main`.

## Preparación local

```powershell
uv sync --extra dev --locked
uv run pytest -q
uv run python -m siespbip validate --profile source
node --check scripts/construir_pbip.mjs
node --check scripts/visuales.mjs
```

Para una modificación funcional, materialice Matrícula y Titulados SIES fuera de Git,
ejecute `siespbip prepare --profile author` y abra exclusivamente el PBIP ubicado en
`.sies-work/`. Use `capture --check` antes de `capture --apply`.

## Qué debe actualizar cada cambio

| Cambio | Evidencia mínima |
|---|---|
| Indicador o medida DAX | TMDL, `docs/03-dax.md`, prueba y resultado antes/después |
| Relación, tabla o columna | TMDL, `docs/02-modelo-semantico.md`, diagrama y prueba de cardinalidad |
| Transformación o fuente | script, manifiesto, hash, `docs/04-power-query.md` y conciliación |
| Página o visual | definición del reporte, `docs/05-reporte.md` y captura o descripción verificable |
| Seguridad | TMDL, `docs/06-seguridad.md` y matriz de pruebas por rol |
| Decisión irreversible o transversal | nuevo ADR en `docs/10-adr/` |
| Versión liberada | `CHANGELOG.md`, manifiesto y checklist de release |

## Reglas del modelo

- No introducir una columna `RUT`; `MRUN` es el identificador enmascarado de las fuentes abiertas.
- No publicar archivos fuente brutos en `datos_fuente/`.
- No incorporar credenciales, tokens ni identificadores de tenant o workspace reales. La única ruta local admitida es el valor generado de `Ruta datos`, necesario para actualizar el PBIP en esa copia.
- Mantener relaciones de dimensión a hecho con filtro unidireccional, salvo excepción respaldada por ADR y prueba.
- Las medidas deben tener descripción, formato y carpeta de visualización.
- Toda cifra presentada debe poder reconstruirse desde controles agregados versionados o desde fuentes SIES y scripts documentados.
- Ningún CSV, GZIP o Parquet rastreado por Git puede contener una columna `MRUN` o `RUT` real.
- Todo conteo público entre 1 y 9 debe suprimirse junto con las celdas complementarias necesarias.

## Definición de terminado

Un cambio está terminado cuando:

- CI está verde;
- no modifica resultados sin explicar y conciliar la diferencia;
- el PBIP abre y actualiza;
- los enlaces y diagramas documentales son válidos;
- la revisión cubre DAX, datos o reporte según corresponda;
- no quedan secretos; cualquier ruta local se limita al parámetro generado `Ruta datos`;
- `CHANGELOG.md` y la documentación afectada están actualizados.

Use el checklist completo de [docs/11-checklists.md](docs/11-checklists.md).
