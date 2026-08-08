# Aceptación parcial de V5 — captura visual controlada

Esta entrega añade evidencia visual controlada y un controlador limitado. No
incluye un modelo de visión propio ni modifica la escena automáticamente.

## Herramienta disponible

`capture_controlled_view` acepta únicamente `front`, `back`, `left`, `right`,
`top`, `bottom` o `perspective`. Puede enfocar un objeto por nombre y
encuadrarlo. Devuelve un PNG por MCP y restaura la vista y la selección previas.

La herramienta exige Blender GUI. En modo `--background` devuelve un error
explícito, porque allí no hay un viewport real que capturar.

## Informe y límite de corrección

Un cliente con visión aporta un informe estructurado con `status`, `confidence`
e incidencias con `region`, `problem` y `severity`. Harness rechaza campos o
valores no válidos. Con `pass` o `needs_review` se detiene; con
`needs_correction` solo autoriza otra corrección hasta tres veces por defecto,
nunca más de cinco. Esta autorización no ejecuta cambios por sí sola.

## Comparación con referencia

`build_visual_review_capture_plan` exige tres llamadas individuales a
`capture_controlled_view`, en este orden fijo: `front`, `right`, `perspective`.
Un modelo de visión externo compara esas imágenes con la referencia entregada
por el usuario y devuelve un paquete validado por
`validate_visual_comparison_report`.

El paquete guarda un identificador de referencia, el objeto, las tres vistas,
regiones emparejadas entre referencia y resultado, y el informe visual. Harness
no interpreta los píxeles, no inventa la referencia y no corrige Blender por su
cuenta. El paquete se adjunta al Review Bundle junto con el diff V4.

## Pruebas realizadas

- Pruebas de protocolo: vistas no permitidas y parámetros extra se rechazan.
- Blender en segundo plano: confirma que la captura se rechaza por requerir GUI.
- Blender GUI real: crea un cubo, toma una vista frontal enfocada, valida la
  firma PNG y confirma que selección y objeto activo se restauran.
- Los temporales, incluido el archivo de recuperación de Blender, se dirigieron
  a `D:\Harness Blender\.tmp-v5`; no se escribió un temporal nuevo en C:.
