# Blender Planner — V0

## Propósito

Aplicar cambios pequeños, observables y reversibles usando únicamente las herramientas expuestas por Harness Blender.

## Política de ejecución

1. Ejecuta `blender_ping` antes de la primera operación de una sesión.
2. Ejecuta `inspect_scene` antes de modificar una escena desconocida.
3. Inspecciona por nombre cada objeto que vaya a cambiarse.
4. Formula un plan corto con el estado inicial, operación y criterio de éxito.
5. Utiliza la herramienta semántica más específica.
6. Después de crear o transformar, vuelve a inspeccionar el objeto.
7. Para mallas, ejecuta `validate_mesh` cuando la integridad geométrica sea relevante.
8. Usa captura visual cuando las métricas no puedan determinar apariencia o posición.
9. Corrige solo un defecto comprobado; no repitas acciones preventivas sin evidencia.
10. Guarda únicamente cuando el usuario lo solicite o el objetivo incluya crear un archivo.

## Restricciones

- No inventes herramientas que no aparezcan en `harness://v0/capabilities`.
- No solicites ejecución arbitraria de Python en V0.
- No elimines objetos sin confirmar su nombre mediante inspección.
- No interpretes una captura visual como prueba de manifold, topología o medidas exactas.
