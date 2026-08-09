# C0 — Cell Diagram Style Foundation

## Objetivo

Crear el contrato visual mínimo y verificable que todas las células 2D del Harness deberán respetar antes de construir anatomía o fisiología específica.

C0 no crea todavía un atlas celular completo. C0 fija la gramática gráfica.

## Canvas

- Cámara: ortográfica.
- Orientación: perpendicular al plano XY.
- Fondo: neutro claro configurable por style contract.
- Layout: X/Y para composición; Z solo para orden visual.

## Capas Z obligatorias

| Layer | Z base | Uso |
|---|---:|---|
| background | 0.00 | fondo y paneles |
| cell_body | 0.05 | citoplasma / cuerpo celular |
| organelles | 0.10 | núcleo, mitocondrias, RE, Golgi, vesículas |
| membrane | 0.20 | membrana y especializaciones |
| membrane_proteins | 0.30 | canales, bombas, receptores |
| pathways | 0.40 | proteínas, iones, segundos mensajeros |
| arrows | 0.50 | flujo, activación, inhibición |
| labels | 0.60 | texto y anotaciones |

Las operaciones futuras deben colocar elementos en la capa apropiada y rechazar categorías desconocidas.

## Categorías visuales iniciales

- membrane
- cytoplasm
- organelle
- ion_channel
- pump
- exchanger
- receptor
- signaling_protein
- second_messenger
- ion
- vesicle
- activation_arrow
- inhibition_line
- transport_arrow
- label

## Reglas visuales

- La membrana usa siempre el mismo material semántico y line weight.
- Los canales/transportadores/receptores comparten una familia gráfica común, aunque sus iconos puedan distinguir subtipos.
- Las proteínas de señalización usan otra familia visual consistente.
- Los iones y segundos mensajeros son símbolos compactos con etiqueta legible.
- Las flechas nunca deben utilizarse como sustituto de una medición o relación no sustentada por el perfil fisiológico.
- Ningún color se decide ad hoc por célula: los colores salen del style contract.
- La anatomía puede deformar la silueta celular, pero no cambiar las reglas de símbolo, tipografía o línea.

## Biblioteca C0

La primera escena de referencia futura deberá contener al menos:

- segmento de membrana;
- cuerpo celular simple;
- núcleo;
- mitocondria;
- canal;
- bomba;
- GPCR/receptor genérico;
- proteína señalizadora;
- ion;
- vesícula;
- flecha de activación;
- línea inhibitoria;
- label.

## Validaciones deterministas C0

El Harness debe poder validar sin visión:

- categoría conocida;
- layer Z correcta;
- material semántico registrado;
- grosor de línea dentro del contrato;
- tamaño de texto dentro de los rangos definidos;
- nombres únicos cuando corresponda;
- ausencia de valores no finitos;
- paleta únicamente desde el contrato.

La revisión visual se reserva para consistencia perceptual, solapamientos complejos y composición.

## Fuera de alcance C0

- perfiles celulares específicos;
- consulta automática de CellML;
- localización automática de proteínas;
- layout automático de vías;
- animación;
- generación automática de morfología a partir de imágenes.

## Acceptance C0

PASS cuando:

1. exista un style contract versionado;
2. su esquema pueda validarse de forma determinista;
3. todas las categorías y capas tengan contratos explícitos;
4. se pueda construir después una escena golden-reference sin decisiones visuales arbitrarias del agente;
5. ninguna operación C0 introduzca Python arbitrario, red adicional o dependencia externa de ejecución.