# Validación del 3.3.1

Fecha de migración: 13 de septiembre de 2026.

## Estado

- [OK] Contrato `sies-pbip/v1` con Matrícula y Titulados obligatorios.
- [OK] MRUN textual y oculto en el modelo; RUT prohibido.
- [OK] Microdatos retirados del árbol vigente.
- [OK] Un PBIP, 16 páginas y 211 visuales únicos.
- [OK] Controles agregados públicos para IP+CFT y ECS.
- [OK] Flujo local `prepare`/`capture` sin rutas personales canónicas.
- [OK] El historial público nuevo no contiene los microdatos de la publicación anterior.
- [OK] Refresh, navegación y revisión visual informados como correctos en Power BI Desktop.
- [PENDIENTE] Configuración del ruleset y reporte privado de vulnerabilidades en GitHub.

La auditoría 3.3.1 concilió 5.693 controles sin fallos sobre 1.998.296 filas de seguimiento y 22.722.855 transiciones persona-año locales. El resumen agregado permanece en `auditoria/evidencia/resumen_auditoria.json`; el detalle y los microdatos se regeneran localmente y no se publican.

## Controles públicos vigentes

| Ámbito | Cohorte / horizonte | Base | Académica | Institucional | Educación superior |
|---|---|---:|---:|---:|---:|
| IP+CFT | 2025 / año 2 | 50.233 | 31.349 | 32.153 | 35.339 |
| ECS | 2025 / año 2 | 2.299 | 1.621 | 1.655 | 1.767 |

## Repetir validación de código

```powershell
uv sync --extra dev --locked
uv run python -m siespbip doctor
uv run python -m siespbip validate --profile source
uv run pytest -q
node --check scripts/construir_pbip.mjs
node --check scripts/visuales.mjs
```

La release 3.3.1 solo podrá marcarse `released` cuando la plantilla se complete como `governance/desktop-validation.yml`, las aprobaciones estén cerradas y CI esté verde.
