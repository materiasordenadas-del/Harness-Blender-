# V3 — Capa de conocimiento

## Objetivo

V3 ayuda al agente a elegir capacidades existentes sin depender de recordar
Blender. Expone un registro local de skills, documentación oficial indexada y un
router determinista. No ejecuta operaciones de Blender ni recibe Python.

## Contratos iniciales

- Un skill es un Markdown con bloque YAML inicial: `name`, `domain`,
  `applies_to` y `tools`.
- El registro devuelve metadatos y ruta; solo carga el contenido cuando se pide
  un skill concreto.
- El índice de documentación solo admite entradas con URL oficial de
  `docs.blender.org`.
- El router devuelve skills, documentos y herramientas relevantes, sin ampliar
  el catálogo completo.

## Aceptación

Para la tarea “conectar dos vasos”, el router debe sugerir skills orgánicas y
herramientas de malla pertinentes, sin incluir herramientas de materiales o
curvas no necesarias.
