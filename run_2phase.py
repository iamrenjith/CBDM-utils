#!/usr/bin/env python3
import os
import glob
import subprocess
import argparse
from pathlib import Path
from Commands import read_radfiles,read_matfiles,read_climfiles, getArgs, makesmx, run_2ph

Rad_filenames=read_radfiles()
Mat_filenames=read_matfiles()
Clim_filenames=read_climfiles()

nproc_cmd = 'sysctl -n hw.ncpu'
proc = subprocess.Popen(nproc_cmd, shell=True, stdout=subprocess.PIPE)
nproc = int(proc.communicate()[0])


for a in range(0,len(Clim_filenames)):
    clim=Clim_filenames[a]
    print(clim)
    opt='Radiance_parameters/Par.opt'
    #orientations
    for b in range(0,8):
        r=b*45
        for c in range(0,len(Rad_filenames)):
                Rad_file=Rad_filenames[c]
                Mat_file=Mat_filenames[c]
                os.system("oconv %s %s > file.oct" % (Mat_file,Rad_file))
                oct= 'file.oct'
                args = getArgs()
                smx_fp = makesmx(clim, Rad_file, args.mf, args.ts)
                run_2ph(oct, Rad_file, clim, r, opt, args.pts, smx_fp, args.mf, args.ts)
