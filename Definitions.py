#!/usr/bin/env python3

from __future__ import print_function
#import cbdm as cbdm
#import do_ill2mets as mets
import pandas as pd
import os
import argparse
import numpy as np

import glob
import subprocess

from pathlib import Path
import csv
import time
start_time = time.time()


#Read Rad files
def read_radfiles():
    Rad_filenames = sorted(glob.glob('RAD_files/Case001_3d.rad'))
    return Rad_filenames
#Read Mat files
def read_matfiles():
    Mat_filenames = sorted(glob.glob('RAD_files/Case001_3d.mat'))
    return Mat_filenames
#Read Climate files
def read_climfiles():
    Clim_filenames = sorted(glob.glob('Climatefiles/*.epw'))
    return Clim_filenames


def getArgs():
        parser = argparse.ArgumentParser(description='Create illuminance profiles with the 2-phase method')
        parser.add_argument('-mf', type=int, default=2,
                        help='sky subdivision factor')
        parser.add_argument('-ts', type=int, default=60,
                        help='time step (minutes)')
    #    parser.add_argument('-r', type=int, default=0,
    #                    help='sky rotation (degrees west of north)')
        parser.add_argument('pts', type=str, nargs='+',
                        help='sensor points list file path, multiple entries allowed')

        args = parser.parse_args()
        return args



def makesmx(clim_fn, Rad_file, mf, ts=60, north=0):
    mf = int(mf)

    clim, clim_ext = os.path.splitext(clim_fn)
    clim_f_name = os.path.basename(clim)

    #Folder with climate filename
    if not os.path.exists('%s' % clim_f_name):
        os.makedirs('%s' % clim_f_name)

    Rad_f_name = os.path.basename(Rad_file)
    Rad_f_name = os.path.splitext(Rad_f_name)[0]
    if not os.path.exists('%s/%s' % (clim_f_name,Rad_f_name)):
        os.makedirs('%s/%s' % (clim_f_name,Rad_f_name))

    if not os.path.exists('%s/%s/temp' % (clim_f_name, Rad_f_name)):
        os.makedirs('%s/%s/temp' % (clim_f_name, Rad_f_name))

    if clim_ext == '.epw':
        #epw2wea reads location, direct normal and diffuse horizontal irradiance data from epw and saves them in wea
        wea = 'epw2wea %s %s/%s/temp/%s.wea' % (clim_fn, clim_f_name, Rad_f_name, clim_f_name)
        os.system(wea)
    if clim_ext == '.wea':
        os.rename(clim_fn, '%s/%s/temp/%s.wea' % (clim_f_name, Rad_f_name, clim_f_name))

    smx = 'gendaymtx -of -m %d -r %d %s/%s/temp/%s.wea | rmtxop -c .27 .66 .07 - > %s/%s/temp/%s-t%d-MF%d.smx' % (
                mf, north, clim_f_name, Rad_f_name, clim_f_name, clim_f_name, Rad_f_name, clim_f_name, ts, mf)
    smx_fp = '%s/%s/temp/%s-t%d-MF%d.smx' % (clim_f_name, Rad_f_name, clim_f_name, ts, mf)

    os.system(smx)

    return smx_fp



def run_2ph(oct, Rad_file, clim_fn, r, opt_fn, pts_fn, smx_fp, mf, ts=60):
    Clim_f_name = os.path.basename(clim_fn)
    Clim_f_name = os.path.splitext(Clim_f_name)[0]
    Rad_f_name = os.path.basename(Rad_file)
    Rad_f_name = os.path.splitext(Rad_f_name)[0]
    print('Case-%s Weatherfile-%s Orientation-%d run started' % (Rad_f_name, Clim_f_name, r))
    prj = os.path.splitext(oct)[0]
    #print(prj)

    nhyear = (60 / ts) * 24 * 365
    assert (ts % 60 == 0) & (ts / 60 >= 1), 'The timestep should be 60 minutes or a submultiple of 60'

    with open(opt_fn, 'r') as f:
        opt = f.read()
    #    print(opt)

    if not os.path.exists('%s/%s/dc' % (Clim_f_name, Rad_f_name)):
        os.makedirs('%s/%s/dc' % (Clim_f_name, Rad_f_name))
    if not os.path.exists('%s/%s/res' % (Clim_f_name, Rad_f_name)):
        os.makedirs('%s/%s/res' % (Clim_f_name, Rad_f_name))
    if not os.path.exists('%s/%s/temp' % (Clim_f_name, Rad_f_name)):
        os.makedirs('%s/%s/temp' % (Clim_f_name, Rad_f_name))

    groundglow = '#@rfluxmtx h=u u=Y\nvoid glow ground_glow 0 0 4 1 1 1 0\nground_glow source ground 0 0 4 0 0 -1 180\n'
    skyglow = '#@rfluxmtx h=r%d u=Y\nvoid glow sky_glow 0 0 4 1 1 1 0\nsky_glow source sky 0 0 4 0 0 1 180\n' % mf
    with open('%s/%s/temp/whitesky.rad' % (Clim_f_name, Rad_f_name), 'w') as f:
        f.write(groundglow)
        f.write(skyglow)

    for wp_fp in pts_fn:
        line_n_cmd = 'wc -l < %s' % wp_fp
        proc = subprocess.Popen(line_n_cmd, shell=True, stdout=subprocess.PIPE)
        sen_n = int(proc.communicate()[0])
        print('Number of sensor points: %d' % sen_n)

        wp = os.path.basename(wp_fp)
        wp = os.path.splitext(wp)[0]


        bounces = ''
        dc_fn = '%s/%s/dc/%s_MF%d.dc' % (Clim_f_name, Rad_f_name, Rad_f_name, mf)
        #edit to specify ill name
        res_fn = '%s/%s/res/%s_%s_R_%03d' % (Clim_f_name, Rad_f_name, Rad_f_name, Clim_f_name, r)

        #if not os.path.exists(dc_fn):
        rfluxmtx = 'rfluxmtx -faf -n %d @%s %s -I+ -y %d < %s - %s/%s/temp/whitesky.rad -i %s.oct | rmtxop -c .27 .66 .07 - > %s' % (
                    nproc, opt_fn, bounces, sen_n, wp_fp, Clim_f_name, Rad_f_name, prj, dc_fn)

        os.system(rfluxmtx)

        #else:
        #        print('Existing DC matrix used for the simulation')

        rmtxop = 'rmtxop %s %s | rmtxop -fa -s 179 - > %s.ill' % (dc_fn, smx_fp, res_fn)
        os.system(rmtxop)

    for f in os.listdir('%s/%s/dc' % (Clim_f_name, Rad_f_name)):
        if os.path.getsize('%s/%s/dc/%s' % (Clim_f_name, Rad_f_name, f)) is 0:
            print('%s/%s/dc/%s is empty and will be removed' % (Clim_f_name, Rad_f_name, f))
            os.remove('%s/%s/dc/%s' % (Clim_f_name, Rad_f_name, f))

        for f in os.listdir('%s/%s/res' % (Clim_f_name, Rad_f_name)):
            if os.path.getsize('%s/%s/res/%s' % (Clim_f_name, Rad_f_name, f)) is 0:
                print('%s/%s/res/%s is empty and will be removed' % (Clim_f_name, Rad_f_name, f))
                os.remove('%s/%s/res/%s' % (Clim_f_name, Rad_f_name, f))
    print('Simulation finished\n Case-%s, Weatherfile-%s, Orientation-%d, Time taken - %s seconds' % (Rad_f_name, Clim_f_name, r,(time.time() - start_time)))
