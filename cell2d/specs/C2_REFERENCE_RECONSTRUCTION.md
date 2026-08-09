# C2 — Intérprete y reconstructor de referencias

## Objetivo de la primera fase

Transformar un análisis revisado de una imagen, SVG o dibujo en un plan de escena canónico, trazable y preparado para Blender.

## Garantías

- Se registra el archivo de referencia con nombre, formato, hash, URL opcional y estado de derechos.
- La identidad biológica no se adivina: el análisis propone y el plan reutiliza solo assets registrados.
- Un elemento con confianza menor a 0.80, categoría visual desconocida o asset no registrado queda en revisión.
- El plan asigna la categoría y el estilo Harness, pero aún no crea objetos Blender. Esa operación segura corresponde a la fase siguiente.

## Límite explícito

La interpretación automática de píxeles requiere un agente o modelo visual conectado. Esta fase define y valida el contrato entre ese intérprete y Blender; por ello permite que Codex o el usuario aporten observaciones revisables sin que el programa invente datos.

## Resultado

Un `reconstruction plan` contiene instancias canónicas reutilizables, sus posiciones relativas, dominio celular, estilo de destino y una lista de ambigüedades.
