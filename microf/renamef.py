import re


#### For CV7000 ################ 
CV7000 = '{}_{}_T0001F{}L01A01Z01C{}.tif'

#### For IC6000 only #############

# This is the filename type being parsed
# C_13_fld_2_wv_405_Blue.tif
# 20180328_TestAbs_G - 8(fld 4 wv Red - Cy5).tif

def _IC6000_replace(params, channels):
    exp_name = params['n'].replace("_","")
    well_letter = params['w'].replace(" ","").split('-')[0]
    well_number = params['w'].replace(" ","").split('-')[1].zfill(2)
    site = str(params['s'].zfill(3))
    channel = channels[params['c'].replace(" ","")]
    return exp_name, well_letter+well_number, site, channel
 

IC6000 = {
        'pattern': r'(?P<n>.*_.*)_(?P<w>[A-Z]\D*\d*)\(fld\D*(?P<s>\d*)\D*wv(?P<c>.*)\).(tif|png)',
        'channels': {'UV-DAPI':'01',
                     'Blue-FITC':'02',
                     'Green-dsRed':'03',
                     'Red-Cy5':'04'},
        'replace': _IC6000_replace

        }   



