# Herramientas que pueden ser agregadas

Esta rama es un **staging externo e independiente de la cadena V0→V8**. Su contenido no debe considerarse parte del harness activo.

Objetivo: dejar material listo para que Codex evalúe qué conviene implementar después.

## Carpetas

- `tripo_official/`: backend y ejemplos oficiales MIT de Tripo, más una propuesta de adaptación al contrato del harness.
- `meshy_agent_skills/`: skill oficial de Meshy para generación 3D, conservado como material candidato para V3.
- `polyhaven/`: adapter pequeño escrito contra la API oficial de Poly Haven.
- `sketchfab_official/`: extracción/documentación para search, download, metadata, licencias y atribución desde el plugin oficial.

## Regla de integración futura

Nada de aquí se registra automáticamente como herramienta MCP. Codex debe decidir si cada pieza entra como skill, adapter, operación tipada o simplemente referencia.

Arquitectura sugerida:

```text
Agent
  -> V3/Router
  -> Source Router
      -> Poly Haven
      -> Sketchfab
      -> Tripo
      -> Meshy
  -> AssetDescriptor
  -> IMPORT_STAGING
  -> validación/evaluación del harness
  -> ACCEPT / REJECT
```

## Restricciones

- No introducir `exec()` ni Python arbitrario como herramienta normal.
- No guardar API keys.
- Mantener atribución y licencias upstream.
- Descargar/importar assets primero a staging.
- Validar formato, tamaño, topología, UV y materiales antes de aceptar un asset.
- Mantener los proveedores desacoplados mediante un contrato común.