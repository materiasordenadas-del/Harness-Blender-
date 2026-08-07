# V1 Curvas: evidencia de aceptación

Estado: validado en una instancia de Blender 5.2 aislada.

## Alcance comprobado

- Curvas editables Bézier, NURBS y Poly con puntos, radio, inclinación, bevel,
  resolución y cierre de spline.
- Agregar, mover y eliminar puntos con recuperación mediante `undo` del harness.
- Tipos y posiciones de handles Bézier.
- Subdivisión, remuestreo y copia explícita de una curva evaluada a malla sin
  destruir la curva fuente.
- Entrada restringida a operaciones y parámetros tipados: no se acepta Python
  arbitrario por el socket.

## Pruebas ejecutadas

1. `pytest`: 34 pruebas pasaron.
2. Blender en segundo plano: `HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK`.
3. MCP real contra una instancia temporal de Blender: `V1_MCP_E2E_OK`.
   La prueba creó una Bézier, cambió bevel, radio y handles, subdividió y creó
   una copia en malla. La instancia temporal se cerró al terminar.

## Límites conocidos

- Inserción y eliminación de puntos se limita a curvas V1 con una sola spline.
- La subdivisión y el remuestreo interpolan los puntos de control de forma
  lineal; son operaciones explícitas y no intentan reinterpretar la curva como
  un trazado clínico o anatómico.
- La conversión crea una copia de malla con nombre indicado y conserva la curva
  editable original.
