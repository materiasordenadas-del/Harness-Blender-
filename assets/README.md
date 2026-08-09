# Biblioteca de assets 2D celulares

Esta carpeta separa los recursos externos de las versiones que Harness usa en Blender.

```text
assets/
├── originals/  archivo descargado sin modificar
└── harness/    versión preparada para Blender, con metadatos Harness
```

## Regla de procedencia

Ningún archivo se añade sin una entrada correspondiente en `catalog/asset_catalog.json`.
La entrada debe conservar fuente, URL exacta, licencia, atribución necesaria y hash del archivo original.

Solo se importan por lote assets cuya licencia permita copiar y adaptar. El catálogo empezará admitiendo CC0, CC BY 4.0 y MIT. Cualquier otra licencia queda en revisión antes de descargar o distribuir el asset.

Los originales no se editan. Si se normaliza un SVG para Harness, el resultado va en `harness/` y se declara como derivado en el catálogo.
