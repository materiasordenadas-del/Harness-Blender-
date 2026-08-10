# blender-llm-addin — piezas candidatas

Fuente upstream: `mac999/blender-llm-addin`.

Este directorio conserva únicamente las ideas y piezas reutilizables para una futura **Expert Execution Lane** de Harness Blender. No está conectado al MCP, no modifica V0 y no convierte `exec()` en una herramienta normal.

## Qué se conserva

- extracción de bloques Python generados por un modelo;
- validación sintáctica previa con `ast.parse()` / `compile()`;
- ejecución de Python en modo explícitamente confiable;
- captura estructurada de `stdout`, `stderr`, excepción y traceback;
- bucle de retry/corrección desacoplado del proveedor de IA mediante un callback `fixer`;
- límite de intentos configurable.

## Qué se descarta del upstream

- panel UI para escribir prompts dentro de Blender;
- clientes OpenAI/Ollama embebidos en Blender;
- claves API dentro del script;
- selección fija de modelos;
- prompt interno del add-on;
- comprobación de seguridad basada en buscar palabras con `split()`;
- retry que solo devuelve texto y no un resultado estructurado.

## Por qué puede ser útil al harness

La arquitectura futura puede mantener dos rutas:

```text
Agent / Codex
  -> Planner
  -> Router
      -> Semantic Operations     (ruta normal)
      -> Expert Execution Lane   (ruta privilegiada)
             -> script generado en workspace
             -> validación AST
             -> Bridge
             -> main thread de Blender
             -> ejecución bpy/bmesh/mathutils
             -> resultado estructurado
             -> evaluator / corrección
```

La pieza de este directorio cubre únicamente el núcleo de la segunda ruta. No implementa transporte, autenticación, acceso al filesystem del proyecto, main-thread dispatch ni política de permisos; esas responsabilidades pertenecen al Harness Blender.

## Estado

**Candidato aislado. No producción. No registrado como tool MCP.**

Antes de integrarlo en el harness activo se debe decidir:

1. cómo se habilita/deshabilita Expert Mode;
2. si el agente envía código o, preferiblemente, una referencia a un script del workspace;
3. qué metadatos y hashes se registran;
4. cómo se integra con undo/checkpoints;
5. qué límites de tiempo y memoria se aplican;
6. cómo se devuelve el diff de escena al Evaluator.

## Procedencia

El upstream declara licencia MIT en su README. La adaptación de este directorio elimina la integración específica con OpenAI/Ollama y conserva solo el patrón genérico de ejecución/corrección que puede ser evaluado dentro de la arquitectura del harness.
