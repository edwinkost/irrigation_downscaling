
import pcraster as pcr

# General steps:
# ~ 0. irr_area_5min = min(cell_area_5min, irr_area_5min)
# ~ 1. downscaled_irr_area_30sec = (irr_area_30sec / sum_irr_area_30sec) * irr_area_5min
# ~ 2. downscaled_irr_area_30sec = min(cell_area_30sec, downscaled_irr_area_30sec)
# ~ 3. remaining_irr_area_5min   = max(0.0, irr_area_5min - sum_downscaled_irr_area_30sec)
# ~ 4. downscaled_irr_area_30sec = downscaled_irr_area_30sec + (not_irr_assigned_yet_cell_area_30sec / sum_not_irr_assigned_yet_cell_area_30sec) * remaining_irr_area_5min 


# clone map
clone_map_file = "/scratch/depfg/sutan101/data/pcrglobwb_input_arise/develop/europe_30sec/cloneMaps/clonemaps_europe_countries/rhinemeuse/rhinemeuse_30sec.map"

# output and tmp directories
output_dir =
tmp_dir    = output_dir + "/" + tmp_dir
# - create output and tmp directories

# irrigation area at 5 arcmin resolution
irr_area_5min_file = "/scratch/depfg/sutan101/irrigated_area_30sec/develop/irrigated_area_05min_hectar_meier_g_aei_1900_2015.nc"
irr_area_5min      = vos.netcdf2PCRobjClone(ncFile  = irr_area_5min_file,\
                                            varName = "automatic",
                                            dateInput = None,\
                                            useDoy = None,
                                            cloneMapFileName  = clone_map_file,\
                                            LatitudeLongitude = True,\
                                            specificFillValue = None)

# cell area at 5 arcmin resolution
cell_area_5min_file = "/scratch/depfg/sutan101/irrigated_area_30sec/develop/cdo_gridarea_clone_global_05min_correct_lats.nc"
cell_area_5min      = vos.netcdf2PCRobjClone(ncFile  = cell_area_5min_file,\
                                             varName = "automatic",
                                             dateInput = None,\
                                             useDoy = None,
                                             cloneMapFileName  = clone_map_file,\
                                             LatitudeLongitude = True,\
                                             specificFillValue = None)
                                             
# step 0: irr_area_5min = min(cell_area_5min, irr_area_5min)
irr_area_5min      = pcr.min(irr_area_5min, cell_area_5min)


# cell area at 30 arcsec resolution
cell_area_30sec_file = "/scratch/depfg/sutan101/irrigated_area_30sec/develop/cdo_gridarea_clone_global_05min_correct_lats.nc"
cell_area_30sec      = vos.netcdf2PCRobjClone(ncFile  = cell_area_30sec_file,\
                                              varName = "automatic",
                                              dateInput = None,\
                                              useDoy = None,
                                              cloneMapFileName  = clone_map_file,\
                                              LatitudeLongitude = True,\
                                              specificFillValue = None)

# typical/reference irrigation area fraction within a 30sec cell, based on the GFSAD1KCM
irr_area_30sec_fraction_file = "/scratch/depfg/sutan101/data/GFSAD1KCM/edwin_process_on_2021-03-XX/global_irrigated_map_GFSAD1KCMv001_30sec.map"
irr_area_30sec_fraction = vos.netcdf2PCRobjClone(ncFile  = irr_area_30sec_fraction_file,\
                                             varName = "automatic",
                                             dateInput = None,\
                                             useDoy = None,
                                             cloneMapFileName  = clone_map_file,\
                                             LatitudeLongitude = True,\
                                             specificFillValue = None)
# typical/reference irrigation area area a 30sec cell (unit: m2)
irr_area_30sec = irr_area_30sec_fraction * cell_area_30sec


# cell unique id at 5 arcmin resolution
uniqueid_5min_file = "/scratch/depfg/sutan101/irrigated_area_30sec/develop/uniqueid_5min.map"
uniqueid_5min      = vos.readPCRmapClone(v = uniqueid_5min_file, \
                                         cloneMapFileName = clone_map_file, \
                                         tmpDir, absolutePath = None, isLddMap = False, cover = None, isNomMap = True)

# upscaling typical/reference irrigation area area a 30sec cell (unit: m2) t0 5min- STILL TODO
sum_irr_area_30sec_at_5min = pcr.areatotal(irr_area_30sec, uniqueid_5min)


# step 1: downscaled_irr_area_30sec = (irr_area_30sec / sum_irr_area_30sec) * irr_area_5min
downscaled_irr_area_30sec  = pcr.ifthenelse(sum_irr_area_30sec_at_5min > 0.0, (irr_area_30sec / sum_irr_area_30sec_at_5min), 0.0) * irr_area_5min

                                             
# step 2: downscaled_irr_area_30sec = min(cell_area_30sec, downscaled_irr_area_30sec)
downscaled_irr_area_30sec  = pcr.min(downscaled_irr_area_30sec, cell_area_30sec)
# - upscaling to 5 min
downscaled_irr_area_30sec_at_5min = pcr.areatotal(downscaled_irr_area_30sec, uniqueid_5min)


# step 3 remaining_irr_area_5min   = max(0.0, irr_area_5min - sum_downscaled_irr_area_30sec)
remaining_irr_area_5min    = pcr.max(0.0, irr_area_5min - downscaled_irr_area_30sec_at_5min)

# identify the cell area at 30sec that has not been assigned as irrigated land
not_irr_assigned_yet_cell_area_30sec     = pcr.max(0.0, cell_area_30sec - downscaled_irr_area_30sec)
sum_not_irr_assigned_yet_cell_area_30sec = pcr.areatotal(not_irr_assigned_yet_cell_area_30sec, not_irr_assigned_yet_cell_area_30sec)


# 4. downscaled_irr_area_30sec = downscaled_irr_area_30sec + (not_irr_assigned_yet_cell_area_30sec / sum_not_irr_assigned_yet_cell_area_30sec) * remaining_irr_area_5min 
downscaled_irr_area_30sec = downscaled_irr_area_30sec + \
                            pcr.ifthenelse(sum_not_irr_assigned_yet_cell_area_30sec > 0.0, not_irr_assigned_yet_cell_area_30sec/sum_not_irr_assigned_yet_cell_area_30sec, 0.0) * remaining_irr_area_5min

