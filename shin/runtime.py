"""Bounded stack VM. Resource accounting is logical, not OS memory isolation."""
from dataclasses import dataclass
import json
import math
import time
from .compiler import ShinError, DEFAULT_LIMITS


@dataclass(frozen=True)
class Untrusted:
    value: str


def size(value, ceiling, depth=0):
    if depth > 32:
        raise ShinError('value nesting exceeds 32')
    if isinstance(value, Untrusted):
        return size(value.value, ceiling, depth + 1)
    if value is None or type(value) is bool:
        return 8
    if type(value) in (int, float):
        if type(value) is int and not -(1 << 63) <= value < (1 << 63):
            raise ShinError('integer exceeds signed 64-bit range')
        if type(value) is float and not math.isfinite(value):
            raise ShinError('non-finite number')
        return 8
    if type(value) is str:
        try:
            n = len(value.encode('utf-8'))
        except UnicodeError:
            raise ShinError('invalid Unicode text') from None
    elif type(value) in (list, dict):
        n = 8
        values = value if type(value) is list else [x for pair in value.items() for x in pair]
        for item in values:
            n += size(item, ceiling, depth + 1) + 8
            if n > ceiling:
                break
    else:
        raise ShinError('unsupported host value')
    if n > ceiling:
        raise ShinError('value_bytes budget exceeded')
    return n


def trusted(value):
    if isinstance(value, Untrusted):
        raise ShinError('untrusted model output: use check_text or check_json first')
    if isinstance(value, (list, dict)):
        for item in (value.values() if isinstance(value, dict) else value):
            trusted(item)
    return value


def boolean(value):
    trusted(value)
    if type(value) is not bool:
        raise ShinError('condition must be a boolean')
    return value


def number(value):
    trusted(value)
    if type(value) not in (int, float):
        raise ShinError('expected number')
    return value


def text(value):
    trusted(value)
    if type(value) is not str:
        raise ShinError('expected text')
    return value


def encode(value):
    trusted(value)
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


