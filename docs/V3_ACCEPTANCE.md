# V3 Capa de conocimiento: evidencia de aceptación

## Entregado

- Registro local de skills Markdown con metadatos y lectura bajo demanda.
- Router determinista que elige solo las skills, herramientas y documentación
  oficial necesarias para una tarea corta.
- Índice SQLite FTS local con entradas exclusivas de `https://docs.blender.org`.
- Herramientas MCP: `route_blender_task`, `list_blender_skills`,
  `get_blender_skill` y `search_blender_docs`.
- Recursos MCP de solo lectura: `harness://v3/skills` y `harness://v3/docs`.

## Escenario de aceptación

Para “conectar estos dos vasos”, el router devuelve:

- Skills: `tubular-connections`, `smooth-transitions`, `bridge-loops`.
- Herramientas: inspección, bridge, remesh, suavizado, normales y validación.
- Documentación oficial de BMesh.

No devuelve herramientas de materiales ni el catálogo completo. La prueba
integrada verifica la cadena tarea → router → skill → documentación → tools.
