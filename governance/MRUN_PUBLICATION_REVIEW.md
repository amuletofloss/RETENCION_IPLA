# Revisión de publicación histórica de MRUN

## Decisión operativa vigente

El estándar `sies-pbip/v1` usa Matrícula y Titulados SIES con MRUN como llave longitudinal local, pero adopta `external_mrun`: ningún archivo fila a fila con MRUN se incorpora al árbol vigente ni a los bundles de release.

La publicación anterior de `RETENCION_IPLA` incluyó archivos `seguimiento_*.csv.gz` con MRUN enmascarado. La versión 3.3.1 se prepara como un historial raíz nuevo sin esos archivos. El reemplazo de las referencias remotas no elimina copias ya clonadas ni cachés externas.

## Condición de publicación

Antes de reconstruir localmente los datos, cada usuario debe revisar:

1. términos exactos de Matrícula y Titulados SIES;
2. base para redistribuir derivados longitudinales;
3. riesgo de vinculación o reidentificación indirecta;
4. necesidad de notificación adicional sobre publicaciones anteriores.

La sustitución remota de `main` y la eliminación del tag anterior requieren confirmación explícita del propietario en el momento de ejecutarlas.
