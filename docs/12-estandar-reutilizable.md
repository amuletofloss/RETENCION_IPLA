# Estándar reutilizable `crear_pbip_github`

## Alcance obligatorio

Todo proyecto generado es 100 % SIES: sus únicas fuentes analíticas permitidas
son Matrícula y Titulados de Datos Abiertos SIES. El cruce longitudinal utiliza
`MRUN` como texto en el entorno local. `RUT` está prohibido.

## Contrato fijo

| Decisión | Regla |
|---|---|
| Repositorio | una sola raíz Git, nunca copias Git anidadas |
| Microdatos | fuentes y derivados con MRUN en `.sies-local/` |
| Autoría PBIP | copia operativa en `.sies-work/` |
| PBIP canónico | marcador `__PBIP_DATA_PATH__`, sin rutas personales |
| Publicación | código, PBIP, metadatos, hashes y agregados |
| Privacidad | celdas 1–9 suprimidas y supresión complementaria |
| Release | solo desde un commit limpio y estado `released` |

## Ciclo de vida

1. `sources verify` comprueba un archivo por fuente/año, MRUN presente y RUT ausente.
2. `materialize` construye derivados locales reproducibles.
3. `prepare` crea un workspace con la ruta local inyectada.
4. Power BI Desktop abre únicamente la copia de `.sies-work/`.
5. `capture --check` muestra cambios y `capture --apply` los incorpora al canónico.
6. `validate --profile source` bloquea microdatos rastreados y celdas pequeñas.
7. `release --bundle` empaqueta exclusivamente el contenido confirmado en `HEAD`.

`prepare` solo reemplaza workspaces que tengan su sentinel. `capture` limita el
alcance al `.pbip`, `.Report` y `.SemanticModel` declarados, restaura el marcador
y rechaza rutas personales. Ningún comando inicializa Git ni publica a GitHub.

## Qué debe personalizar un proyecto nuevo

- `analysis.universe_id`, cohortes y horizonte en `config/sies-pbip.yml`;
- reglas de materialización y validaciones del universo;
- tablas, relaciones, medidas DAX y páginas del reporte;
- controles públicos reales y hashes, retirando el control `MRUN_TEST`;
- nombre, responsables, cita, licencias de datos y documentación metodológica;
- validación final en Power BI Desktop registrada en gobernanza.

La semilla se entrega en estado `development`. Cambiarla a `released` sin cerrar
esas decisiones contradice el estándar y debe ser rechazado en revisión.
