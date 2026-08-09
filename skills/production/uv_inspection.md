---
name: uv-inspection
---

# Inspección UV

Antes de desplegar UV, confirma una malla y usa `inspect_uv`. Registra la
existencia de mapas UV, el mapa activo y los límites de sus coordenadas. Esta
habilidad es de solo lectura: no crea UV, no mueve coordenadas y no evalúa
solapes o islas como si fueran datos confirmados.

Cuando el usuario haya autorizado el cambio, `unwrap_uv` puede desplegar todas
las caras con `ANGLE_BASED` o `CONFORMAL`. Usa un margen explícito y conserva
una copia de todos los mapas UV para que `undo` los restaure.
