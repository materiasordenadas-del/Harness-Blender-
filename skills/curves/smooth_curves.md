---
name: smooth-curves
domain: curves
applies_to: [curve]
tools: [inspect_curve, set_curve_handle_type, set_curve_handle_position]
sources: [blender_api, ezblender]
---

# Curvas suaves

Para una transición orgánica, comienza con handles `AUTO` o `ALIGNED`. Usa
`VECTOR` solo para un quiebre deliberado. Cambia un handle concreto antes de
alterar toda la curva e inspecciona después de cada ajuste. No diagnostiques
continuidad solo por imagen: conserva evidencia de handles y puntos antes/después.
