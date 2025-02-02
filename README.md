# irrigation_downscaling
This repo contains the scripts for downscaling irrigation areas (from a coarse spatial resolution).


Steps:

0. irr_area_5min = min(cell_area_5min, irr_area_5min)

1. downscaled_irr_area_30sec = (irr_area_30sec / sum_irr_area_30sec) * irr_area_5min

2. downscaled_irr_area_30sec = min(cell_area_30sec, downscaled_irr_area_30sec)

3. remaining_irr_area_5min   = max(0.0, irr_area_5min - sum_downscaled_irr_area_30sec)

4. downscaled_irr_area_30sec = downscaled_irr_area_30sec + (cell_area_30sec / sum_cell_area_30sec) * surplus_irr_area_5min 

TODO: The step 4 can be improved by a suitability map (e.g. avoiding steep areas and surface water areas).
