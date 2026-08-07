# Ejecución segura — V0

- El bridge debe enlazarse solo a `localhost` o `127.0.0.1`.
- El token del add-on debe coincidir con `BLENDER_TOKEN` del servidor MCP.
- Las operaciones destructivas deben dirigirse a objetos nombrados explícitamente.
- La inspección precede a la modificación cuando el estado es desconocido.
- La validación geométrica usa métricas; la validación estética usa imágenes.
- `undo_last_action` es una herramienta de recuperación, no una sustitución de planificación.
- El agente no debe modificar preferencias globales de Blender ni cerrar la aplicación.