class VM:
    def __init__(self, program, allow_models=(), models=None, input_value=None,
                 output=None, limits=None):
        self.program = program
        self.allowed = set(allow_models)
        self.models = dict(models or {})
        self.limits = dict(DEFAULT_LIMITS)
        for requested in (program.limits, limits or {}):
            for key, value in requested.items():
                if key not in self.limits or type(value) is not int or value < 1:
                    raise ShinError('invalid host limit')
                self.limits[key] = min(self.limits[key], value)
        self.steps = self.allocated = self.output_bytes = 0
        self.lines = []
        self.output = output
        self.globals = {}
        self.input_value = input_value
        size(input_value, self.limits['value_bytes'])
        self.start = time.monotonic()

    def tick(self):
        self.steps += 1
        if self.steps > self.limits['steps']:
            raise ShinError('steps budget exceeded')
        self.check_time()

    def check_time(self):
        if time.monotonic() - self.start > self.limits['wall_ms'] / 1000:
            raise ShinError('wall_ms budget exceeded')

    def account(self, value):
        self.allocated += size(value, self.limits['value_bytes'])
        if self.allocated > self.limits['allocation_bytes']:
            raise ShinError('allocation_bytes budget exceeded')
        return value

    def run(self):
        denied = self.program.effects - self.allowed
        if denied:
            raise ShinError('host denied model capability: ' + ', '.join(sorted(denied)))
        missing = self.program.effects - self.models.keys()
        if missing:
            raise ShinError('model not configured: ' + ', '.join(sorted(missing)))
        self.execute(self.program.main, [self.globals], 0)
        return self.lines

    def execute(self, code, scopes, depth):
        if depth > self.limits['depth']:
            raise ShinError('depth budget exceeded')
        stack, pc = [], 0
        while pc < len(code):
            op, arg, line = code[pc]
            pc += 1
            try:
                self.tick()
                if op == 'CONST':
                    stack.append(self.account(arg))
                elif op == 'LOAD':
                    scope = next((s for s in reversed(scopes) if arg in s), None)
                    if scope is None and arg in self.globals:
                        scope = self.globals
                    if scope is None:
                        raise ShinError(f'undefined variable {arg!r}')
                    stack.append(scope[arg])
                elif op == 'LET':
                    if arg in scopes[-1]:
                        raise ShinError(f'duplicate variable {arg!r}')
                    scopes[-1][arg] = stack.pop()
                elif op == 'SET':
                    scope = next((s for s in reversed(scopes) if arg in s), None)
                    if scope is None:
                        raise ShinError(f'cannot assign undefined or outer function variable {arg!r}')
                    scope[arg] = stack.pop()
                elif op == 'ENTER':
                    scopes.append({})
                elif op == 'LEAVE':
                    scopes.pop()
                elif op == 'POP':
                    stack.pop()
                elif op == 'RETURN':
                    return stack.pop()
                elif op == 'JUMP':
                    pc = arg
                elif op == 'JUMP_FALSE':
                    if not boolean(stack.pop()):
                        pc = arg
                elif op == 'BOOL':
                    stack.append(boolean(stack.pop()))
                elif op == 'SHORT':
                    value = boolean(stack[-1])
                    if (arg[0] == '&&' and not value) or (arg[0] == '||' and value):
                        pc = arg[1]
                    else:
                        stack.pop()
                elif op == 'ARRAY':
                    values = stack[-arg:] if arg else []
                    if arg:
                        del stack[-arg:]
                    stack.append(self.account(values))
                elif op == 'RECORD':
                    values = stack[-arg * 2:] if arg else []
                    if arg:
                        del stack[-arg * 2:]
                    stack.append(self.account(dict(zip(values[::2], values[1::2]))))
                elif op == 'INDEX':
                    index, container = stack.pop(), stack.pop()
                    trusted(index)
                    if isinstance(container, Untrusted):
                        trusted(container)
                    if type(container) is dict:
                        text(index)
                        if index not in container:
                            raise ShinError(f'missing record key {index!r}')
                    elif type(container) in (list, str):
                        if type(index) is not int or not 0 <= index < len(container):
                            raise ShinError('index out of bounds or not an integer')
                    else:
                        raise ShinError('indexing requires array, record, or text')
                    stack.append(container[index])
                elif op == 'UNARY':
                    value = stack.pop()
                    stack.append(self.account(not boolean(value) if arg == '!' else -number(value)))
                elif op == 'BINARY':
                    right, left = stack.pop(), stack.pop()
                    stack.append(self.account(self.binary(arg, left, right)))
                elif op == 'CALL':
                    name, count = arg
                    args = stack[-count:] if count else []
                    if count:
                        del stack[-count:]
                    if name in self.program.functions:
                        fn = self.program.functions[name]
                        result = self.execute(fn.code, [dict(zip(fn.params, args))], depth + 1)
                    else:
                        result = self.builtin(name, args)
                    stack.append(self.account(result))
                else:
                    raise ShinError('invalid instruction')
            except ShinError as exc:
                if str(exc).startswith('line '):
                    raise
                raise ShinError(f'line {line}: {exc}') from None
            except (ArithmeticError, TypeError, ValueError, KeyError, IndexError, RecursionError):
                raise ShinError(f'line {line}: invalid operation or resource limit') from None
        return None

    def binary(self, op, a, b):
        trusted(a)
        trusted(b)
        if op in ('==', '!='):
            same = equal(a, b)
            return same if op == '==' else not same
        if op == '+' and type(a) is type(b) and type(a) in (str, list):
            if size(a, self.limits['value_bytes']) + size(b, self.limits['value_bytes']) > self.limits['value_bytes']:
                raise ShinError('value_bytes budget exceeded')
            return a + b
        number(a)
        number(b)
        if op == '+': return a + b
        if op == '-': return a - b
        if op == '*': return a * b
        if op == '/': return a / b
        if op == '%': return a % b
        if op == '<': return a < b
        if op == '>': return a > b
        if op == '<=': return a <= b
        if op == '>=': return a >= b
        raise ShinError('unsupported operator')

    def builtin(self, name, args):
        arity = {'print': 1, 'len': 1, 'str': 1, 'push': 2, 'keys': 1,
                 'assert': 1, 'infer': 2, 'check_text': 2, 'check_json': 2,
                 'json': 1, 'input': 0}
        if len(args) != arity[name]:
            raise ShinError(f'{name} expects {arity[name]} arguments')
        if name == 'input':
            # Host input, like model output, is untrusted and must be validated.
            return Untrusted(encode(self.input_value))
        if name == 'infer':
            model, prompt = text(args[0]), text(args[1])
            if model not in self.program.permits or model not in self.allowed:
                raise ShinError('model capability denied')
            remaining = self.limits['wall_ms'] / 1000 - (time.monotonic() - self.start)
            if remaining <= 0:
                raise ShinError('wall_ms budget exceeded')
            result = self.models[model](prompt, remaining, self.limits['value_bytes'])
            self.check_time()
            if type(result) is not str:
                raise ShinError('model must return text')
            return Untrusted(result)
        if name == 'check_text':
            value, maximum = args
            if not isinstance(value, Untrusted):
                raise ShinError('check_text expects untrusted text')
            if type(maximum) is not int or not 0 < maximum <= self.limits['value_bytes']:
                raise ShinError('invalid text length limit')
            if not 0 < len(value.value) <= maximum:
                raise ShinError('text validation failed: empty or too long')
            return value.value
        if name == 'check_json':
            value, schema = args
            if not isinstance(value, Untrusted) or type(schema) is not dict:
                raise ShinError('check_json expects untrusted text and a record schema')
            trusted(schema)
            try:
                result = json.loads(value.value, parse_constant=reject_constant,
                                    object_pairs_hook=unique_object)
            except (ValueError, RecursionError):
                raise ShinError('invalid JSON model output') from None
            if type(result) is not dict or set(result) != set(schema):
                raise ShinError('JSON keys do not match schema')
            types = {'text': str, 'number': (int, float), 'boolean': bool,
                     'array': list, 'record': dict}
            for key, kind in schema.items():
                if type(kind) is not str or kind not in types:
                    raise ShinError('unsupported schema type')
                expected = types[kind]
                valid = type(result[key]) in expected if type(expected) is tuple else type(result[key]) is expected
                if not valid:
                    raise ShinError(f'JSON field {key!r} must be {kind}')
            size(result, self.limits['value_bytes'])
            return result
        for value in args:
            trusted(value)
        if name == 'print':
            rendered = args[0] if type(args[0]) is str else encode(args[0])
            n = len(rendered.encode('utf-8')) + 1
            if self.output_bytes + n > self.limits['output_bytes']:
                raise ShinError('output_bytes budget exceeded')
            self.output_bytes += n
            self.lines.append(rendered)
            if self.output:
                self.output(rendered)
            return None
        if name == 'len':
            if type(args[0]) not in (list, dict, str):
                raise ShinError('len expects array, record, or text')
            return len(args[0])
        if name == 'str':
            return args[0] if type(args[0]) is str else encode(args[0])
        if name == 'json':
            return encode(args[0])
        if name == 'keys':
            if type(args[0]) is not dict:
                raise ShinError('keys expects record')
            return list(args[0])
        if name == 'push':
            if type(args[0]) is not list:
                raise ShinError('push expects array')
            size(args, self.limits['value_bytes'])
            return args[0] + [args[1]]
        if name == 'assert':
            if not boolean(args[0]):
                raise ShinError('assertion failed')
            return None
        raise ShinError('unknown builtin')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-standard JSON number')


def equal(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is list:
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    if type(a) is dict:
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    return a == b
