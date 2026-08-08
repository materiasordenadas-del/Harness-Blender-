# Cell 2D Style Contract

## Use when

Creating, editing or reviewing any 2D scientific cell diagram in Harness Blender.

## Goal

Preserve a single visual language across different cell types while allowing each cell to retain its real biological morphology, polarity and characteristic structures.

## Required procedure

1. Resolve the requested cell type and purpose before drawing.
2. Separate base cell anatomy from physiology overlay.
3. Load `config/cell_diagram_style.json`.
4. Use only registered symbol categories and semantic palette entries.
5. Keep all composition in XY and use the registered Z layer for each category.
6. Preserve orthographic presentation.
7. Reuse standard symbol families instead of inventing a new icon for each cell.
8. Change cell silhouette and organelle distribution only when required by the cell profile.
9. Do not infer protein localization solely from visual convention; require a curated scientific source or explicit user instruction.
10. Validate deterministic style constraints before requesting visual review.

## Style invariants

- Membranes always use the membrane visual family.
- Membrane proteins use the membrane-protein family.
- Signaling proteins use the signaling-protein family.
- Arrows and inhibition marks follow the registered pathway style.
- Labels use the logical sans family and registered size limits.
- Colors are semantic and come only from the style palette.
- Cell-specific overrides require an explicit style version change; they are not ad-hoc agent decisions.

## Common failures

- drawing every cell with the same silhouette;
- changing colors between cell types;
- using perspective rendering for a diagram intended to be orthographic;
- placing labels behind arrows or membranes;
- converting pathway arrows into decorative rather than physiological relationships;
- mixing anatomy and physiology so the same base cell cannot be reused;
- copying symbols or artwork from external scientific diagrams.

## Validation

Deterministic:

- style contract loads successfully;
- symbol categories resolve to registered layers/materials;
- layer Z is correct;
- no unregistered palette value is used;
- text settings remain inside the contract.

Visual review:

- overall composition remains readable;
- symbols do not overlap labels unnecessarily;
- the cell remains recognizable as the requested biological type;
- the diagram still looks like part of the same Harness visual family.
