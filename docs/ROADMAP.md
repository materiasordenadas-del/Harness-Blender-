# Roadmap

Las fuentes que orientan cada fase están en [SOURCE_MAP.md](SOURCE_MAP.md) y en la sección obligatoria **Source repositories** de cada especificación.

| Fase | Estado | Entrega principal |
|---|---|---|
| V0 — núcleo seguro | ✅ | Bridge loopback con token, MCP y operaciones tipadas |
| V1 — curvas | ✅ | Curvas editables, tubos y radios variables |
| V2 — malla | ✅ | Topología, modifiers y materiales básicos |
| V3 — conocimiento | ✅ | Skills, docs index y router |
| V4 — evaluador | ✅ | Inspección, métricas y diff determinista |
| V5 — visión | ✅ | Capturas GUI, informe visual y ciclo limitado |
| V6 — Geometry Nodes | ✅ | Tubos, scatter y ramificación procedurales reversibles |
| V7 — producción | ✅ | Sculpt localizado, retopo recuperable, UV recuperable, materiales Principled y validación de asset |
| V8 — animación | Pendiente | Rigging, shape keys, constraints y keyframes |
| V9 — orquestación | Pendiente | Planner, estado, reviewer y recetas revisadas |

Cada fase debe seguir: rama → implementación → pruebas unitarias → Blender background → GUI cuando aplique → MCP E2E → PR → revisión → merge → tag.
