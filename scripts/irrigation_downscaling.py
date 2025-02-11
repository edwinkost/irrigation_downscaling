
import os
import sys
import shutil
import datetime

import pcraster as pcr

import virtualOS as vos

# General steps:
# ~ 0. irr_area_5min = min(cell_area_5min, irr_area_5min)
# ~ 1. downscaled_irr_area_30sec = (irr_area_30sec / sum_irr_area_30sec) * irr_area_5min
# ~ 2. downscaled_irr_area_30sec = min(cell_area_30sec, downscaled_irr_area_30sec)
# ~ 3. remaining_irr_area_5min   = max(0.0, irr_area_5min - sum_downscaled_irr_area_30sec)
# ~ 4. downscaled_irr_area_30sec = downscaled_irr_area_30sec + (not_irr_assigned_yet_cell_area_30sec / sum_not_irr_assigned_yet_cell_area_30sec) * remaining_irr_area_5min 


class MakingNetCDF():
    
    def __init__(self, cloneMapFile, attribute = None):
        		
        # cloneMap
        # - the cloneMap must be at 5 arc min resolution
        cloneMap = pcr.readmap(cloneMapFile)
        cloneMap = pcr.boolean(1.0)
        
        # latitudes and longitudes
        self.latitudes  = np.unique(pcr.pcr2numpy(pcr.ycoordinate(cloneMap), vos.MV))[::-1]
        self.longitudes = np.unique(pcr.pcr2numpy(pcr.xcoordinate(cloneMap), vos.MV))

        # netCDF format and attributes:
        self.format = 'NETCDF4'
        self.attributeDictionary = {}
        if attribute == None:
            self.attributeDictionary['institution'] = "None"
            self.attributeDictionary['title'      ] = "None"
            self.attributeDictionary['description'] = "None"
        else:
            self.attributeDictionary = attribute

    def createNetCDF(self,ncFileName,varName,varUnit):

        rootgrp= nc.Dataset(ncFileName, 'w', format = self.format)

        #-create dimensions - time is unlimited, others are fixed
        rootgrp.createDimension('time', None)
        rootgrp.createDimension('lat', len(self.latitudes))
        rootgrp.createDimension('lon', len(self.longitudes))

        date_time= rootgrp.createVariable('time', 'f4', ('time',))
        date_time.standard_name = 'time'
        date_time.long_name = 'Days since 1901-01-01'

        date_time.units = 'Days since 1901-01-01' 
        date_time.calendar = 'standard'

        lat= rootgrp.createVariable('lat','f4',('lat',))
        lat.long_name = 'latitude'
        lat.units = 'degrees_north'
        lat.standard_name = 'latitude'

        lon= rootgrp.createVariable('lon','f4',('lon',))
        lon.standard_name = 'longitude'
        lon.long_name = 'longitude'
        lon.units = 'degrees_east'

        lat[:]= self.latitudes
        lon[:]= self.longitudes

        shortVarName = varName
        var= rootgrp.createVariable(shortVarName,'f4', ('time','lat','lon',), fill_value = vos.MV, zlib = True)
        var.standard_name = shortVarName
        var.long_name = shortVarName
        var.units = varUnit

        attributeDictionary = self.attributeDictionary
        for k, v in attributeDictionary.items():
          setattr(rootgrp,k,v)

        rootgrp.sync()
        rootgrp.close()

    def writePCR2NetCDF(self,ncFileName,varName,varField,timeStamp,posCnt):

        #-write data to netCDF
        rootgrp= nc.Dataset(ncFileName,'a')    

        shortVarName = varName        

        date_time = rootgrp.variables['time']
        date_time[posCnt] = nc.date2num(timeStamp, date_time.units, date_time.calendar)

        rootgrp.variables[shortVarName][posCnt,:,:] = (varField)

        rootgrp.sync()
        rootgrp.close()

