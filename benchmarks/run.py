"""Transparent microbenchmark; not a claim of superiority to other languages."""
import json
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shin import compile_source, VM

SOURCE='let i=0; let total=0; while i<1000 {total=total+i; i=i+1;} assert(total==499500);'
program=compile_source(SOURCE)


def measure(fn, n=7):
    times=[]
    for _ in range(n):
        start=time.perf_counter()
        fn()
        times.append((time.perf_counter()-start)*1000)
    return round(statistics.median(times),4)


def python_loop():
    i=total=0
    while i<1000:
        total+=i
        i+=1
    assert total==499500


vm=VM(program)
vm.run()
root=Path(__file__).resolve().parents[1]
print(json.dumps({
    'python':platform.python_version(), 'platform':platform.system(),
    'machine':platform.machine(),'rounds':7,'statistic':'median milliseconds',
    'compile_ms':measure(lambda:compile_source(SOURCE)),
    'vm_execute_ms':measure(lambda:VM(program).run()),
    'python_loop_ms':measure(python_loop),
    'vm_steps':vm.steps,'logical_allocation_bytes':vm.allocated,
    'runtime_source_bytes':sum(p.stat().st_size for p in (root/'shin').glob('*.py')),
    'note':'Single sum loop, no AI or startup; CPython reference VM, not native code. Logical allocation is not RSS.'
},indent=2))
