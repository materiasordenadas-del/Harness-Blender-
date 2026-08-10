# Sketchfab oficial — search/download/license candidate

## Repositorio fuente

`https://github.com/sketchfab/blender-plugin`

Licencia del plugin upstream: **Apache-2.0**.

Documentación oficial relevante:

- Data API v3
- Download API
- Download API Guidelines

## Qué se dejó en esta carpeta

- `sketchfab_adapter_candidate.py`: extracción/adaptación mínima de las responsabilidades que interesan al harness: búsqueda, detalle/metadata, solicitud de descarga, descarga del archive y preservación de datos de licencia/autor.
- `LICENSE_UPSTREAM.txt`: licencia Apache-2.0 del plugin oficial.

No se copió la UI del addon ni su lógica específica de paneles Blender. El objetivo es que Codex estudie un límite de proveedor limpio antes de integrar nada.

## Para qué sirve

Sketchfab puede funcionar como una biblioteca externa de modelos existentes. El harness podría buscar antes de modelar un asset genérico desde cero.

Flujo candidato:

```text
intent
  -> Sketchfab.search(downloadable=True)
  -> metadata + creator + license
  -> user/provider authentication
  -> request_download(uid)
  -> temporary glTF archive URL
  -> download archive
  -> IMPORT_STAGING
  -> validation
```

## Cómo puede ayudar al proyecto

- Reutilización de modelos ya existentes.
- Búsqueda por intención/palabras clave.
- Acceso a metadata útil antes de descargar.
- Preservación explícita de creador, URL del modelo y licencia.
- Reduce modelado innecesario para objetos auxiliares o ambientales.

## Restricciones importantes que Codex debe preservar

- Descargar modelos mediante el Download API requiere autenticación de un usuario de Sketchfab salvo acuerdo específico con Sketchfab.
- La URL de descarga obtenida es temporal y no debe tratarse como URL permanente/cacheable.
- La licencia Creative Commons y la atribución al creador deben viajar con el asset.
- La aplicación debe indicar claramente que los modelos descargables vienen de Sketchfab.
- No guardar tokens OAuth dentro del repositorio.

## Qué debe evaluar Codex

1. Si Sketchfab aporta suficiente valor frente al coste de OAuth/UX.
2. Si `search` debe estar disponible sin autenticar y `download` activarse solo cuando exista una sesión válida.
3. Qué licencias aceptar según el uso del proyecto.
4. Cómo serializar creator/license/source dentro de `AssetDescriptor` y Review Bundle.
5. Cómo inspeccionar tamaño/formato antes de descargar cuando sea posible.
6. Cómo desempaquetar glTF en staging sin permitir path traversal.
7. Si conviene importar glTF directamente o convertirlo primero a GLB dentro de una etapa controlada.

## Recomendación inicial

Útil, pero de menor prioridad que Poly Haven si se busca simplicidad. Su mayor coste arquitectónico es la autenticación y la obligación de transportar correctamente licencias/atribución.