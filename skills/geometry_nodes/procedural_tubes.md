---
name: procedural-tubes
domain: geometry_nodes
applies_to: [curve, geometry_nodes]
tools: [create_procedural_tube_setup, inspect_geometry_node_tree, evaluate_tubular, evaluate_mesh]
---

# Tubos procedurales

Usa un tubo procedural cuando necesites conservar una curva editable y cambiar
su resolución o perfil sin convertirla permanentemente en una malla. Parte de
una curva limpia y define primero su radio y trayectoria con las herramientas
de curvas.

El flujo recomendado es: curva de entrada, remuestreo solo cuando sea útil,
perfil circular y conversión a malla dentro del árbol. Expón únicamente los
parámetros que el usuario necesita ajustar, como radio de perfil y longitud de
remuestreo.

Antes de darlo por válido, inspecciona el árbol, comprueba que el modificador
apunta al grupo correcto y mide la curva o malla resultante. No uses Geometry
Nodes para ocultar una curva con puntos mal colocados o autointersecciones.
