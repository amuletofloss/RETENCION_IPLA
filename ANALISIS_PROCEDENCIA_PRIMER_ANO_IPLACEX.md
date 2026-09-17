# Procedencia de la matrícula de primer año de IPLACEX

## Respuesta ejecutiva publicable

En los cohortes **2012–2026**, el universo del PBIP contiene **80.028
matrículas/trayectorias de primer año de IPLACEX**:

- **42.286 (52,8 %)** tienen matrícula previa observable en otra IES;
- **36.792 (46,0 %)** no tienen matrícula previa observable;
- **43.236 (54,0 %)** tienen alguna matrícula previa;
- **8.965 (11,2 %)** registran un antecedente online en otra IES.

En **2025–2026**, 20.058 de 34.356 trayectorias (58,4 %) tienen historia en
otra IES y 4.486 (13,1 %) presentan historia online en otra IES.

Los resultados describen antecedentes de matrícula. No demuestran captación
directa ni causalidad.

## Política de publicación

La desagregación anual histórica contenía celdas entre 1 y 9. Se retiró de la
versión pública 3.3.1 y permanece solo en el entorno local de auditoría. Este
documento muestra periodos agregados cuyas celdas cumplen el umbral mínimo 10.
Los valores publicables y sus hashes están en
[`datos/controles_publicos/procedencia_iplacex.csv`](datos/controles_publicos/procedencia_iplacex.csv).

## Definiciones y filtros

- Unidad: trayectoria deduplicada MRUN–carrera–institución–cohorte.
- IPLACEX: `InstitucionID = 152`.
- Universo: pregrado IP, Plan Regular, ingreso en el primer semestre del cohorte
  y modalidad No Presencial/Semipresencial o jornada A Distancia.
- Con matrícula previa: el MRUN aparece en cualquier año anterior disponible,
  en IPLACEX o en otra IES.
- Antecedente en otra IES: existe un registro anterior en una institución
  distinta de IPLACEX.
- No se consideran matrículas simultáneas del mismo año como antecedente previo.

Fuente: Matrícula de Educación Superior SIES 2011–2025. Se excluye 2011 porque
no existe historia anterior observable. La ventana de observación aumenta en
cohortes recientes, por lo que la evolución no debe interpretarse causalmente.
