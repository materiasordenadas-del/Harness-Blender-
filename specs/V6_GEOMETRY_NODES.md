# V6 — Geometry Nodes

## Objetivo

V6 permite crear estructuras procedurales reutilizables sin exponer un MCP tool
por cada nodo interno de Blender. La primera receta es un tubo procedural:
curva de entrada, remuestreo opcional, perfil circular y conversión a malla.

## Contrato

- Las herramientas reciben un objeto de curva o un nombre explícito de grupo.
- Los árboles se crean como `GeometryNodeTree` y se adjuntan mediante un
  modificador Geometry Nodes identificable.
- Las recetas usan nombres estables de sockets y nodos comprobados en Blender
  5.2 local.
- Las operaciones que creen o cambien un árbol registrarán una estrategia de
  recuperación antes de modificarlo.
- La inspección devolverá nodos, enlaces, interfaz expuesta y objeto asociado.

## Recetas iniciales

- `procedural_tube`: curva → resample opcional → Curve Circle → Curve to Mesh.
- `curve_resampling`: remuestrea una curva con longitud o cantidad explícita.
- `radius_control`: permite variar el radio antes de convertir a malla.

## Fuera de alcance inicial

- No se exponen decenas de nodos individuales.
- No se aceptan scripts Python por MCP.
- Instancing, scatter y ramificación procedural quedan para entregas posteriores
  de V6, después de probar el tubo base.
