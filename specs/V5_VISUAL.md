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

## Ciclo de corrección

El ciclo futuro será `plan → ejecutar → medir → revisar → corregir`.
Por defecto tendrá un máximo de 3 iteraciones y nunca podrá superar 5. No se
corregirá nada si las métricas y la revisión visual ya indican `pass`.

## Alcance de esta primera entrega

Se define el contrato y se enrutan las tareas visuales. La siguiente entrega
implementará capturas controladas en Blender GUI y sus pruebas reales.
