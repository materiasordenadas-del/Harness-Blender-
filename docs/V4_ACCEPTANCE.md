# Aceptación de V4 — evaluador determinista

V4 solo lee y mide la escena. Sus operaciones no crean, borran ni modifican
objetos, materiales o modificadores y tampoco escriben acciones de deshacer.

## Herramientas entregadas

- `inspect_scene_detailed`: jerarquía, colecciones, transformaciones,
  dimensiones, materiales, modificadores y conteos de mallas/curvas.
- `evaluate_mesh`: topología, bordes, caras degeneradas, normales no
  consistentes, autointersecciones, área, volumen y caja mundial.
- `evaluate_spatial`: solapamiento y distancia entre cajas mundiales.
- `evaluate_penetration`: pares de caras que se intersectan entre dos mallas.
- `evaluate_tubular`: radios, grosores, eje central, saltos y curvatura de una
  curva con bevel.
- `diff_evaluation_reports`: compara dos informes ya obtenidos, sin contactar
  Blender.

## Pruebas prácticas

1. `pytest -q`: pruebas de protocolo, cliente MCP y comparación de informes.
2. Blender 5.2 en segundo plano: ejecuta el puente real sobre una escena vacía.
   Comprueba un cubo cerrado (área 24, volumen 8), sin autointersecciones ni
   normales inconsistentes, y detecta que dos cubos separados no penetran pero
   dos cubos solapados sí.
3. Prueba manual visual: abrir Blender con una escena de dos cubos solapados y
   una curva tubular; las herramientas V4 se limitan a medir esa escena.

## Límites explícitos

- La detección de penetración verifica cruces de superficies trianguladas. No
  sustituye una simulación física ni clasifica una malla totalmente contenida
  dentro de otra sin tocar su superficie.
- La distancia espacial es entre cajas envolventes, no entre superficies exactas.
- El grosor tubular depende de `bevel_depth` y del radio de los puntos de la
  curva; no mide una malla tubular ya convertida.
