# V7 — contrato inicial de producción de assets

## Alcance de este primer paso

V7 comienza por una comprobación de preparación del asset. No altera la escena:
reúne datos ya disponibles antes de autorizar sculpt, retopología o UV.

## Habilidad `asset-validation`

Entrada: el nombre confirmado de un objeto `MESH`.

Comprobaciones obligatorias:

1. La malla existe y su topología fue inspeccionada.
2. Se registran vértices, aristas, caras, bordes abiertos, aristas sueltas y
   no-manifold.
3. Se registran las transformaciones, el nombre y las colecciones del objeto.
4. Se registra si hay al menos un material asignado.
5. La malla se evalúa para caras degeneradas, normales inconsistentes e
   intersecciones consigo misma.

Resultado: `ready`, `needs_review` o `blocked`, con una lista explícita de las
comprobaciones que fallaron. La habilidad no corrige, no aplica modificadores y
no crea UVs.

## Límites y recuperación

Esta primera entrega es de solo lectura, así que no necesita undo. Las futuras
operaciones V7 que editen geometría o UV deberán declarar su propia copia de
seguridad y una prueba de undo antes de incorporarse.

## Criterio de aceptación de contrato

- La habilidad aparece en el registro local.
- Su contrato exige inspección de escena y malla antes de evaluar el asset.
- Solo utiliza herramientas existentes de lectura o evaluación.
- La suite unitaria comprueba ese registro.
- `evaluate_asset_readiness` devuelve un estado sin cambiar la escena.

## Inspección UV

`inspect_uv` es una operación de solo lectura para una malla confirmada. Reporta
si existen mapas UV, cuál está activo y, por mapa, el nombre, la cantidad de
coordenadas y sus límites. No crea mapas UV, no calcula islas ni modifica las
coordenadas; esas operaciones requieren un contrato reversible posterior.

`unwrap_uv` usa `ANGLE_BASED` o `CONFORMAL` con un margen limitado. Antes de
desplegar, guarda todos los mapas UV y sus coordenadas; `undo` restaura ese
estado completo. No analiza solapes ni decide automáticamente qué método usar.
