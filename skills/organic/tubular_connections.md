---
name: tubular-connections
domain: organic
applies_to: [curve, mesh]
tools: [inspect_mesh_detailed, smooth_mesh, recalculate_normals]
sources: [blender_api, blender_manual, blender_mcp_n8n]
---

# Conexiones tubulares

Conserva el radio proximal y evita estrechamientos abruptos. Tras una conexión,
comprueba continuidad visual, normales y bordes abiertos.

Precondición: loops compatibles e inspección de ambos objetos. Validación:
`validate_mesh` y `evaluate_mesh`; usa captura controlada solo para continuidad
orgánica. Detente ante nuevas aristas abiertas o non-manifold.
