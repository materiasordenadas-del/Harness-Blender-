---
name: asset-validation
---

# Validación de asset

Antes de iniciar sculpt, retopología o UV, confirma un único objeto `MESH` y
reúne sus métricas de topología, evaluación, transformación, nombre,
colecciones y materiales mediante `evaluate_asset_readiness`. Devuelve `ready`, `needs_review` o `blocked` con las
causas observadas. Esta habilidad es de solo lectura: no corrige la malla, no
aplica modificadores y no crea UVs.
