# V1 — Curvas y estructuras tubulares

## Alcance

V1 añade curvas editables de tipo Bézier, NURBS y Poly. Todas las operaciones
reciben nombres, índices y valores tipados; el bridge no recibe Python.

## Contrato de seguridad

- Solo se aceptan objetos `CURVE` creados o existentes en la escena.
- Las coordenadas, radios, tilt, resoluciones e índices se validan en el
  bridge antes de llegar a Blender.
- Una curva conserva al menos dos puntos por spline.
- Las acciones destructivas registran una recuperación reversible en memoria
  de Harness Blender V1.
- `convert_curve_to_mesh` es explícita e irreversible fuera del undo de
  Harness; nunca se ejecuta como efecto secundario de crear o editar curvas.

## Herramientas V1

| Herramienta | Efecto | Recuperación |
|---|---|---|
| `create_curve` | Crea una curva 3D con una spline | Elimina la curva creada |
| `inspect_curve` | Informa geometría y ajustes | No modifica |
| `add_curve_point`, `move_curve_point`, `remove_curve_point` | Edita puntos | Restaura el estado previo |
| `set_curve_handle_type`, `set_curve_handle_position` | Edita handles Bézier | Restaura el estado previo |
| `set_curve_point_radius`, `set_curve_point_tilt` | Edita perfil por punto | Restaura el estado previo |
| `set_curve_bevel_depth`, `set_curve_bevel_resolution`, `set_curve_resolution`, `set_curve_cyclic` | Edita propiedades de spline | Restaura el estado previo |
| `subdivide_curve`, `resample_curve` | Cambia puntos de forma explícita | Restaura el estado previo |
| `convert_curve_to_mesh` | Convierte la curva a una malla | Recuperación mediante undo del harness |

## Escenario de aceptación

1. Crear una curva Bézier con 8–12 puntos y otra curva auxiliar.
2. Aplicar radios con progresión proximal mayor que distal y un bevel circular.
3. Editar trayectoria, handles, un punto y la inclinación de un punto.
4. Inspeccionar la curva y confirmar que sigue siendo editable.
5. Convertir una copia explícita a mesh y validar su topología.
6. Comprobar en background, GUI/timer y MCP E2E.
