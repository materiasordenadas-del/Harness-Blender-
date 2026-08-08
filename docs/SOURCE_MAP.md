# Mapa de fuentes de investigación

Este documento conecta cada componente de Harness Blender con fuentes que se deben estudiar antes de ampliar una fase. Son referencias de arquitectura y catálogo; no son dependencias ni autorización para copiar código.

| Fuente | Componente | Estudiar | No copiar |
|---|---|---|---|
| [BlenderMCP](https://github.com/MCPBlender/blender-mcp) | Bridge MCP, socket, inspección y capturas | Separación cliente/servidor/add-on y screenshots | Python arbitrario, host remoto o credenciales |
| [blender-mcp-n8n](https://github.com/seehiong/blender-mcp-n8n) | Catálogo de tools | Agrupación y nombres semánticos | Catálogo plano completo |
| [SimWorld Studio](https://github.com/SimWorld-AI/SimWorld-Studio) | Skills y verificación | Contexto bajo demanda, modelo intercambiable y verificación dual | Código y dependencias de Unreal/React |
| [SimWorld](https://github.com/SimWorld-AI/SimWorld) | Orquestación | Planner → coder → reviewer → verifier | Arquitectura de simulación física |
| [AgentCAD](https://agentcad.dev/) | Evaluador | Execute → inspect → render → validate → diff | Integración no revisada |
| [Blender API](https://docs.blender.org/api/current/) / [Manual](https://docs.blender.org/manual/en/latest/) | Autoridad técnica | Tipos y comportamiento vigente | Suposiciones que contradigan la API |
| [EZBlender](https://arxiv.org/abs/2601.07143) | Investigación V5/V9 | Plan-and-ReAct | Código o afirmaciones no verificadas |
| [ArtisanCAD](https://arxiv.org/abs/2607.05750) | Investigación V7/V9 | Skills procedurales y verificación | CAD-IR o código CATIA |

## Matriz por fase

| Fase | Fuentes prioritarias | Resultado |
|---|---|---|
| V0 | BlenderMCP | Bridge MCP, socket, capturas e inspección segura |
| V1 | BlenderMCP, blender-mcp-n8n, Blender API | Curvas y contratos tipados |
| V2 | blender-mcp-n8n, BMesh, Blender API | Topología, remesh y modifiers |
| V3 | SimWorld Studio | Skills, retrieval y contexto |
| V4 | AgentCAD, SimWorld Studio | Inspect, validate y diff |
| V5 | SimWorld Studio, EZBlender | Visión y ciclo limitado |
| V6 | Blender API/Manual, repos MCP | Recetas procedurales |
| V7 | blender-mcp-n8n, Blender API, ArtisanCAD | Producción de assets |
| V8 | Blender API/Manual, blender-mcp-n8n | Animación |
| V9 | SimWorld Studio, SimWorld, AgentCAD, EZBlender, ArtisanCAD | Orquestación |

## Regla de uso

Antes de implementar una fase, leer su sección **Source repositories**, estudiar solo lo pertinente y registrar cualquier código reutilizado en `THIRD_PARTY_NOTICES.md`. Python arbitrario por socket nunca entra en Harness Blender.
