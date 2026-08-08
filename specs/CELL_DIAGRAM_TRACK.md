# Cell Diagram Track

## Objetivo

Añadir a Harness Blender una línea de trabajo 2D científica para crear diagramas celulares editables en Blender con una identidad visual constante, anatomía adaptada al tipo celular y overlays fisiológicos reutilizables.

El sistema debe separar tres capas:

1. **Cell Profile** — identidad, morfología, polaridad, compartimentos y estructuras relevantes.
2. **Physiology Overlay** — canales, bombas, receptores, iones, segundos mensajeros, vías y flechas.
3. **Style System** — gramática visual única para todos los tipos celulares.

El objetivo final es que un agente pueda recibir una instrucción como:

> Crea una célula principal del túbulo colector en estilo Harness y representa la vía de ADH con V2R, cAMP, PKA y AQP2.

Y produzca una escena Blender 2D editable, científicamente razonable y visualmente consistente con el resto del atlas.

## Principios

- Blender sigue siendo el motor de composición y exportación.
- La escena usa cámara ortográfica y coordenadas X/Y para layout; Z se reserva para capas visuales.
- No se copian assets gráficos de CellML ni de otras fuentes.
- Las fuentes científicas aportan identidad, morfología, localización y fisiología; Harness genera sus propios símbolos y composición.
- El estilo visual no depende del tipo celular: cambia la anatomía, no la gramática gráfica.
- El usuario no debe necesitar conocer Blender.
- Las operaciones seguirán siendo tipadas; no se introduce Python arbitrario por MCP.

## Fuentes científicas previstas

Las fuentes externas se registrarán mediante la capa de integración ya existente.

- CellML: fisiología, variables, conexiones y modelos matemáticos.
- Cell Ontology: identidad y clasificación celular.
- Gene Ontology: componentes y compartimentos celulares.
- Human Protein Atlas: localización subcelular y tisular cuando aplique.
- Human Cell Atlas: contexto de tipos y estados celulares.
- Referencias morfológicas seleccionadas y revisadas por licencia.

Blender API/Manual siguen siendo la autoridad técnica para implementación.

## Arquitectura objetivo

```text
User task
   ↓
Cell resolver
   ↓
Cell Profile + Physiology Overlay
   ↓
Diagram Planner
   ↓
Style Engine
   ↓
Typed 2D Blender tools
   ↓
Blender orthographic scene
   ↓
Deterministic validation + controlled visual review
```

## Track de fases

### C0 — Style Foundation

Define cámara, capas Z, paleta semántica, tipografía, line weights, categorías visuales y contratos de símbolos. No intenta crear células completas todavía.

### C1 — Cell Body & Organelles

Formas celulares, membrana, núcleo y organelos básicos editables.

### C2 — Membrane Proteins & Molecular Symbols

Canales, bombas, intercambiadores, receptores, proteínas señalizadoras, iones y vesículas.

### C3 — Pathways & Labels

Flechas, inhibición, transporte transmembrana, etiquetas, conectores y layout de vías.

### C4 — Scientific Cell Profiles

Perfiles versionados por tipo celular con morfología, polaridad, compartimentos y localización funcional.

### C5 — CellML Adapter

Adaptador que transforma componentes/variables/conexiones CellML en un grafo fisiológico utilizable por el Diagram Planner sin tratar CellML como autoridad morfológica.

### C6 — Auto-layout & Review

Layout automático acotado, validaciones geométricas 2D, detección de solapamientos y revisión visual controlada.

### C7 — Optional Physiology Animation

Animación opcional de flujos, cambios de estado, translocación de proteínas y señalización manteniendo el mismo estilo.

## Regla de integración

Este track reutiliza las capas existentes de Harness Blender:

- source registry;
- skills;
- Task Packet;
- evidence/review bundle;
- visual review;
- operaciones tipadas y seguridad de bridge.

No duplica esas infraestructuras.

## Criterio de éxito del track

Dos células diferentes deben ser anatómicamente distinguibles pero visualmente reconocibles como parte del mismo sistema Harness.

La consistencia debe poder validarse en parte de forma determinista: materiales, categorías, grosor de línea, capas Z, tipografía, nombres de símbolos y reglas de layout.