# Registro de cambios

Este proyecto usa Semantic Versioning y el formato de Keep a Changelog.

## [Sin publicar]

### Cambiado

- Migración candidata a 3.3.1 y al contrato `sies-pbip/v1`.
- MRUN pasa a ser un insumo exclusivamente local bajo el modo `external_mrun`.
- La edición de Power BI se realiza en `.sies-work` mediante `prepare` y `capture`.
- La configuración operativa se centraliza en `config/sies-pbip.yml`.
- Se incorpora la CLI `siespbip` y el generador reutilizable `init-sies` (`crear_pbip_github`).
- CI valida estructura, fixtures Windows/Linux, proyecto, privacidad, código generado y dependencias.

### Seguridad

- Se retiran del árbol vigente los derivados fila a fila con MRUN.
- Los datos públicos usan umbral mínimo de 10 y controles de privacidad automatizados.
- La posible purga del historial queda fuera de alcance hasta cerrar la revisión jurídica y de privacidad.
- Se actualizan DuckDB y pytest a versiones sin vulnerabilidades conocidas en la auditoría.

## [3.1.0] - 2026-09-12

- Siete páginas, 73 visuales únicos y 21 medidas.
- Auditoría numérica de 4.955 controles sobre el corte Matrícula 2025 / Titulados 2024.
- Parámetro portable de ruta de datos y documentación PBIP/TMDL.

## [3.0.0] - 2026-09-11

- Primera versión del PBIP reproducible de Retención Académica SIES.
