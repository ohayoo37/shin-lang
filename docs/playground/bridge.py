"""Fixed host adapter for the browser playground; never evaluates user Python."""
import json
from shin import ShinError, VM, compile_source


def run_playground(source, allow_demo=False):
    lines = []
    vm = None
    try:
        if type(source) is not str or len(source.encode('utf-8')) > 65536:
            raise ShinError('source exceeds 65536 bytes or is not text')
        program = compile_source(source)
        vm = VM(program, allow_models=['demo'] if allow_demo is True else [],
                models={'demo': lambda prompt, timeout, max_bytes: prompt},
                output=lines.append,
                limits={'steps': 50000, 'wall_ms': 1000, 'output_bytes': 8192,
                        'value_bytes': 32768, 'allocation_bytes': 1048576})
        vm.run()
        return {'ok': True, 'output': '\n'.join(lines), 'steps': vm.steps}
    except (ShinError, RecursionError) as error:
        return {'ok': False, 'output': '\n'.join(lines), 'error': str(error),
                'steps': vm.steps if vm else 0}
