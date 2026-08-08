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

Integrar un planner explícito, estado de tarea, revisión determinista y visual, y recetas aprendidas solo después de revisión humana.

Flujo objetivo: `planner → coder → Blender → reviewer/verifier → planner`.
