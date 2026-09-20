"""SHIN lexer and compiler. No Python eval, exec, imports, or bytecode loading."""
from dataclasses import dataclass, field
import json
import re


class ShinError(Exception):
    """A diagnostic safe to present without a Python traceback."""


@dataclass
class Token:
    text: str
    line: int
    kind: str = ''


@dataclass
class Function:
    params: list
    code: list


@dataclass
class Program:
    main: list
    functions: dict
    permits: set
    effects: set
    limits: dict


DEFAULT_LIMITS = {'steps': 100000, 'depth': 64, 'value_bytes': 65536,
                  'output_bytes': 65536, 'wall_ms': 5000, 'allocation_bytes': 8388608}
BUILTINS = {'print', 'len', 'str', 'push', 'keys', 'assert', 'infer',
            'check_text', 'check_json', 'json', 'input'}
RESERVED = BUILTINS | {'fn', 'let', 'if', 'else', 'while', 'return', 'permit',
                       'model', 'budget', 'true', 'false', 'null'}
TOKEN = re.compile(r'(?P<space>\s+)|(?P<comment>//[^\n]*)|'
                   r'(?P<string>"(?:[^"\\\n]|\\.)*")|'
                   r'(?P<number>\d+(?:\.\d+)?)|(?P<name>[A-Za-z_][A-Za-z_0-9]*)|'
                   r'(?P<symbol>==|!=|<=|>=|&&|\|\||[{}\[\](),;:+*/%!=<>-])')


def lex(source):
    if len(source.encode('utf-8')) > 65536:
        raise ShinError('source exceeds 65536 bytes')
    tokens, pos, line = [], 0, 1
    while pos < len(source):
        m = TOKEN.match(source, pos)
        if not m:
            raise ShinError(f'line {line}: unexpected character {source[pos]!r}')
        value = m.group()
        if m.lastgroup not in ('space', 'comment'):
            tokens.append(Token(value, line, m.lastgroup))
        line += value.count('\n')
        pos = m.end()
    tokens.append(Token('<eof>', line))
    return tokens


