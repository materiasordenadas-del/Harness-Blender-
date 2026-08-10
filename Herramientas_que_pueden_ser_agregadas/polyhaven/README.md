# Poly Haven — adapter candidato

## Fuente

API oficial: `https://api.polyhaven.com`

Documentación pública: `https://polyhaven.com/our-api`

No se copió un addon de terceros. Este candidato se escribió específicamente para Harness-Blender contra la API oficial.

## Qué se escribió

- `polyhaven_adapter_candidate.py`

El adapter cubre únicamente:

- obtención del catálogo `/assets`;
- búsqueda local sobre metadata;
- obtención del árbol de archivos `/files/{asset_id}`;
- selección determinista de una variante de archivo;
- descarga a una ruta explícita;
- verificación MD5 cuando la API la proporciona.

No llama `bpy`, no registra herramientas MCP y no inserta automáticamente nada en una escena.

## Para qué sirve

Dar al agente acceso a assets humanos ya construidos —modelos, texturas y HDRIs— antes de decidir modelarlos desde cero.

Flujo candidato:

```text
intent
  -> PolyHavenAdapter.search()
  -> asset id + metadata
  -> choose_file()
  -> download()
  -> IMPORT_STAGING
  -> validación del harness
```

## Cómo puede ayudar al proyecto

- Reduce trabajo innecesario de modelado de props genéricos.
- Aporta texturas y HDRIs de alta calidad.
- La metadata del catálogo incluye información útil para routing y validación, como tipo de asset y, cuando existe, polycount/dimensiones.
- El adapter puede permanecer fuera del contexto MCP hasta que V3 determine que una búsqueda de assets es relevante.

## Condiciones actuales de la API que Codex debe preservar

- Usar un `User-Agent` identificable en las peticiones.
- Mostrar claramente a los usuarios que los assets obtenidos mediante la API en vivo provienen de Poly Haven.
- Los assets de Poly Haven son CC0; las condiciones de uso de la API en vivo son independientes de la licencia CC0 del asset.

## Qué debe evaluar Codex

1. Si este adapter se ubica detrás de `SourceRouter`.
2. Si el catálogo debe cachearse con TTL para no descargar `/assets` repetidamente.
3. Cómo convertir metadata a `AssetDescriptor`.
4. Qué formatos/resoluciones permitir mediante allowlist.
5. Límites de tamaño antes de descargar assets grandes.
6. Cómo incorporar atribución de la fuente en evidencia/UI aunque el asset sea CC0.
7. Cómo hacer staging e importación sin mezclar descarga de red con operaciones Blender.

## Recomendación inicial

Alta prioridad. Es una integración pequeña, no requiere API key y puede ahorrar muchas operaciones de modelado en tareas donde ya existe un asset adecuado.