# Cell2D

Módulo independiente de Harness Blender para crear diagramas celulares 2D editables.

`cell2d` utiliza la infraestructura general de Harness —conexión segura con Blender, curvas, materiales, inspección y exportación—, pero conserva aquí sus reglas visuales, assets, catálogos, plantillas y especificaciones.

## Estructura

```text
cell2d/
├── assets/     originales licenciados y versiones para Blender
├── catalog/    identidad, licencia y procedencia de cada asset
├── config/     contrato de estilo
├── docs/       hoja de ruta
├── skills/     reglas de uso del módulo
├── specs/      requisitos verificables
└── templates/  anatomía base reutilizable de cada tipo celular
```

El código que implementa este módulo vive en `src/harness_blender/cell2d/`.
