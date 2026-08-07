# V4 — Evaluador determinista

V4 añade inspección, medición y comparación; nunca modifica Blender. Su primera
herramienta es `inspect_scene_detailed`, seguida por evaluadores de malla,
tubulares, espaciales y diff de informes.

## Regla de seguridad

Las herramientas V4 no llaman operadores que cambien la escena, no registran
undo y devuelven solo datos JSON.
