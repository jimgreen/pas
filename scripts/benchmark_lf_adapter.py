"""Compare LF adapter versions on identical solved values (no solver change)."""
import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pas.kernels import _extract_lf_devices, normalize_lf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',default='aee1b5f')
    parser.add_argument('--devices',type=int,default=2500)
    args=parser.parse_args()
    source=subprocess.check_output(['git','show',f'{args.baseline}:pas/kernels.py'],encoding='utf-8')
    baseline={'__name__':'baseline_adapter'}
    exec(compile(source,'baseline_adapter','exec'),baseline)
    n=args.devices
    network=NS(ac=NS(branches=[NS(name=f'L{i}',idx=i,i_node=i,j_node=i+1) for i in range(n)]))
    result=NS(ac=NS(branches={f'L{i}':NS(i_p=float(i),j_p=-float(i),i_v=1.,j_v=.99) for i in range(n)}),network=network,arrays={'voltage':[1.]*n,'power':[float(i) for i in range(n)]})
    calc=NS(lf_result=result)
    old=baseline['_extract_lf_devices']
    assert old(calc,result)==_extract_lf_devices(calc,result)
    times={'baseline':[],'indexed':[]}
    for i in range(6):
        for name,fn in ([('baseline',old),('indexed',_extract_lf_devices)] if i%2==0 else [('indexed',_extract_lf_devices),('baseline',old)]):
            start=time.perf_counter();fn(calc,result);times[name].append(time.perf_counter()-start)
    before=len(json.dumps(baseline['normalize_lf'](calc)['summary']).encode())
    after=len(json.dumps(normalize_lf(calc)['summary']).encode())
    report={'baseline':args.baseline,'devices':n,'numeric_rows_identical':True,'seconds':times,'median_speedup':statistics.median(times['baseline'])/statistics.median(times['indexed']),'summary_bytes_before':before,'summary_bytes_after':after,'scope':'Synthetic full-mode result mapping only, not solver timing.'}
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
