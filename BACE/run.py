#!/usr/bin/env python3
"""BACE preparation, pilot, acceptance, and explicit main experiment entry point."""
from pathlib import Path
import argparse
import os
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['RAGAS_DO_NOT_TRACK'] = 'true'
os.environ['HF_HUB_OFFLINE'] = '1'

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'script'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['sample','prepare-evidence','prepare-inputs','freeze','pilot','check','main','summarize'])
    parser.add_argument('--scope',choices=['pilot','main'],default='pilot',help='Only used by summarize')
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.command=='sample':
        from select_sample import select
        select()
    elif args.command=='prepare-evidence':
        from prepare_evidence import prepare
        prepare()
    elif args.command=='prepare-inputs':
        from prepare_inputs import prepare
        prepare()
    elif args.command in ('freeze','check'):
        from acceptance import freeze,check
        (freeze if args.command=='freeze' else check)()
    elif args.command in ('pilot','main'):
        from pipeline import run_experiment
        run_experiment(args.command)
    else:
        from summarize import summarize
        summarize(ROOT/'results'/f'{args.scope}_v1')


if __name__ == "__main__":
    main()
