# Seguridad

## Alcance

El repositorio usa exclusivamente Matrícula y Titulados de Datos Abiertos SIES. `MRUN` es un identificador enmascarado, no un RUT real, y se procesa únicamente en `.sies-local/`: no se publica fila a fila, no se muestra en visuales y no se combina con fuentes privadas.

## Versiones soportadas

| Versión | Estado |
|---|---|
| 3.3.1 | Vigente; historial público limpio |
| 3.3.0 y anteriores | Retiradas por contener artefactos que no pertenecen a la distribución pública |

## Reporte responsable

No publique credenciales, MRUN ni evidencia sensible en un issue. Use **Private vulnerability reporting** en la pestaña Security. Si esa opción no está disponible, abra únicamente un issue sin detalles titulado `Solicitud de canal privado de seguridad`; el propietario coordinará un canal antes de recibir evidencia.

## Controles obligatorios

- No versionar `.env`, tokens, secretos, conexiones personales ni identificadores internos no autorizados.
- Usar GitHub Environments y secretos del repositorio para automatización.
- Aplicar mínimo privilegio al service principal de despliegue.
- Revisar cambios en `expressions.tmdl`, roles y workflows por un propietario independiente.
- Rotar de inmediato una credencial expuesta y eliminarla del historial mediante un procedimiento autorizado.
- Verificar que `.sies-local/` permanezca excluida y que ningún archivo rastreado tenga una columna MRUN o RUT.
- Aplicar umbral mínimo 10 y supresión complementaria a los controles públicos.

## RLS y OLS

El modelo actual no define RLS ni OLS. Es una decisión acorde con su conjunto de datos abiertos y alcance público, no una garantía general de seguridad. Si se incorporan datos internos, la publicación queda bloqueada hasta diseñar roles, pruebas positivas/negativas y un ADR de seguridad. Consulte [docs/06-seguridad.md](docs/06-seguridad.md).
