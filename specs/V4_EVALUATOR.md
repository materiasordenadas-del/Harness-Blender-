# V4 — Evaluador determinista

V4 añade inspección, medición y comparación; nunca modifica Blender. Su primera
herramienta es `inspect_scene_detailed`, seguida por evaluadores de malla,
tubulares, espaciales y diff de informes.

## Source repositories

### AgentCAD
https://agentcad.dev/

Estudiar: execute → inspect → render → validate → diff. No copiar código ni integraciones no revisadas.

### SimWorld Studio
https://github.com/SimWorld-AI/SimWorld-Studio

Estudiar: verificación rule-based y visual. No usar su arquitectura de Unreal.

## Regla de seguridad

Las herramientas V4 no llaman operadores que cambien la escena, no registran
undo y devuelven solo datos JSON.
