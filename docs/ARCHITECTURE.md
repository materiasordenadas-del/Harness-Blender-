# Arquitectura V0

## Decisión principal

La IA no vive dentro de Blender. El proceso externo expone MCP; Blender recibe únicamente **operaciones semánticas tipadas** y las ejecuta mediante una lista cerrada de handlers. Ningún fragmento de Python viaja por el socket.

## Fuentes de investigación por fase

La metodología y las fuentes externas se mantienen en
[`SOURCE_MAP.md`](SOURCE_MAP.md). Cada especificación de fase repite las fuentes
que debe estudiar antes de implementar. Las referencias inspiran patrones; la
API oficial de Blender es la autoridad técnica y el bridge de Harness nunca
acepta Python arbitrario.

## Componentes

### 1. Agente

Puede ser Codex, Kimi Code, Claude Code u otro cliente MCP. El repositorio no depende de un proveedor concreto.

### 2. Servidor MCP externo

`src/harness_blender/server.py` registra las herramientas visibles para el agente.

Responsabilidades:

- mapear cada herramienta MCP a un nombre de operación V0;
- enviar `operation + params + token` al bridge;
- convertir resultados a JSON o imagen;
- no disponer de ninguna ruta `execute_python`.

### 3. Transporte

`src/harness_blender/connection.py` abre conexiones TCP únicamente a loopback. `BLENDER_TOKEN` es obligatorio; no existe token operativo por defecto.

La petición tiene esta forma:

```json
{
  "type": "operation",
  "operation": "transform_object",
  "params": {
    "object_name": "Cube",
    "location": [2, 0, 1]
  },
  "token": "..."
}
```

### 4. Bridge de Blender

`blender_addon/harness_blender_bridge/__init__.py` abre el socket TCP local. El worker de red no llama a `bpy`; autentica y valida la solicitud, la coloca en una cola y `bpy.app.timers` ejecuta el trabajo en el hilo principal.

El token se genera con `secrets.token_urlsafe(32)` al activar el add-on por primera vez y queda almacenado en sus preferencias. Puede copiarse o regenerarse desde la UI.

### 5. Validador de protocolo

`blender_addon/harness_blender_bridge/bridge_protocol.py` es Python puro y testeable fuera de Blender. Define:

- allowlist de operaciones V0;
- esquema de parámetros por operación;
- límites de nombres, vectores y rutas;
- rechazo de campos desconocidos;
- comparación constante del token.

Este validador es la frontera de seguridad. Incluso un cliente local que conozca el puerto no puede enviar un campo `code` ni inventar una operación nueva.

### 6. Registro de operaciones

`blender_addon/harness_blender_bridge/operations.py` contiene los diez handlers V0 reales. El dispatcher solo puede ejecutar nombres presentes en `OPERATIONS`.

`delete_object` usa `bpy.ops.object.delete` para integrarse con el historial de undo de Blender. `validate_mesh` reporta por separado:

- `boundary_edges`: un solo face enlazado;
- `loose_edges`: cero faces enlazados;
- `non_manifold_edges`: más de dos faces enlazados.

### 7. Contexto y ciclo de revisión

`config/skill_contracts.json` convierte cada skill en datos revisables: fuente,
sinónimos de intención, precondiciones, herramientas permitidas, validación,
fallos comunes y límites. El router usa esas señales para formar un Task Packet
de máximo tres skills, sin agregar herramientas ajenas.

Antes de ejecutar, `build_scene_task_packet` captura el estado real de Blender.
Si no hay objetos o tipos compatibles, devuelve bloqueos y permite únicamente
inspección. Después, `build_review_bundle_from_snapshots` implementa el patrón
inspirado en AgentCAD: `inspect → execute typed operation → inspect/render →
validate → diff → decision`.

El bundle registra estado antes/después, operaciones semánticas, diff por objeto,
regresiones geométricas y revisión visual opcional. Solo puede guardarse una vez
en `HARNESS_EVIDENCE_DIR`; no ejecuta scripts ni corrige la escena por sí solo.

`config/benchmarks.json` mide cinco tareas repetibles de enrutamiento. Los
candidatos de herramientas permanecen no ejecutables hasta tener contrato,
recuperación, pruebas unitarias, Blender background, GUI, MCP E2E y escenario de
aceptación documentados.

### 8. Skills

Los `.md` explican cómo debe razonar el agente: inspeccionar antes de modificar, utilizar operaciones mínimas y validar después. No sustituyen al software ejecutable.

## Flujo de una operación

```text
Usuario: crea un cilindro
        ↓
Agente selecciona create_primitive
        ↓
Servidor MCP construye params
        ↓
connection.py envía operation + params + token
        ↓
bridge_protocol autentica y valida
        ↓
Bridge encola la operación
        ↓
Timer de Blender → operations.py
        ↓
Resultado JSON
        ↓
Agente inspecciona o valida
```

## Límite deliberado

La V0 demuestra transporte, seguridad básica y contrato de herramientas. Planner, router, retrieval y evaluator todavía no son procesos independientes. El modelo usa el skill de planificación como política inicial.
