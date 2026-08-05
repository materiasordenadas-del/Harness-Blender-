# Arquitectura V0

## Decisión principal

La IA no vive dentro de Blender. Blender ejecuta únicamente el bridge y las operaciones `bpy`; el proceso externo expone MCP y traduce herramientas semánticas a código controlado.

## Componentes

### 1. Agente

Puede ser Codex, Kimi Code, Claude Code u otro cliente MCP. El repositorio no depende de un proveedor concreto.

### 2. Servidor MCP externo

`src/harness_blender/server.py` registra las herramientas visibles para el agente.

Responsabilidades:

- validar parámetros;
- elegir una plantilla de código conocida;
- comunicarse con Blender;
- convertir resultados a JSON o imagen;
- impedir Python arbitrario en V0.

### 3. Bridge de Blender

`blender_addon/harness_blender_bridge/` abre un socket TCP local. El worker de red no llama a `bpy`: coloca las solicitudes en una cola y un `bpy.app.timers` las ejecuta en el hilo principal de Blender.

### 4. Plantillas de operación

`code_templates.py` contiene pequeñas unidades de ejecución. Son código, no prompts. Cada plantilla corresponde a una capacidad concreta y testeable.

### 5. Skills

Los `.md` explican cómo debe razonar el agente: inspeccionar antes de modificar, utilizar operaciones mínimas y validar después. No sustituyen a las herramientas Python.

## Flujo de una operación

```text
Usuario: crea un cilindro
        ↓
Agente selecciona create_primitive
        ↓
FastMCP valida primitive/name/location/scale
        ↓
code_templates crea código bpy controlado
        ↓
connection.py envía JSON por localhost:9876
        ↓
Bridge encola la solicitud
        ↓
Timer de Blender ejecuta en el hilo principal
        ↓
Resultado JSON
        ↓
Agente inspecciona o valida
```

## Límite deliberado

La V0 demuestra el transporte y el contrato de herramientas. El planner, router y evaluator todavía no son procesos independientes. El modelo usa el skill de planificación como política inicial.
