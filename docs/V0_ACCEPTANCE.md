# Criterios de aceptación de V0

V0 **no se considera estable ni debe fusionarse a `main`** hasta completar los tres niveles siguientes.

## A. Pruebas automáticas fuera de Blender

- [x] `python -m pytest` pasa completamente.
- [x] El bridge no contiene `exec()` ni acepta un campo `code`.
- [x] Un token incorrecto es rechazado.
- [x] Una operación desconocida es rechazada.
- [x] Campos y parámetros desconocidos son rechazados.
- [x] Vectores de tamaño incorrecto, valores no finitos o fuera de límites son rechazados.
- [x] No existe un token operativo fijo por defecto.

## B. Integración con Blender en modo background

Ejecutar con Blender 5.1+:

```text
blender --background --factory-startup --python tests/blender_background_integration.py
```

Debe finalizar mostrando:

```text
HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK
```

La prueba comprueba:

1. ping;
2. inspección de escena;
3. creación de un cubo;
4. transformación;
5. inspección del objeto;
6. validación de malla;
7. separación correcta entre `boundary_edges`, `loose_edges` y `non_manifold_edges`;
8. borrado mediante una operación compatible con undo;
9. `undo` recupera el objeto borrado.

## C. End-to-end real MCP ↔ Blender gráfico

Con el add-on instalado y Blender abierto:

1. El add-on genera un token aleatorio al activarse.
2. Copiar ese token a `BLENDER_TOKEN` del servidor MCP.
3. `blender_ping` devuelve la versión de Blender.
4. `inspect_scene` enumera los objetos existentes.
5. `create_primitive` crea `V0_Test`.
6. `transform_object` lo mueve a `[2, 0, 1]`.
7. `inspect_object` confirma esa transformación.
8. `validate_mesh` informa `boundary_edges=0` y `non_manifold_edges=0` para el cubo cerrado.
9. `delete_object` elimina `V0_Test`.
10. `undo_last_action` recupera `V0_Test`.
11. `capture_blender_screen` devuelve un PNG válido.
12. `save_blend` guarda un `.blend` de prueba en una ruta absoluta.
13. Una petición con token incorrecto es rechazada.
14. Una petición manual al socket que incluya `code` es rechazada aunque el token sea correcto.

Registrar versión exacta de Blender, sistema operativo y resultado de cada paso antes de fusionar PR #1.

## Registro de validación

Validado el 2026-08-07 en Windows con Blender 5.2.0 LTS.

- Pruebas unitarias: `19 passed`.
- Blender background: `HARNESS_BLENDER_BACKGROUND_INTEGRATION_OK`.
- GUI/timer: creación, borrado y recuperación validados desde el mismo tipo de timer que usa el bridge.
- MCP E2E: add-on instalado, servidor MCP real por stdio y bridge TCP local; las diez herramientas V0 completaron el escenario de aceptación.
- Seguridad por socket: token incorrecto, campo `code`, operación desconocida y parámetro inválido fueron rechazados.
