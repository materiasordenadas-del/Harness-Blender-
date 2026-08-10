# V2 Malla y modelado orgánico: evidencia de aceptación

## Operaciones entregadas

- Inspección detallada de topología y materiales.
- Recalcular/invertir normales, subdividir, suavizar, fusionar vértices,
  puente entre loops y relleno de huecos; todas con recuperación mediante
  `undo` del harness.
- Booleanos exactos (unión, diferencia e intersección), decimate y voxel remesh,
  aplicados solo de forma explícita y recuperables.
- Material Principled básico: crear, asignar, color base, rugosidad, metalizado
  y alfa.
- Modificadores con allowlist: crear, ajustar parámetros seguros, aplicar y
  eliminar de forma reversible para sus parámetros V2 conocidos.

## Límites

- La recuperación topológica conserva vértices, aristas, caras, material por
  cara y suavizado por cara. UVs, atributos personalizados y parámetros no
  expuestos de un modificador no se restauran como parte de V2.
- Los bridges, rellenos y booleanos requieren topología compatible; el bridge
  y el relleno rechazan una selección que no forme loops válidos.

## Pruebas realizadas

- Pytest del proyecto.
- Blender en segundo plano para merge, bridge, fill, boolean, decimate, voxel
  remesh, materiales y modificadores con undo.
- Escenario representativo: dos tubos cilindricos unidos con Boolean union;
  `validate_mesh` confirmó una única malla cerrada (`V2_TUBULAR_CONNECTION_OK`).
- MCP real y timer GUI: una instancia temporal creó mallas, asignó material,
  aplicó Subdivision y Boolean union, e inspeccionó la topología
  (`V2_MCP_GUI_TIMER_E2E_OK`). La instancia se cerró al terminar.
