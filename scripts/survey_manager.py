#!/usr/bin/env python3
"""Print NĀSADĪYA's real-survey acquisition plan and exact safe commands."""
from __future__ import annotations
from pathlib import Path
import sys
PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT/'pipeline'))
from nasadiya_lightcone.photoz import PHOTOZ_PROFILES
from nasadiya_lightcone.desi import DESI_COMPONENTS

def main():
    print('NĀSADĪYA multi-survey local build plan')
    print('1. 2MRS: already installed as the 43,533-row spectroscopic anchor.')
    print('2. 2MPZ: .\\.venv\\Scripts\\python.exe scripts\\download_2mpz.py')
    print('          .\\.venv\\Scripts\\python.exe scripts\\build_2mpz_tile_store.py')
    print('3. WISE × SuperCOSMOS: .\\.venv\\Scripts\\python.exe scripts\\download_wise_sc.py')
    print('          .\\.venv\\Scripts\\python.exe scripts\\build_wise_sc_tile_store.py')
    print('4. DESI DR1 LSS: .\\.venv\\Scripts\\python.exe scripts\\download_desi_dr1_lss.py --dry-run')
    print('          .\\.venv\\Scripts\\python.exe scripts\\download_desi_dr1_lss.py --yes')
    print('          .\\.venv\\Scripts\\python.exe scripts\\build_desi_dr1_tile_store.py')
    print('5. Gaia DR3 local stars (separate galactic mode): .\\.venv\\Scripts\\python.exe scripts\\download_gaia_dr3_local.py --yes')
    print('          .\\.venv\\Scripts\\python.exe scripts\\build_gaia_dr3_local_sample.py')
    print('\nNo raw catalogue or multi-million-row tile store belongs in Git history.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
