import contextlib
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from shin import ShinError, VM, compile_source
from shin.models import mock_model

ROOT = Path(__file__).resolve().parents[1]


def run(source, **kwargs):
    return VM(compile_source(source), **kwargs).run()


class LanguageTests(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(run('print(2 + 3 * 4); print((2 + 3) * 4); print(-5 + 2);'), ['14', '20', '-3'])

    def test_scopes_and_assignment(self):
        self.assertEqual(run('let x = 1; if true { let x = 2; print(x); } print(x); x = 3; print(x);'), ['2', '1', '3'])

    def test_branch(self):
        self.assertEqual(run('if false { print(0); } else { print(1); }'), ['1'])

    def test_loop(self):
        self.assertEqual(run('let i=0; let total=0; while i<10 { let n=i; total=total+n; i=i+1; } print(total);'), ['45'])

    def test_recursion(self):
        self.assertEqual(run('fn fact(n) { if n <= 1 { return 1; } return n * fact(n-1); } print(fact(6));'), ['720'])

    def test_forward_function(self):
        self.assertEqual(run('print(double(9)); fn double(n) { return n*2; }'), ['18'])

    def test_globals_read_only_in_function(self):
        self.assertEqual(run('let x=4; fn read(){return x;} print(read());'), ['4'])
        with self.assertRaisesRegex(ShinError, 'cannot assign'):
            run('let x=4; fn change(){x=5;} change();')

    def test_collections(self):
        self.assertEqual(run('let a=[1,2]; let b=push(a,3); print(len(a)); print(b[2]); print({"x":a}["x"][0]);'), ['2','3','1'])

    def test_short_circuit(self):
        self.assertEqual(run('print(false && (1/0 == 1)); print(true || (1/0 == 1));'), ['false','true'])

    def test_strict_boolean(self):
        with self.assertRaisesRegex(ShinError, 'boolean'):
            run('if 1 { print(1); }')

    def test_unicode(self):
        self.assertEqual(run('print("芯 🌱"); print(len("日本語"));'), ['芯 🌱','3'])

    def test_empty_values(self):
        self.assertEqual(run('print([]); print({}); print(null); fn f() {return;} print(f());'), ['[]','{}','null','null'])

    def test_syntax_errors(self):
        for source in ['budget', 'budget steps =', 'let = 1;', 'print(1)', 'fn x(){', 'return 1;', 'let x=;', 'print(@);', 'print("bad\\q");']:
            with self.subTest(source=source), self.assertRaises(ShinError):
                compile_source(source)

    def test_bad_names(self):
        for source in ['let print=1;', 'fn x(a,a){}', 'fn x(){} fn x(){}', 'unknown();', 'fn f(a){} f();']:
            with self.subTest(source=source), self.assertRaises(ShinError):
                compile_source(source)

    def test_runtime_errors(self):
        for source in ['print(x);', 'let a=1; let a=2;', 'x=3;', 'print([1][-1]);', 'print({}["x"]);', 'print(1/0);', 'print(true+1);', 'print(len(1));']:
            with self.subTest(source=source), self.assertRaises(ShinError):
                run(source)

    def test_steps(self):
        with self.assertRaisesRegex(ShinError, 'steps budget'):
            run('budget steps=20; while true {}')

    def test_depth(self):
        with self.assertRaisesRegex(ShinError, 'depth budget'):
            run('budget depth=4; fn f(){return f();} f();')

    def test_value_limit(self):
        with self.assertRaisesRegex(ShinError, 'value_bytes'):
            run('budget value_bytes=32; let x="12345678"; while true {x=x+x;}')

    def test_allocation_limit(self):
        with self.assertRaisesRegex(ShinError, 'allocation_bytes'):
            run('budget allocation_bytes=50; let x=0; while x<100 {x=x+1;}')

    def test_output_limit(self):
        with self.assertRaisesRegex(ShinError, 'output_bytes'):
            run('budget output_bytes=3; print("abcd");')

    def test_integer_lower_bound(self):
        self.assertEqual(run('print(-9223372036854775808);'), ['-9223372036854775808'])

    def test_nested_type_equality(self):
        self.assertEqual(run('print([1] == [true]); print({"x":1} == {"x":1.0});'), ['false','false'])

    def test_integer_overflow(self):
        with self.assertRaisesRegex(ShinError, '64-bit'):
            run('print(9223372036854775807 + 1);')

    def test_limits_cannot_escalate(self):
        with self.assertRaises(ShinError):
            compile_source('budget depth=99999;')
        with self.assertRaisesRegex(ShinError, 'steps budget'):
            run('budget steps=100; while true {}', limits={'steps': 5})

    def test_source_limit(self):
        with self.assertRaisesRegex(ShinError, 'source exceeds'):
            compile_source(' ' * 65537)

    def test_nested_source_limit(self):
        with self.assertRaises(ShinError):
            compile_source('print(' + '(' * 3000 + '1' + ')' * 3000 + ');')

    def test_no_host_escape(self):
        for source in ['open("/etc/passwd");','eval("1");','exec("x");','__import__("os");','print.__class__;']:
            with self.subTest(source=source), self.assertRaises(ShinError):
                compile_source(source)

    def test_permit_required(self):
        with self.assertRaisesRegex(ShinError, 'missing permit'):
            compile_source('infer("demo","hello");')

    def test_host_grant_required_before_any_output(self):
        emitted=[]
        with self.assertRaisesRegex(ShinError, 'host denied'):
            run('permit model "demo"; print("should not print"); infer("demo","x");', output=emitted.append)
        self.assertEqual(emitted, [])

    def test_indirect_function_effects(self):
        with self.assertRaisesRegex(ShinError, 'missing permit'):
            compile_source('fn hidden(){return infer("demo","x");}')

    def test_dynamic_model_forbidden(self):
        with self.assertRaisesRegex(ShinError, 'literal'):
            compile_source('let name="demo"; infer(name,"x");')

    def test_untrusted_output(self):
        for expr in ['print(d);','print([d]);','if d {print(1);}','print(d + "x");','print(d[0]);']:
            with self.subTest(expr=expr), self.assertRaisesRegex(ShinError, 'untrusted'):
                run('permit model "demo"; let d=infer("demo","x");' + expr,
                    allow_models=['demo'],models={'demo': mock_model()})

    def test_check_text(self):
        self.assertEqual(run('permit model "demo"; print(check_text(infer("demo","hello"),10));',
                             allow_models=['demo'], models={'demo':mock_model()}), ['hello'])

    def test_text_validation_fails(self):
        with self.assertRaisesRegex(ShinError, 'validation failed'):
            run('permit model "demo"; check_text(infer("demo","long"),2);',allow_models=['demo'],models={'demo':mock_model()})

    def test_structured_output(self):
        source=(ROOT/'examples/structured.shin').read_text()
        self.assertEqual(run(source, allow_models=['demo'],models={'demo':mock_model()}), ['First release'])

    def test_schema_rejects(self):
        source='permit model "demo"; check_json(infer("demo","x"),{"n":"number"});'
        for response in ['{"n":true}','{"n":1,"extra":2}','{"n":1,"n":2}','{"n":NaN}','{}','not json','{"n":1e999}']:
            with self.subTest(response=response), self.assertRaises(ShinError):
                run(source,allow_models=['demo'],models={'demo':mock_model(response)})

    def test_malformed_unicode_response(self):
        with self.assertRaisesRegex(ShinError, 'Unicode'):
            run('permit model "demo"; infer("demo","x");',allow_models=['demo'],models={'demo':mock_model('\ud800')})

    def test_input_boundary(self):
        self.assertEqual(run((ROOT/'examples/input.shin').read_text(),input_value={'name':'World','count':3}),['Hello, World'])
        with self.assertRaisesRegex(ShinError,'untrusted'):
            run('print(input());',input_value='unsafe')

    def test_examples(self):
        for filename in ['hello.shin','functions.shin','ai.shin','structured.shin']:
            with self.subTest(filename=filename):
                self.assertTrue(run((ROOT/'examples'/filename).read_text(),allow_models=['demo'],models={'demo':mock_model()}))

    def test_parser_fuzz_is_diagnostic(self):
        randomizer=random.Random(42)
        alphabet='abc012{}[]();+-*/=!" ,\n'
        for _ in range(400):
            source=''.join(randomizer.choice(alphabet) for _ in range(randomizer.randint(1,160)))
            try:
                compile_source(source)
            except ShinError:
                pass

    def test_cli(self):
        result=subprocess.run([sys.executable,'-m','shin','run','examples/ai.shin','--allow-model','demo'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SHIN:',result.stdout)
        denied=subprocess.run([sys.executable,'-m','shin','run','examples/ai.shin'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(denied.returncode,1)
        self.assertNotIn('Traceback',denied.stderr)


if __name__=='__main__':
    unittest.main()
