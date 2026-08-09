# Hoja de ruta: atlas celular 2D

## Paso 1 — Consolidar C0

Validar el contrato visual ya creado con una escena de muestra: cámara ortográfica, capas, paleta, líneas y etiquetas.

## Paso 2 — C1: catálogo e importación por lote

1. Elegir fuentes y licencias permitidas.
2. Buscar assets por familias, no proteína por proteína.
3. Registrar licencia, atribución, URL, hash y estado en el catálogo.
4. Guardar el original intacto e importar SVG en Blender.
5. Normalizar solo las propiedades permitidas por la licencia.

## Paso 3 — C2: intérprete y reconstructor de referencias

1. Registrar una imagen, SVG o dibujo con su hash y procedencia.
2. Recibir observaciones revisables de un agente visual o del usuario.
3. Reutilizar assets canónicos registrados y aplicar el estilo Harness.
4. Enviar a revisión los elementos ambiguos, no registrados o de baja confianza.

## Paso 4 — C3: constructor 2D seguro

Crear operaciones tipadas para importar un asset, crear una instancia, asignar su nombre semántico y colocarlo por dominio celular. No se aceptará Python arbitrario.

Estado actual: `create_cell2d_symbol` está disponible en el bridge y crea mallas o texto 2D editables con metadatos de identidad, dominio y procedencia.

## Paso 5 — C4: Style Pack Cell2D v1

1. Fijar la apariencia objetivo del proyecto para membranas, organelos, proteínas, iones, flechas y texto.
2. Incorporar únicamente assets con fuente, licencia y atribución verificadas.
3. Adaptar los assets permitidos al estilo objetivo sin cambiar su significado biológico.
4. Crear una lámina Blender de referencia y aprobarla visualmente antes de usarla en células.

El manifiesto de esta etapa vive en `cell2d/style_packs/harness_cell_diagram_v1/`. No se considera completada hasta que existan assets visuales aprobados y una revisión en Blender.

## Paso 6 — C5: dos células piloto

Construir y revisar un enterocito y una célula principal del túbulo colector. El objetivo es probar anatomía polarizada, dominios y colocación de assets.

## Paso 7 — C6: biblioteca de células

Incorporar podocito, neurona, célula beta pancreática y cardiomiocito usando la misma estructura. Cada perfil se respalda con evidencia visual y de localización antes de añadir componentes.

## Paso 8 — C7: calidad y exportación

Validar licencias, nombres, capas, ausencia de solapamientos, legibilidad y fidelidad al estilo antes de exportar una imagen o archivo Blender.

## Criterio de avance

Una etapa solo termina cuando deja un resultado visible en Blender y una validación automática o revisión documentada.
