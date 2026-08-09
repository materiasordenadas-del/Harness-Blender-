# C3 — Paquete de escena 2D seguro

## Objetivo

Convertir únicamente planes de reconstrucción ya revisados en operaciones tipadas que el bridge de Blender pueda ejecutar.

## Garantías

- Un plan con ambigüedades no produce operaciones Blender.
- Cada objeto conserva `asset_id`, categoría visual, dominio, referencia y observación de origen.
- Las instrucciones incluyen solo parámetros explícitos: posición, tamaño, capa, material, color y familia de forma.
- No transportan Python, scripts ni comandos libres.

## Resultado de esta subfase

Se genera un paquete `harness-cell2d-scene` con operaciones `create_cell2d_symbol`. La siguiente subfase implementará esta operación dentro del bridge de Blender y la validará en una escena real.
