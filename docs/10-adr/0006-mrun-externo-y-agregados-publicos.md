# ADR-0006 · MRUN externo y agregados públicos

- Estado: Aceptado
- Fecha: 2026-09-13
- Decisor: `@amuletofloss`

## Contexto

Matrícula y Titulados SIES requieren MRUN para vinculación longitudinal. Que MRUN sea enmascarado y provenga de Datos Abiertos no elimina el riesgo de vincular trayectorias individuales.

## Decisión

Adoptar `external_mrun`: las fuentes y derivados con MRUN viven en `.sies-local/` y nunca se versionan. GitHub publica controles agregados con umbral 10 y supresión complementaria. RUT queda prohibido.

No se mantiene un modelo agregado alternativo; actualizar el PBIP exige reconstruir localmente las fuentes SIES.

## Consecuencias

- Un clon no actualiza inmediatamente.
- Se reduce la exposición de registros longitudinales.
- Las pruebas automatizadas usan solo `MRUN_TEST_*` inventados.
- La publicación histórica se revisa por separado y no autoriza una purga automática.

