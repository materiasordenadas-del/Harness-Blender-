# Herramientas que pueden ser agregadas

Esta rama es un staging externo e independiente de la cadena V0→V8. Su contenido no forma parte del harness activo.

Objetivo: conservar únicamente herramientas candidatas que puedan utilizarse sin pagos extra.

## Regla económica

No se aceptan proveedores que requieran comprar créditos, suscripciones, planes Pro, pago por llamada o cualquier otro gasto adicional para usar la capacidad integrada.

Se permiten cuentas gratuitas y OAuth cuando la capacidad concreta utilizada sea gratuita.

## Candidatos actuales

- `polyhaven/`: adapter contra la API oficial de Poly Haven. La API pública actual puede usarse sin pago y los assets son CC0.
- `sketchfab_official/`: búsqueda y descarga únicamente de modelos gratuitos marcados como descargables, preservando licencia y atribución. Puede requerir cuenta/OAuth, pero no se integrarán funciones que exijan planes de pago.

## Excluidos

- Meshy: retirado porque su API de generación funciona mediante créditos de pago.
- Tripo: retirado porque su API de generación es pay-before-you-go basada en créditos.

## Regla de integración futura

Nada de aquí se registra automáticamente como herramienta MCP. Codex debe decidir si cada pieza entra como adapter, operación tipada o referencia.

Arquitectura sugerida:

```text
Agent
  -> V3/Router
  -> Source Router
      -> Poly Haven
      -> Sketchfab (free downloadable only)
  -> AssetDescriptor
  -> IMPORT_STAGING
  -> validación/evaluación del harness
  -> ACCEPT / REJECT
```

## Restricciones

- No introducir `exec()` ni Python arbitrario como herramienta normal.
- No guardar tokens o credenciales en el repositorio.
- No habilitar endpoints o assets que requieran pago.
- Mantener atribución y licencias upstream.
- Descargar/importar assets primero a staging.
- Validar formato, tamaño, topología, UV y materiales antes de aceptar un asset.
- Si un proveedor cambia su política y empieza a exigir pago para la capacidad integrada, debe retirarse o deshabilitarse hasta una nueva evaluación.
