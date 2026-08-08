# V6 — Geometry Nodes

## Source repositories

### Blender Python API y Manual
https://docs.blender.org/api/current/
https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/

Estudiar: árboles, interfaz y sockets actuales. La API oficial tiene prioridad.

### BlenderMCP y blender-mcp-n8n
https://github.com/MCPBlender/blender-mcp
https://github.com/seehiong/blender-mcp-n8n

Estudiar: nombres semánticos y agrupación de capacidades. No copiar ejecución arbitraria ni exponer cada nodo como tool.

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
- `surface_scatter`: superficie MESH + instancia separada → puntos sobre caras → instancias, con densidad explícita y Undo.
- `procedural_branching`: curva principal + ramas CURVE → unión de curvas → remuestreo → tubo, con Undo.

## Fuera de alcance inicial

- No se exponen decenas de nodos individuales.
- No se aceptan scripts Python por MCP.
- No se fusionan automáticamente las ramas en una única malla ni se aplican los
  modificadores sin una solicitud explícita.
