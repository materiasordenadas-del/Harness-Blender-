# Criterios de aceptación de V0

V0 se considera funcional cuando, desde un cliente MCP:

1. `blender_ping` devuelve la versión de Blender.
2. `inspect_scene` enumera los objetos existentes.
3. `create_primitive` crea un objeto con nombre explícito.
4. `transform_object` modifica su transformación.
5. `inspect_object` confirma el estado resultante.
6. `validate_mesh` devuelve métricas sin modificar la malla.
7. `capture_blender_screen` devuelve una imagen PNG en modo gráfico.
8. `save_blend` guarda el archivo solicitado.
9. El token incorrecto es rechazado.
10. Ninguna herramienta MCP acepta código Python proporcionado por el modelo.
