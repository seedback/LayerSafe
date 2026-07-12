# %%
"""Manual base placement: the user supplies each base's x position and
resting edge; this module derives y exactly as the automatic layouts do
(edge-resting plus edge_offset) and validates the result.

No packing or redistribution happens here — the user's x coordinates are
authoritative. Free y placement is not supported yet: every base rests
against the front or back edge, which is the assumption the cutout
builders' slide-path and flap-relief geometry depends on (see
docs/feature-manual-placement.md, Phase 2).

Pure math: no CAD libraries required.
"""
try:
  from .validate_positions import validate_positions, format_size
except ImportError:
  from validate_positions import validate_positions, format_size

EDGES = ('front', 'back')


def calculate_manual_cutout_positions(
    usable_area,
    sizes,
    placements,
    edge_offsets,
    tolerance,
    is_double_tray=True,
    layout_sizes=None,
    nesting='box',
):
  """Place bases at user-chosen x positions along the tray edges.

  `placements` is a per-base list of {'x': float, 'edge': 'front'|'back'}
  parallel to `sizes` ('edge' defaults to 'front'). y is derived from the
  resting edge the same way the linear layout derives it, honoring
  `edge_offsets` (which move a base inward, away from its edge).
  `layout_sizes` and `nesting` follow the conventions of the automatic
  layouts. Positions carry the input order in the 'index' key.

  Raises ValueError, naming the offending base, when a placement leaves
  the usable area or two placements overlap.
  """
  if layout_sizes is None:
    layout_sizes = [(size, size) for size in sizes]
  if isinstance(nesting, str):
    nesting = [nesting] * len(sizes)
  if len(placements) != len(sizes):
    raise ValueError(
        f"Got {len(sizes)} base sizes but {len(placements)} placements; "
        "each base needs exactly one placement."
    )

  positions = []
  for i, (size, placement) in enumerate(zip(sizes, placements)):
    edge = placement.get('edge', 'front')
    if edge not in EDGES:
      raise ValueError(
          f"Base {i + 1} ({format_size(size)}mm): unknown edge "
          f"'{edge}'. Use 'front' or 'back'."
      )
    if edge == 'back' and not is_double_tray:
      raise ValueError(
          f"Base {i + 1} ({format_size(size)}mm) is placed on the back "
          "edge, but a single-sided tray only has a front edge.\n"
          "Use edge 'front' or generate a double-sided tray."
      )
    offset = edge_offsets[i] if i < len(edge_offsets) else 0
    fy = layout_sizes[i][1]
    if edge == 'back':
      y = usable_area['max']['y'] - fy / 2 - offset
    else:
      y = usable_area['min']['y'] + fy / 2 + offset
    positions.append({
        'x': placement['x'],
        'y': y,
        'size': size,
        'index': i,
        'flipped': edge == 'back',
    })

  validate_positions(usable_area, positions, tolerance, layout_sizes,
                     nesting, name_bases=True,
                     row_rule_for_opposite_edges=True)

  return positions
