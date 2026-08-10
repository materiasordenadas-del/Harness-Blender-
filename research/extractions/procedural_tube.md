# Hallazgo curado — tubo procedural

- **Pregunta:** cómo conservar una curva editable mientras se genera malla procedural.
- **Fuente y revisión:** `blender_api`, `blender_manual`, `blender_mcp_n8n`, revisados 2026-08-08.
- **Hallazgo:** exponer solo radio y remuestreo; árbol y malla evaluada se inspeccionan por separado.
- **Artefacto:** skill, receta V6 y Task Packet procedural.
- **Prueba:** integración Blender crea árbol, genera malla e invierte con undo.
- **No incorporar:** un tool MCP por cada nodo.
