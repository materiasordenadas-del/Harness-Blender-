# V5 — percepción visual y evaluación visual

## Objetivo

V5 añade evidencia visual a las métricas deterministas de V4. Una revisión
visual no sustituye las mediciones de malla, volumen, grosor o intersección.

## Contrato inicial

- Las vistas permitidas son `front`, `back`, `left`, `right`, `top`, `bottom`
  y `perspective`.
- Una captura puede enfocarse en un objeto por nombre y encuadrarlo.
- La evaluación debe devolver datos estructurados: `status`, `confidence` e
  `issues` con `region`, `problem` y `severity`.
- La revisión describe solo lo observable; si una imagen no permite decidir,
  debe devolver `needs_review`, no inventar un diagnóstico.
- La captura no modifica geometría, materiales ni animación. Cambiar una vista
  de la interfaz es temporal.
- La carpeta temporal debe configurarse mediante `HARNESS_BLENDER_TEMP_DIR`.
  En este proyecto se usa una carpeta dentro de `D:\Harness Blender`; el PNG se
  borra después de enviarse al MCP.

## Ciclo de corrección

El ciclo futuro será `plan → ejecutar → medir → revisar → corregir`.
Por defecto tendrá un máximo de 3 iteraciones y nunca podrá superar 5. No se
corregirá nada si las métricas y la revisión visual ya indican `pass`.

## Entrega actual

Se define el contrato, se enrutan las tareas visuales y se implementa
`capture_controlled_view` en Blender GUI. La captura acepta solo vistas fijas,
puede encuadrar un objeto por nombre y restaura la selección y la vista previa.

La siguiente entrega definirá la evaluación visual estructurada. No se activará
ninguna corrección automática hasta entonces.
