# Harness Blender

Harness Blender convierte un agente compatible con MCP —Codex, Kimi Code, Claude Code u otro— en un operador estructurado de Blender.

La **V0** demuestra un núcleo pequeño y verificable:

```text
Agente MCP
    ↓
Servidor Harness Blender (Python externo)
    ↓  TCP loopback: operation + params + token
Add-on Harness Blender Bridge
    ↓  cola → hilo principal de Blender
Operaciones V0 cerradas / bpy
```

## Qué incluye V0

- Conexión exclusivamente por loopback entre el agente y Blender.
- Herramientas MCP tipadas.
- El socket **no acepta Python**, `code` ni `exec` remoto.
- Allowlist cerrada de diez operaciones Blender.
- Validación de parámetros también dentro del add-on, no solo en MCP.
- Token aleatorio generado localmente al activar el add-on.
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

Esas capas se construirán después de estabilizar V0 en Blender real.

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
6. Activa **Online Access** si Blender lo solicita para sockets.
7. En las preferencias de Harness Blender Bridge confirma:
   - Host: `127.0.0.1`
   - Port: `9876`
   - Auto Start: activado
8. El add-on genera automáticamente un **Access Token aleatorio**. Pulsa **Copy Token** y guárdalo para el paso MCP. No uses un token público compartido.

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

### 4. Configurar el cliente MCP

Usa `config/mcp.example.json` como referencia y reemplaza:

```text
<COPY_GENERATED_TOKEN_FROM_BLENDER_PREFERENCES>
```

por el token generado en Blender. El servidor externo **no tiene token por defecto** y se negará a operar si `BLENDER_TOKEN` está vacío.

### 5. Probar

Con Blender abierto y el bridge activo, pide al agente:

```text
Usa blender_ping. Luego inspecciona la escena. Crea un cubo llamado V0_Test, muévelo a [2, 0, 1] y valida su malla.
```

## Seguridad de V0

El protocolo del socket solo admite:

```json
{
  "type": "operation",
  "operation": "create_primitive",
  "params": {},
  "token": "..."
}
```

El add-on rechaza campos desconocidos, operaciones fuera de la allowlist, vectores mal formados, valores no finitos y rutas de guardado no absolutas. El bridge permanece en `127.0.0.1`; no lo expongas a una red pública.

`capture_blender_screen` no acepta una ruta proporcionada por el cliente: Blender captura a un archivo temporal interno y devuelve el PNG codificado en base64.

## Pruebas

Pruebas normales:

```powershell
python -m pytest
```

Prueba de integración con Blender en modo background:

```powershell
blender --background --factory-startup --python tests/blender_background_integration.py
```

Esta prueba comprueba ping, inspección, creación, transformación, validación, borrado y recuperación mediante undo. La captura de pantalla requiere Blender gráfico y permanece como prueba manual.

V0 **no debe fusionarse a `main`** hasta ejecutar además la secuencia end-to-end descrita en `docs/V0_ACCEPTANCE.md` con el servidor MCP y el add-on realmente conectados.

## Estructura

```text
blender_addon/               Add-on instalado dentro de Blender
src/harness_blender/         Servidor MCP externo
skills/                      Reglas y conocimiento operativo
config/                      Ejemplos de configuración MCP
docs/                        Arquitectura y alcance
scripts/                     Empaquetado del add-on
tests/                       Pruebas unitarias e integración Blender
```

## Licencia y procedencia

El repositorio se publica bajo GPL-3.0-or-later. La arquitectura del bridge fue contrastada con el add-on MCP de Blender Lab 1.0.0 aportado como referencia, pero la implementación V0 fue escrita específicamente para este repositorio. Consulta `THIRD_PARTY_NOTICES.md`.
