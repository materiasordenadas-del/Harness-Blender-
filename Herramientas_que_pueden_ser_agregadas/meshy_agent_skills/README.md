# Meshy Agent Skills — candidato para V3

## Repositorio fuente

`https://github.com/meshy-dev/meshy-3d-agent`

Licencia upstream revisada: **MIT**.

## Qué se copió

- `UPSTREAM_SKILL.md`: copia del skill oficial `skills/meshy-3d-generation/SKILL.md` para evaluación sin modificar su intención ni mezclarlo todavía con V3.
- `SKILL.md`: variante reducida/adaptada dejada únicamente para que Codex compare qué instrucciones realmente merece la pena conservar en el harness.
- `LICENSE_UPSTREAM.txt`: licencia MIT del repositorio fuente.

El `reference.md` completo de Meshy es un archivo generado y muy grande. No se duplica aquí en esta primera bandeja de evaluación; el README conserva el repositorio y la ruta exacta upstream (`skills/meshy-3d-generation/reference.md`) para que Codex decida si debe vendorizarse, indexarse como documentación externa o mantenerse fuera del contexto normal.

## Para qué se copió

El valor principal de este repositorio no es una nueva capa MCP. Es conocimiento operativo ya escrito para agentes:

- text-to-3D;
- image-to-3D y multi-image-to-3D;
- retexture;
- remesh;
- convert/resize/UV unwrap;
- auto-rigging;
- animation;
- polling y descarga de resultados;
- manejo de errores, formatos y coste/créditos.

## Cómo puede ayudar al proyecto

V3 ya tiene el concepto correcto: seleccionar solamente conocimiento relevante para la tarea. Este skill puede ampliar lo que el agente sabe hacer con un provider externo sin agregar decenas de herramientas al contexto global.

Flujo candidato:

```text
prompt
  -> V3 detecta intención external-3d
  -> carga Meshy skill
  -> provider adapter
  -> tarea asíncrona
  -> asset descargado
  -> IMPORT_STAGING
  -> validación del harness
```

## Qué debe adaptar Codex

El archivo upstream asume herramientas de agente como Bash/Read/Write/Glob/Grep y un CLI propio de Meshy. No debe registrarse literalmente sin revisión.

Codex debe decidir:

1. Qué metadata conservar para el `SkillRegistry` del harness.
2. Sustituir llamadas shell por un provider tipado si eso reduce superficie de ejecución.
3. Mantener la regla de no gastar créditos sin autorización explícita.
4. Mantener las API keys fuera del repositorio.
5. Evitar que instrucciones propias de Claude/Cursor se conviertan accidentalmente en políticas globales del harness.
6. Mantener el skill cargado bajo demanda, no en cada prompt.
7. Si `reference.md` debe indexarse externamente en lugar de entrar en cada contexto.

## Recomendación inicial

**Alta prioridad como fuente de conocimiento de V3**, pero adaptar el contrato y no asumir que todas sus instrucciones de runtime son apropiadas para Harness-Blender.