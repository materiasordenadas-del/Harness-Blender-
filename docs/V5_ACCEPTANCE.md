# Aceptación parcial de V5 — captura visual controlada

Esta entrega añade evidencia visual controlada; todavía no decide si una forma
es anatómicamente correcta ni modifica la escena automáticamente.

## Herramienta disponible

`capture_controlled_view` acepta únicamente `front`, `back`, `left`, `right`,
`top`, `bottom` o `perspective`. Puede enfocar un objeto por nombre y
encuadrarlo. Devuelve un PNG por MCP y restaura la vista y la selección previas.

La herramienta exige Blender GUI. En modo `--background` devuelve un error
explícito, porque allí no hay un viewport real que capturar.

## Pruebas realizadas

- Pruebas de protocolo: vistas no permitidas y parámetros extra se rechazan.
- Blender en segundo plano: confirma que la captura se rechaza por requerir GUI.
- Blender GUI real: crea un cubo, toma una vista frontal enfocada, valida la
  firma PNG y confirma que selección y objeto activo se restauran.
- Los temporales, incluido el archivo de recuperación de Blender, se dirigieron
  a `D:\Harness Blender\.tmp-v5`; no se escribió un temporal nuevo en C:.