class Compiler:
    PRECEDENCE = {'||': 1, '&&': 2, '==': 3, '!=': 3, '<': 4, '>': 4,
                  '<=': 4, '>=': 4, '+': 5, '-': 5, '*': 6, '/': 6, '%': 6}

    def __init__(self, source):
        self.tokens = lex(source)
        self.i = 0
        self.functions = {}
        self.permits, self.effects = set(), set()
        self.limits = {}
        self.calls = []
        self.code = []
        self.in_function = False

    @property
    def token(self):
        return self.tokens[self.i]

    def error(self, message):
        raise ShinError(f'line {self.token.line}: {message}')

    def take(self, text=None):
        token = self.token
        if token.text == '<eof>':
            self.error('unexpected end of source')
        if text is not None and token.text != text:
            self.error(f'expected {text!r}, got {token.text!r}')
        self.i += 1
        return token

    def accept(self, text):
        if self.token.text == text:
            self.take()
            return True
        return False

    def name(self):
        if self.token.kind != 'name' or self.token.text in RESERVED:
            self.error('expected a non-reserved identifier')
        return self.take().text

    def emit(self, op, arg=None, line=None):
        self.code.append([op, arg, self.token.line if line is None else line])
        return len(self.code) - 1

    def patch(self, index):
        self.code[index][1] = len(self.code)

    def compile(self):
        while self.token.text != '<eof>':
            if self.accept('permit'):
                self.take('model')
                if self.token.kind != 'string':
                    self.error('model permit requires a string literal')
                name = self.string()
                if name in self.permits:
                    self.error(f'duplicate permit {name!r}')
                self.permits.add(name)
                self.take(';')
            elif self.accept('budget'):
                name = self.take().text
                if name not in DEFAULT_LIMITS or name in self.limits:
                    self.error('unknown or duplicate budget')
                self.take('=')
                token = self.take()
                if token.kind != 'number' or '.' in token.text:
                    self.error('budget must be a positive integer')
                value = int(token.text)
                if value < 1 or value > DEFAULT_LIMITS[name]:
                    self.error(f'{name} must be 1..{DEFAULT_LIMITS[name]}')
                self.limits[name] = value
                self.take(';')
            elif self.accept('fn'):
                self.function()
            else:
                self.statement()
        for name, argc, line in self.calls:
            if name not in BUILTINS and name not in self.functions:
                raise ShinError(f'line {line}: unknown function {name!r}')
            if name in self.functions and argc != len(self.functions[name].params):
                raise ShinError(f'line {line}: wrong argument count for {name!r}')
        missing = self.effects - self.permits
        if missing:
            raise ShinError('missing permit model: ' + ', '.join(sorted(missing)))
        return Program(self.code, self.functions, self.permits, self.effects, self.limits)

    def function(self):
        name = self.name()
        if name in self.functions:
            self.error('duplicate function')
        self.take('(')
        params = []
        if self.token.text != ')':
            while True:
                param = self.name()
                if param in params:
                    self.error('duplicate parameter')
                params.append(param)
                if not self.accept(','):
                    break
        self.take(')')
        outer = self.code
        self.code = []
        self.in_function = True
        self.block()
        self.emit('CONST', None)
        self.emit('RETURN')
        self.functions[name] = Function(params, self.code)
        self.code = outer
        self.in_function = False

    def block(self):
        self.take('{')
        self.emit('ENTER')
        while self.token.text not in ('}', '<eof>'):
            self.statement()
        self.take('}')
        self.emit('LEAVE')

    def statement(self):
        line = self.token.line
        if self.accept('let'):
            name = self.name()
            self.take('=')
            self.expression()
            self.take(';')
            self.emit('LET', name, line)
        elif self.accept('if'):
            self.expression()
            jump = self.emit('JUMP_FALSE', line=line)
            self.block()
            if self.accept('else'):
                end = self.emit('JUMP')
                self.patch(jump)
                self.block()
                self.patch(end)
            else:
                self.patch(jump)
        elif self.accept('while'):
            start = len(self.code)
            self.expression()
            jump = self.emit('JUMP_FALSE', line=line)
            self.block()
            self.emit('JUMP', start)
            self.patch(jump)
        elif self.accept('return'):
            if not self.in_function:
                self.error('return is only valid inside a function')
            if self.token.text == ';':
                self.emit('CONST', None)
            else:
                self.expression()
            self.take(';')
            self.emit('RETURN', line=line)
        elif self.token.kind == 'name' and self.tokens[self.i + 1].text == '=':
            name = self.name()
            self.take('=')
            self.expression()
            self.take(';')
            self.emit('SET', name, line)
        else:
            self.expression()
            self.take(';')
            self.emit('POP')

    def string(self):
        token = self.take()
        try:
            value = json.loads(token.text)
            value.encode('utf-8')
            return value
        except (ValueError, UnicodeError):
            raise ShinError(f'line {token.line}: invalid string escape') from None

    def expression(self, minimum=0):
        line = self.token.line
        if self.token.text in ('!', '-'):
            op = self.take().text
            if op == '-' and self.token.kind == 'number':
                literal = self.take().text
                self.emit('CONST', -float(literal) if '.' in literal else -int(literal), line)
            else:
                self.expression(7)
                self.emit('UNARY', op, line)
        else:
            self.atom()
        while self.accept('['):
            self.expression()
            self.take(']')
            self.emit('INDEX', line=line)
        while self.token.text in self.PRECEDENCE:
            op = self.token.text
            prec = self.PRECEDENCE[op]
            if prec < minimum:
                break
            self.take()
            if op in ('&&', '||'):
                self.emit('BOOL', line=line)
                jump = self.emit('SHORT', [op, None], line)
                self.expression(prec + 1)
                self.emit('BOOL', line=line)
                self.code[jump][1][1] = len(self.code)
            else:
                self.expression(prec + 1)
                self.emit('BINARY', op, line)

    def atom(self):
        token = self.token
        if token.kind == 'number':
            self.take()
            self.emit('CONST', float(token.text) if '.' in token.text else int(token.text), token.line)
        elif token.kind == 'string':
            self.emit('CONST', self.string(), token.line)
        elif token.text in ('true', 'false', 'null'):
            self.take()
            self.emit('CONST', {'true': True, 'false': False, 'null': None}[token.text], token.line)
        elif self.accept('('):
            self.expression()
            self.take(')')
        elif self.accept('['):
            n = self.items(']')
            self.emit('ARRAY', n, token.line)
        elif self.accept('{'):
            n, keys = 0, set()
            if self.token.text != '}':
                while True:
                    if self.token.kind != 'string':
                        self.error('record keys must be string literals')
                    key = self.string()
                    if key in keys:
                        self.error('duplicate record key')
                    keys.add(key)
                    self.emit('CONST', key)
                    self.take(':')
                    self.expression()
                    n += 1
                    if not self.accept(','):
                        break
            self.take('}')
            self.emit('RECORD', n, token.line)
        elif token.kind == 'name':
            name = self.take().text
            if self.accept('('):
                if name == 'infer':
                    if self.token.kind != 'string':
                        self.error('infer model name must be a literal for effect analysis')
                    model = json.loads(self.token.text)
                    self.effects.add(model)
                n = self.items(')')
                self.calls.append((name, n, token.line))
                self.emit('CALL', [name, n], token.line)
            else:
                if name in RESERVED:
                    self.error('unexpected reserved word')
                self.emit('LOAD', name, token.line)
        else:
            self.error('expected expression')

    def items(self, end):
        count = 0
        if self.token.text != end:
            while True:
                self.expression()
                count += 1
                if not self.accept(','):
                    break
        self.take(end)
        return count


def compile_source(source):
    try:
        return Compiler(source).compile()
    except (RecursionError, ValueError, OverflowError):
        raise ShinError('source nesting or numeric literal exceeds compiler limits') from None
