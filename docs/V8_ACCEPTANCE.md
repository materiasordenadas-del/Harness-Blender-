# V8 — base segura de rigging y animación

## Alcance inicial

V8 empieza con rigs manuales declarados en JSON. No ejecuta auto-rig externo,
no modifica la topología y no acepta scripts arbitrarios.

Un perfil define el objeto, el rig, la raíz y articulaciones con un rol genérico:
`ROOT`, `CORE`, `BASE`, `SEGMENT` o `END_EFFECTOR`. La articulación `BASE`
permite proteger la inserción de una rama antes del primer segmento móvil.

## Orden de entrega

1. Validar perfil e inspeccionar la escena sin editar.
2. Crear armature, huesos y jerarquía desde el perfil; conservar undo.
3. Aplicar skinning de Blender y validar pesos.
4. Crear poses FK y keyframes; después acciones y curvas.
5. Añadir constraints e IK solo con allowlist y pruebas de deformación.

## V8.0 â€” estructura manipulable

Completada el 2026-08-08. Se incorporaron `inspect_movable_structure`,
`prepare_movable_structure`, `list_movable_parts`, `get_part_state` y
`reset_structure`. Para curvas, cada spline se presenta como `Process_01`,
`Process_02`, etc.; `Core` queda fijo. Para mallas, la segmentaciÃ³n automÃ¡tica
queda para V8.2.

Prueba funcional en Blender 5.2: preparar una curva, consultar su parte,
restaurar y deshacer dejÃ³ la curva sin registro de preparaciÃ³n. No cambia
geometrÃ­a, pesos ni huesos.

Auto-rig, Surface Heat, SkinTokens/UniRig y retargeting son backends
experimentales posteriores. No son dependencias ni vías de ejecución V8.
