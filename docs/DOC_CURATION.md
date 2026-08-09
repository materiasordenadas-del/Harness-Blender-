# Curación de documentación oficial

El índice operativo solo contiene resúmenes propios de documentación oficial de Blender. No descarga repositorios externos ni incorpora código de terceros.

Para añadir una entrada:

1. Registrar la pregunta técnica en `research/extractions/` y enlazar una fuente de `config/sources.json`.
2. Confirmar que la URL es HTTPS bajo `docs.blender.org` y anotar versión y fecha de revisión.
3. Escribir un resumen corto, keywords y las skills relacionadas en `src/harness_blender/docs_index.py`.
4. Añadir o actualizar el contrato de la skill en `config/skill_contracts.json`.
5. Crear una prueba de búsqueda y una prueba de Task Packet. No copiar texto extenso ni indexar repositorios externos.

La revisión es manual y versionada. Una fuente externa puede inspirar un hallazgo curado, pero nunca entra al RAG operativo como corpus.