def main():

    # output and temporary directories
    out_directory     = "/scratch-shared/edwinbar/irrigation_downscaling/test/"
    # ~ out_directory = sys.argv[1]
    tmp_directory     = out_directory + "/" + "tmp" + "/"
    # - making output and temporary directories
    if os.path.exists(out_directory):
        shutil.rmtree(out_directory)
    os.makedirs(out_directory)
    os.makedirs(tmp_directory)
    # - moving to the output directory
    os.chdir(out_directory)


    # clone map
    clone_map_file = "/projects/0/dfguu/users/edwin/data/pcrglobwb_input_arise/develop/europe_30sec/cloneMaps/clonemaps_europe_countries/rhinemeuse/rhinemeuse_30sec.map"
    pcr.setclone(clone_map_file) 
    
    
    # cell area at 30 arcsec resolution (unit: m2)
    cell_area_30sec_file = "/projects/0/dfguu/users/edwin/data/pcrglobwb_input_arise/develop/global_30sec/routing/cell_area/cdo_grid_area_30sec_map_correct_lat.nc"
    cell_area_30sec      = pcr.cover(vos.netcdf2PCRobjCloneWithoutTime(ncFile  = cell_area_30sec_file,\
                                                                       varName = "automatic", cloneMapFileName = clone_map_file, LatitudeLongitude = True, specificFillValue = None, absolutePath = None), 0.0)

    # typical/reference irrigation area fraction within 30sec cell, based on the GFSAD1KCM
    irr_area_30sec_fraction_file = "/projects/0/dfguu/users/edwin/data/GFSAD1KCM/edwin_process_on_2021-03-XX/global_irrigated_map_GFSAD1KCMv001_30sec.map"
    irr_area_30sec_fraction = vos.readPCRmapClone(v = irr_area_30sec_fraction_file, \
                                                  cloneMapFileName = clone_map_file, tmpDir = tmp_directory)
    irr_area_30sec_fraction = pcr.cover(irr_area_30sec_fraction, 0.0)
    # typical/reference irrigation area within 30sec cell (unit: m2)
    irr_area_30sec = irr_area_30sec_fraction * cell_area_30sec

    # cell area at 5 arcmin resolution (unit: m2)
    cell_area_5min_file  = "/projects/0/dfguu/users/edwin/data/pcrglobwb_input_aqueduct/version_2021-09-16/general/cdo_gridarea_clone_global_05min_correct_lats.nc"
    cell_area_5min       = pcr.cover(vos.netcdf2PCRobjCloneWithoutTime(ncFile  = cell_area_5min_file, \
                                                                       varName = "automatic", cloneMapFileName = clone_map_file, LatitudeLongitude = True, specificFillValue = None, absolutePath = None), 0.0)
    
    # cell unique id at 5 arcmin resolution
    uniqueid_5min_file = "/projects/0/dfguu/users/edwin/data/pcrglobwb_input_arise/develop/global_05min/others/uniqueids/uniqueid_5min.map"
    uniqueid_5min      = vos.readPCRmapClone(v = uniqueid_5min_file, \
                                             cloneMapFileName = clone_map_file, tmpDir = tmp_directory, absolutePath = None, isLddMap = False, cover = None, isNomMap = True)

    # upscaling typical/reference irrigation area area a 30sec cell (unit: m2) to 5min
    sum_irr_area_30sec_at_5min = pcr.areatotal(irr_area_30sec, uniqueid_5min)

    # file for the irrigation area at 5 arcmin resolution (unit: hectar)
    irr_area_5min_file   = "/projects/0/dfguu/users/edwin/data/irrigated_area_05min_meier_siebert_v20250211/irrigated_area_05min_hectar_meier_g_aei_1900_2015.nc"
    # ~ irr_area_5min_file   = sys.argv[2]
    
    # start year and end year
    staYear = 2000
    endYear = 2005
    # ~ staYear = int(sys.argv[4])
    # ~ endYear = int(sys.argv[5])
    

    # attribute for netCDF files 
    attributeDictionary = {}
    attributeDictionary['title'      ]  = "Irrigation areas - 30sec"
    attributeDictionary['institution']  = "Dept. of Physical Geography, Utrecht University"
    attributeDictionary['source'     ]  = "Downscaled from " + irr_area_5min_file + " based on " + irr_area_30sec_fraction_file
    attributeDictionary['history'    ]  = "None"
    attributeDictionary['references' ]  = "None"
    attributeDictionary['comment'    ]  = "None"
    # additional attribute defined in PCR-GLOBWB 
    attributeDictionary['description']  = "Created by Edwin H. Sutanudjaja, see https://github.com/edwinkost/irrigation_downscaling/blob/main/scripts/irrigation_downscaling.py"

    # initiate the netcd object: 
    tssNetCDF = MakingNetCDF(cloneMapFile = clone_map_file, \
                             attribute    = attributeDictionary)
    # - netcdf output variable name, file name, and unit
    output = {}
    var = "irrigationArea"
    output[var] = {}
    output[var]['file_name'] = out_directory + "/" + "irrigated_area_30sec_hectar_meier_g_aei_1900_2015_v20250211.nc"
    output[var]['unit'] = "hectar"
    tssNetCDF.createNetCDF(output[var]['file_name'], var, output[var]['unit'])
    # - index for the netcdf file
    index = 0
    
    for iYear in range(staYear, endYear+1):
        
        print(iYear)
        
        # time stamp for reading netcdf file:
        fulldate = '%4i-%02i-%02i'  %(int(iYear), int(1), int(1))

        # reading irrigation area at 5 arcmin resolution (unit: hectar)
        irr_area_5min = vos.netcdf2PCRobjClone(ncFile = irr_area_5min_file,\
                                               varName = "automatic", dateInput = fulldate, useDoy = None, cloneMapFileName  = clone_map_file, LatitudeLongitude = True, specificFillValue = None)
    
        irr_area_5min = pcr.cover(irr_area_5min, 0.0)
        # step 0: make sure that irrigation area at 5 arcmin does not exceed 5 arcmin cell area: irr_area_5min = min(cell_area_5min, irr_area_5min)
        irr_area_5min = pcr.min(irr_area_5min, cell_area_5min)
    
        # step 1: downscaling irrigation area at 5 arcmin to 30 sec: downscaled_irr_area_30sec = (irr_area_30sec / sum_irr_area_30sec) * irr_area_5min
        downscaled_irr_area_30sec  = pcr.ifthenelse(sum_irr_area_30sec_at_5min > 0.0, (irr_area_30sec / sum_irr_area_30sec_at_5min), 0.0) * irr_area_5min
                                                     
        # step 2: make sure that irrigation area at 30sec does not exceed 30sec cell area: downscaled_irr_area_30sec = min(cell_area_30sec, downscaled_irr_area_30sec)
        downscaled_irr_area_30sec  = pcr.min(downscaled_irr_area_30sec, cell_area_30sec)
        
        # step 3: calculate the remaining irrigation area at 5 arcmin that has not been assigned
        # - upscaling to 5 min
        downscaled_irr_area_30sec_at_5min = pcr.areatotal(downscaled_irr_area_30sec, uniqueid_5min)
        # - calculate the remaining: remaining_irr_area_5min   = max(0.0, irr_area_5min - sum_downscaled_irr_area_30sec)
        remaining_irr_area_5min    = pcr.max(0.0, irr_area_5min - downscaled_irr_area_30sec_at_5min)
        
        # identify the cell area at 30sec that has not been assigned as irrigated land
        # - at 30sec resolution
        not_irr_assigned_yet_cell_area_30sec             = pcr.max(0.0, cell_area_30sec - downscaled_irr_area_30sec)
        # - at 5min resolution
        sum_not_irr_assigned_yet_cell_area_30sec_at_5min = pcr.areatotal(not_irr_assigned_yet_cell_area_30sec, uniqueid_5min)
        # - TODO: Add the suitability map in this step.
        
        # step 4: assigning the remaining irrigation area at 5 arcmin to 30sec cell: downscaled_irr_area_30sec = downscaled_irr_area_30sec + (not_irr_assigned_yet_cell_area_30sec / sum_not_irr_assigned_yet_cell_area_30sec) * remaining_irr_area_5min 
        downscaled_irr_area_30sec = downscaled_irr_area_30sec + \
                                    remaining_irr_area_5min * pcr.ifthenelse(sum_not_irr_assigned_yet_cell_area_30sec_at_5min > 0.0, \
                                                                             not_irr_assigned_yet_cell_area_30sec/sum_not_irr_assigned_yet_cell_area_30sec_at_5min, 0.0)
        # ~ pcr.aguila(downscaled_irr_area_30sec)                                                                     

        # write values to a netcdf file
        var = "irrigationArea"
        ncFileName = output[var]['file_name']
        varField = pcr.pcr2numpy(downscaled_irr_area_30sec, vos.MV)
        timeStamp = datetime.datetime(int(iYear), int(1), int(1), int(0))
        tssNetCDF.writePCR2NetCDF(ncFileName, var, varField, timeStamp, posCnt = index)
        
        # update index for the next time step
        index = index + 1


if __name__ == '__main__':
    sys.exit(main())


