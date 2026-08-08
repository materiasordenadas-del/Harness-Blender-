---
name: visual-review
domain: visual
applies_to: [scene, mesh, curve]
tools: [inspect_scene_detailed, evaluate_mesh, evaluate_tubular, capture_controlled_view]
---

# Revisión visual con evidencia

Usa una revisión visual cuando la pregunta sea de apariencia: continuidad que
parece abrupta, semejanza con una referencia, deformación visible o lectura de
una bifurcación desde varios ángulos.

Primero identifica el objeto y toma medidas V4. Después solicita vistas
controladas que incluyan el objeto completo y, si hace falta, una vista cercana
de la región cuestionada. Describe solo lo visible y separa una observación de
una hipótesis.

No uses la imagen para estimar aquello que ya tiene una medida fiable, como
volumen, intersección o grosor. Si no hay suficiente evidencia, pide otra vista
o devuelve `needs_review`; no inventes una corrección.

Antes de modificar cualquier cosa, conserva el informe visual y las métricas
previas. Limita la corrección a la región indicada y valida de nuevo al final.
