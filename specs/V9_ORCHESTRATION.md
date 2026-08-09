# V9 — orquestación

## Source repositories

### SimWorld Studio y SimWorld
https://github.com/SimWorld-AI/SimWorld-Studio
https://github.com/SimWorld-AI/SimWorld

Estudiar: cliente de modelo intercambiable, planner, coder, reviewer, verifier, skills y feedback. No copiar componentes de Unreal ni permitir agentes sin límites.

### AgentCAD, EZBlender y ArtisanCAD
https://agentcad.dev/
https://arxiv.org/abs/2601.07143
https://arxiv.org/abs/2607.05750

Estudiar: ejecución-validación-diff, Plan-and-ReAct y recetas dependientes de verificación. Son referencias de investigación, no dependencias.

## Objetivo

Reducir las esperas de tareas de varios pasos sin duplicar las capas ya
implementadas en V3-V5. V9 prepara una tarea desde la escena real, muestra un
plan revisable y ejecuta sus operaciones tipadas en una sola solicitud al
bridge.

Flujo inicial: `preparar → revisar plan → ejecución agrupada → snapshot/diff → revisión visual si se solicita`.

No incluye multiagentes, memoria de recetas, checkpoints ni corrección o
reversión automática. Si un paso falla, la ejecución se detiene e informa el
paso; el usuario conserva el undo normal de Blender.
