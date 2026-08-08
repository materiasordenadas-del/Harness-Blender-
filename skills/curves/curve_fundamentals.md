---
name: curve-fundamentals
domain: curves
applies_to: [curve]
tools: [inspect_curve, set_curve_handle_type, set_curve_handle_position]
sources: [blender_api, blendermcp]
---

# Fundamentos de curvas

Usa curvas 3D para trayectorias que deben seguir editables. Bézier es preferible
cuando la transición depende de handles; NURBS sirve para suavidad global y Poly
para tramos rectos deliberados. Inspecciona antes de editar y conserva al menos
dos puntos.

Precondición: identificar una CURVE y llamar `inspect_curve`. Validación:
inspeccionar tras cada ajuste. Límite: no convertir a malla hasta estabilizar
trayectoria y radios.
