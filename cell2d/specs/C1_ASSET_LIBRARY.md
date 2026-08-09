# C1 — Biblioteca e importación de assets 2D

## Objetivo

Incorporar masivamente assets científicos con licencia compatible, sin redibujar uno a uno ni perder su procedencia.

## Flujo obligatorio

```text
Fuente aprobada → revisión de licencia por asset → original intacto
→ catálogo y hash → importación SVG → normalización Blender → validación visual
```

## Reglas

- Cada elemento posee `asset_id` y `display_name` claros.
- Un asset original nunca se sobreescribe.
- Toda adaptación se declara como derivada y conserva atribución.
- El estilo puede normalizar escala, capas, color y etiquetas solo cuando su licencia lo permita.
- Si un asset no cabe en el estilo sin una alteración relevante, queda como candidato; no se fuerza su uso.

## Resultado de C1

Una importación por lote puede producir assets editables y trazables en Blender, listos para que C2 los coloque sobre células.
