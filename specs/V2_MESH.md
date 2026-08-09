# V2 — Malla y modelado orgánico

## Source repositories

### blender-mcp-n8n
https://github.com/seehiong/blender-mcp-n8n

Estudiar: categorías de booleans, remesh, topology y modifiers. No copiar tools sin límites o sin recuperación.

### Blender API y BMesh
https://docs.blender.org/api/current/bmesh.html

Estudiar: conectividad y operaciones BMesh. La API oficial tiene prioridad.

## Alcance

V2 permite operaciones topológicas tipadas sobre objetos `MESH`, después de que
una curva se haya convertido de forma explícita. El bridge conserva el mismo
principio de V0/V1: recibe una operación permitida y parámetros validados; nunca
recibe código Python generado por el modelo.

## Primer bloque de herramientas

| Herramienta | Efecto | Recuperación |
|---|---|---|
| `inspect_mesh_detailed` | Informa topología, manifold, normales y materiales | No modifica |
| `recalculate_normals` | Reorienta las normales hacia fuera o dentro | Restaura las normales previas |
| `flip_normals` | Invierte las normales de todas las caras | Restaura las normales previas |
| `subdivide_mesh` | Subdivide toda la malla de 1 a 4 cortes | Restaura la malla previa |
| `smooth_mesh` | Suaviza posiciones de vértices con factor limitado | Restaura la malla previa |
| `decimate_mesh` | Añade un modificador Decimate permitido | Se elimina mediante `remove_modifier` |
| `add_modifier`, `set_modifier_parameter`, `apply_modifier`, `remove_modifier` | Gestiona una lista limitada de modificadores | Según la operación |
| `create_material`, `assign_material`, `set_base_color`, `set_roughness`, `set_metallic`, `set_alpha` | Material básico Principled | Restaura el valor anterior |

Las operaciones de loops, booleans, remesh por vóxeles y cierre de huecos se
añaden progresivamente después de validar este bloque en Blender real.

## Límites de seguridad

- Solo se aceptan objetos `MESH` y nombres existentes.
- Índices, ratios, factores y cortes tienen límites explícitos.
- La lista inicial de modificadores es: `SUBSURF`, `SOLIDIFY`, `SHRINKWRAP`,
  `SMOOTH`, `LAPLACIANSMOOTH`, `DECIMATE`, `REMESH` y `BOOLEAN`.
- Las operaciones topológicas usan BMesh cuando no requieran una selección GUI.
- No se aplican booleanos ni remesh destructivos automáticamente como efecto
  secundario de otra herramienta.

## Escenario de aceptación V2

1. Crear dos tubos y convertir una copia a malla.
2. Inspeccionar su topología y normales.
3. Suavizar o subdividir con límites controlados.
4. Aplicar un modificador permitido de forma explícita.
5. Asignar un material básico y comprobar sus valores.
6. Validar en pytest, Blender en segundo plano, GUI/timer y MCP real.
