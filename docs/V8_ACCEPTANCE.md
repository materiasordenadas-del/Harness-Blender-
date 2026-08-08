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

Auto-rig, Surface Heat, SkinTokens/UniRig y retargeting son backends
experimentales posteriores. No son dependencias ni vías de ejecución V8.
