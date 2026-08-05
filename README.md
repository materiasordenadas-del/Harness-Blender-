# Harness Blender

Harness Blender convierte un agente compatible con MCP —Codex, Kimi Code, Claude Code u otro— en un operador estructurado de Blender.

La **V0** no intenta modelar cualquier cosa todavía. Su objetivo es demostrar un núcleo estable y verificable:

```text
Agente MCP
    ↓
Servidor Harness Blender (Python externo)
    ↓  TCP local, JSON delimitado por byte nulo
Add-on Harness Blender Bridge
    ↓  ejecución en el hilo principal de Blender
Blender / bpy
```

## Qué incluye V0

- Conexión local entre el agente y Blender.
- Herramientas MCP tipadas; el modelo no envía Python arbitrario.
- Inspección de escena y objetos.
- Creación de primitivas.
- Transformación y eliminación de objetos.
- Validación básica de mallas.
- Guardado y deshacer.
- Captura de la interfaz de Blender para inspección visual.
- Primer skill de planificación y política de seguridad.

## Qué no incluye todavía

- Geometry Nodes.
- Sculpt.
- Rigging y animación avanzada.
- Recuperación automática de Blender Docs.
- Evaluador visual autónomo.
- Memoria persistente.
- Bucle completo de corrección.

Esas capas se construirán después de probar que la conexión y las herramientas básicas son fiables.

## Instalación rápida en Windows

### 1. Crear el ZIP del add-on

Desde la raíz del repositorio:

```powershell
python scripts/build_addon.py
```

Se crea:

```text
dist/harness_blender_bridge-0.1.0.zip
```

### 2. Instalar el add-on en Blender 5.1+

1. Abre Blender.
2. Ve a **Edit → Preferences → Get Extensions**.
3. Abre el menú de la esquina superior derecha.
4. Selecciona **Install from Disk**.
5. Elige `dist/harness_blender_bridge-0.1.0.zip`.
6. Activa **Online Access** en las preferencias de Blender; el bridge solo escucha en `localhost`, pero Blender exige ese permiso para sockets.
7. En las preferencias del add-on, confirma:
   - Host: `localhost`
   - Port: `9876`
   - Auto Start: activado
   - Access Token: `harness-v0-local` (puedes cambiarlo, pero debe coincidir con `BLENDER_TOKEN`)

### 3. Instalar el servidor externo

Con `uv`:

```powershell
uv sync
```

O con Python:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 4. Configurar tu cliente MCP

Usa `config/mcp.example.json` como referencia. El comando debe iniciar:

```text
harness-blender
```

### 5. Probar

Con Blender abierto y el bridge activo, pide al agente:

```text
Usa blender_ping. Luego inspecciona la escena. Crea un cubo llamado V0_Test, muévelo a [2, 0, 1] y valida su malla.
```

## Seguridad de V0

V0 no expone una herramienta de `execute_python(code)` al modelo. Cada herramienta MCP genera internamente código controlado y validado. El add-on subyacente puede ejecutar Python porque ése es el mecanismo de transporte, pero el agente solo recibe operaciones semánticas limitadas.

El bridge debe permanecer enlazado a `localhost`. No lo expongas a una red pública.

## Estructura

```text
blender_addon/               Add-on instalado dentro de Blender
src/harness_blender/         Servidor MCP externo
skills/                      Reglas y conocimiento operativo
config/                      Ejemplos de configuración MCP
docs/                        Arquitectura y alcance
scripts/                     Empaquetado del add-on
tests/                       Pruebas fuera de Blender
```

## Licencia y procedencia

El repositorio se publica bajo GPL-3.0-or-later. La arquitectura del bridge fue contrastada con el add-on MCP de Blender Lab 1.0.0 aportado como referencia, pero la implementación V0 del bridge fue escrita específicamente para este repositorio. Consulta `THIRD_PARTY_NOTICES.md`.
