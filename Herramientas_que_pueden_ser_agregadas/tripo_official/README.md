# Tripo oficial — candidato de integración

## Repositorios fuente

- Plugin oficial Blender: `https://github.com/VAST-AI-Research/tripo-3d-for-blender`
- SDK Python oficial: `https://github.com/VAST-AI-Research/tripo-python-sdk`

Licencia upstream revisada: **MIT**.

## Qué se copió aquí

Se conservaron ejemplos oficiales pequeños del SDK que muestran los workflows esenciales:

- `upstream_text_to_model.py`
- `upstream_image_to_model.py`
- `LICENSE_UPSTREAM.txt`

Además se añadió `tripo_adapter_candidate.py`, que **no es copia literal**: es una propuesta mínima de adaptación para que Codex evalúe cómo envolver Tripo detrás de una interfaz del harness.

No se copió el plugin completo ni su UI. Tampoco se copió su servidor Blender completo porque el objetivo no es introducir una segunda arquitectura MCP dentro del harness.

## Para qué se copió

Tripo puede añadir una capacidad que el harness no necesita reconstruir con herramientas de modelado: generar una malla base desde texto o imagen y devolverla como asset externo para posterior inspección y refinamiento.

Flujo objetivo:

```text
prompt / image
  -> Tripo adapter
  -> task id
  -> polling
  -> GLB descargado
  -> IMPORT_STAGING
  -> validación del harness
  -> corrección/refinado
```

## Cómo puede ayudar al proyecto

- Text-to-3D para prototipos y assets auxiliares.
- Image-to-3D cuando existe una referencia visual clara.
- Multiview-to-3D como posible ruta de mayor control.
- Descarga automatizada de GLB/modelos generados.
- Permite que el agente decida entre modelar desde cero o comenzar desde una base generada.

## Qué debe evaluar Codex antes de implementar

1. Si conviene depender directamente de `tripo-python-sdk` o escribir un cliente HTTP más pequeño.
2. Qué operaciones deben exponerse al agente: `generate`, `status`, `download/import`, y no toda la API.
3. Coste/créditos y necesidad de confirmación antes de crear tareas pagadas.
4. Gestión segura de `TRIPO_API_KEY` mediante entorno, nunca dentro del repositorio.
5. Validación del archivo descargado antes de introducirlo en una escena de producción.
6. Cómo mapear el resultado a un `AssetDescriptor` común.

## Recomendación inicial

Integrar Tripo como **provider externo**, no como herramientas de modelado Blender. El proveedor debe terminar en un asset descargado; el harness conserva el control sobre inspección, modificación, evaluación y aceptación.