import csv
from dataclasses import dataclass
from datetime import datetime
import json
import math
import os
from os import path
import re
import subprocess
from subprocess import PIPE, STDOUT, TimeoutExpired
import sys
import time
from util import *
import zipfile

from exercises import *
from models import *
from program import *

def usage():
    print(f'usage: py {sys.argv[0]} <model> [args...]')
    print('  -e <ext>: only evaluate exercises with the given language extension')
    print('  -i: let model make function calls to run code')
    print('  -l <cs|en>: only evaluate exercises in the given language')
    print('  -m <num>: stop when exercise count reaches the given value')
    print('  -n: nudge for another program if evaluation fails')
    print('  -ps: prompt that you are a strong programmer')
    print('  -pw: prompt that you are a weak programmer')
    print('  -s <num>: sample number')
    print('  -v: verbose output')
    print('  -1: only evaluate one exercise, then exit')
    exit()

def results_in(filename, all):
    with open(filename) as f:
        return set(row['id'] for row in csv.DictReader(f) if all or float(row['score']) == 1.0)

if len(sys.argv) < 2:
    usage()
model, model_prefix, token_limit = find_model(sys.argv[1])

engine = get_engine(model)
is_gpt = isinstance(engine, GPT)

sample = 1
interactive = nudge = only_one = prompt_strong = prompt_weak = verbose = False
only_ext = only_lang = None
stop_count = -1

i = 2
while i < len(sys.argv):
    match sys.argv[i]:
        case '-e':
            i += 1
            only_ext = sys.argv[i]
        case '-i':
            interactive = True
        case '-l':
            i += 1
            only_lang = sys.argv[i]
        case '-m':
            i += 1
            stop_count = int(sys.argv[i])
        case '-n':
            nudge = True
        case '-ps':
            prompt_strong = True
        case '-pw':
            prompt_weak = True
        case '-s':
            i += 1
            sample = int(sys.argv[i])
            assert sample > 1
        case '-v':
            verbose = True
        case '-1':
            only_one = True
        case _:
            usage()
    i += 1

assert not (nudge and interactive)

def extra_suffix():
    return '' if sample == 1 else f'_{sample}'

def seed():
    return sample + 1000 * int(nudge) + 2000 * int(interactive)

def model_boost():
    suffix = '_weak' if prompt_weak else '_strong' if prompt_strong else ''
    suffix += '_nudge' if nudge else '_interact' if interactive else ''
    return model + suffix + extra_suffix()

results_header = (
            'time,' +
            ('fprint,seed,' if is_gpt else '') +
            'id,group1,group2,name,runtime,lang,num_atts,sub_atts,' +
            ('in_tokens,out_tokens,total_tokens,' if is_gpt else '') +
            ('icalls,ecalls,' if interactive else '') +
            ('rep,' if nudge or interactive else '') +
            'score,tests,passed,' +
            'comp_err,rt_err,wrong_output,time_limit,mem_limit,' +
            'other_err,error_msg\n')

def open_results():
    os.makedirs('results', exist_ok = True)
    results_file = f'results/{model_boost()}.csv'

    if path.exists(results_file):
        results = results_in(results_file, all = True)
        results_out = open(results_file, 'a')
    else:
        results = set()
        results_out = open(results_file, 'w')
        results_out.write(results_header)

    return results, results_out

def valid_attachment(name, size):
    ext = path.splitext(name)[1]
    return ext not in ['.jar', '.pdf', '.png', '.svg', '.zip'] and size < 8 * 1024

def build_spec(e):
    spec = read_all(f'exercises/data/{e.id}.md')
    spec = re.sub(r'\(<?https://recodex[^)]*\)', '', spec)
    tokens = engine.token_count(spec)
    if tokens > 0.9 * token_limit:
        return None, 0, 0

    attach_dir = f'exercises/data/{e.id}'
    if path.exists(attach_dir):
        attachment_files = list(os.scandir(attach_dir))
    else:
        attachment_files = []

    attachments = []
    num_attachments = submitted_attachments = 0
    for a in sorted(attachment_files, key = lambda a: a.name):
        if (a.path.endswith('.zip')):
            with zipfile.ZipFile(a.path) as zip:
                for name in zip.namelist():
                    if not name.endswith('/'):
                        num_attachments += 1
                        info = zip.getinfo(name)
                        if valid_attachment(name, info.file_size):
                            try:
                                text = fix(str(zip.read(name), 'utf-8'))
                            except UnicodeDecodeError:
                                continue    # ignore binary file
                            attachments.append((name, text))
        else:
            num_attachments += 1
            if valid_attachment(a.name, a.stat().st_size):
                try:
                    text = read_all(a.path)
                except UnicodeDecodeError:
                    continue    # ignore binary file
                attachments.append((a.name, text))
    
    for (name, text) in attachments:
        attachment_text = f'\n=== {name} ===\n' + text
        t = engine.token_count(attachment_text)
        if tokens + t < 0.7 * token_limit:
            spec += attachment_text
            tokens += t
            submitted_attachments += 1

    return spec, num_attachments, submitted_attachments

def print_expression(ext, expr):
    match ext:
        case 'c':
            return f'''
#include <stdio.h>

int main() {{
    printf("%d\n", {expr});
    return 0;
}}'''
        case 'cpp':
            return f'''
#include <iostream>

int main() {{
    std::cout << {expr} << std::endl;
    return 0;
}}'''
        case 'cs':
            return f'''
class MainProg {{
    static void Main(string[] args) {{
        Console.WriteLine({expr});
    }}
}}'''
        case 'hs':
            return f'''
main = print $ {expr}
'''
        case 'java':
            return f'''
class MainProg {{
    public static void main(String[] args) {{
        System.out.println({expr});
    }}
}}'''
        case 'pl':
            return ''
        case 'py':
            return f'print({expr})'
        case _:
            assert False, 'unknown extension'

def source_with(named_sources, regexp):
    for name, source in named_sources:
        if re.search(regexp, source) != None:
            return name
    return None

def java_main_class(named_sources):
    for name, source in named_sources:
        cls = None
        for line in source.split('\n'):
            if m := re.search(r'\bclass +(\w+)', line):
                cls = m[1]
            elif re.search(r' +main\(', line):
                return cls
    return None

RUN_TIMEOUT = 20

def run_program(named_sources, extension, input):
    dir = 'run'
    new_dir(dir)

    if extension == 'cs':
         run('(cd run; dotnet new console; rm Program.cs)')

    for name, source in named_sources:
        write_to(f'{dir}/{name}', source)

    compile = None
    match extension:
        case 'c':
            compile = '(cd run; gcc -Wall *.c)'
            cmd = './a.out'
        case 'cpp':
            compile = '(cd run; g++ -Wall *.cpp)'
            cmd = './a.out'
        case 'cs':
            compile = '(cd run; dotnet build)'
            cmd = 'bin/Debug/net7.0/run'
        case 'hs':
            m = source_with(named_sources, r'(^|\n)main +=')
            if not m:
                return "error: can't find main source file"
            cmd = f'runghc {m}'
        case 'java':
            compile = '(cd run; javac *.java)'
            cls = java_main_class(named_sources)
            if not cls:
                return "error: can't find main class"
            cmd = f'java {cls}'
        case 'pl':
            shutil.copy('lang/wrapper.pl', dir)
            names = ' '.join(name for name, _ in named_sources)
            cmd = f'swipl -g recodex_main wrapper.pl {names}'
        case 'py':
            cmd = f'python {named_sources[0][0]}'
        case _:
            assert False, "can't run this program type"

    if compile:
        err, output = run_with_exit_code(compile)
        if err > 0:
            return output

    c = f'firejail --quiet --private={dir} {cmd}'
    print(c)
    print(input)

    process = subprocess.Popen(c, stdin = PIPE, stdout = PIPE, stderr = STDOUT,
                               shell = True, text = True)
    try:
        out, _err = process.communicate(input, timeout = RUN_TIMEOUT)
        return out
    except TimeoutExpired:
        process.terminate()
        return f'timeout: program exceeded maximum allowable time of {RUN_TIMEOUT} seconds'

def eval_expression(program, ext, expr):
    name, source = program[0]
    source += '\n' + print_expression(ext, expr)

    program2 = program[:]
    program2[0] = name, source
    return run_program(program2, ext, expr if ext == 'pl' else '')

def functions(prog_lang, prog_lang_id, ext):
    f = []
    prog_desc = f'''\
The {prog_lang} program, consisting of one or more source files.  For each source file,
this string should contain a filename in the form "=== filename ===",
followed by the contents of the file.'''
    
    if has_run(ext):
        f.append({
            'name': prog_lang_id,
            'description':
                f"Run a {prog_lang} program with given input.  Returns the program's output.",
            'parameters': {
                'type': 'object',
                'properties': {
                    'program': {
                        'type': 'string',
                        'description': prog_desc,
                    },
                    'input': {
                        'type': 'string',
                        'description': 'Standard input to the program'
                    }
                },
                'required': ['program', 'input']
            }
        })
    if has_eval(ext):
        if ext == 'pl':
            desc = 'Call a predicate in a Prolog program.'
            kind = 'predicate'
        else:
            desc = f"Call a function in a {prog_lang} program. Returns the function's return value."
            kind = 'function'
        f.append({
            'name': f'{prog_lang_id}_eval',
            'description': desc,
            'parameters': {
                'type': 'object',
                'properties': {
                    'program': {
                        'type': 'string',
                        'description': prog_desc,
                    },
                    'expression': {
                        'type': 'string',
                        'description': f'The {kind} to call and its parameters'
                    }
                },
                'required': ['program', 'expression']
            }
        })
    return f

def has_eval(ext):
    return ext in ['cpp', 'cs', 'hs', 'java', 'pl', 'py']

def has_run(ext):
    return ext in ['c', 'cpp', 'cs', 'hs', 'java', 'py']

def can_interact(ext):
    return interactive and (has_eval(ext) or has_run(ext))

format_prompt ='''\
For each source file, output a filename in the format "=== filename ===",
followed by the file's contents.
After you have output all source files, output a final line "====".
'''

if prompt_weak:
    prompt_prefix = '''\
You are an inexperienced and uneducated computer programmer who frequently makes
conceptual errors and careless mistakes.
'''
elif prompt_strong:
    prompt_prefix = '''\
You are a brilliant software engineer and computer programmer who has a solid
computer science education and many years of programming experience.
'''
else:
    prompt_prefix = ''

def prompt(prog_lang, prog_lang_id, ext):
    p = f'''{prompt_prefix}\
Write a program in {prog_lang} that solves the given exercise.
Your program should not prompt the user for input.\n'''

    if can_interact(ext):
        if has_eval(ext) and has_run(ext):
            p += f'''\
If your program performs input and output, test it by calling
the function {prog_lang_id}() and providing sample input.
Otherwise, test its functions by calling {prog_lang_id}_eval().\n'''
        elif has_run(ext):
            p += f'''\
Test your program by calling the function {prog_lang_id}() and providing sample input.\n
'''
        else:   # prolog
            p += f"""\
Test your program's predicates by calling {prog_lang_id}_eval().\n
"""
        p += f'''\
If a test produces an incorrect result, try to improve your program,
then test it again.\n'''

    your_prog = 'The final version of your program' if can_interact(ext) else 'Your program'

    p += f'{your_prog} will consist of one or more source files.\n'
    p += format_prompt + 'Do not output any explanatory text.\n'

    if prog_lang_id == 'arduino':
        p += f'''\
Follow these coding guidelines:
''' + read_all('exercises/coding-guidelines.md')

    return p

def build_query(spec, prog_lang, prog_lang_id, extension):
    system = prompt(prog_lang, prog_lang_id, extension)
    messages = [ engine.sys_message(system) ]

    for example in ['hello', 'sum', 'add']:
        ex_filename = f'{example}.{extension}'
        ex_path = f'examples/{ex_filename}'
        if path.exists(ex_path):
            f = 'sum' if example == 'sum' else f'{example}_{extension}'
            f = 'examples/' + f
            ex_spec = read_all(f)
            solution = read_all(ex_path)
            named_solution = f'=== {ex_filename} ===\n' + solution + '====\n'

            fun = parameter = arg = output = None
            if example == 'sum':
                fun = prog_lang_id
                parameter = 'input'
                arg = read_all('examples/sum_in')
                output = read_all('examples/sum_out')
            elif example == 'add':
                fun = prog_lang_id + '_eval'
                parameter = 'expression'

                lines = ex_spec.strip().split('\n')
                assert lines[-3] == '==='
                arg = lines[-2]
                output = lines[-1]
                ex_spec = '\n'.join(lines[:-3]) + '\n'
            messages.append(engine.user_message(ex_spec))

            if isinstance(engine, GPT) and can_interact(extension) and fun:
                example_args = { 'program' : named_solution, parameter : arg }
                messages.append(engine.fun_call(fun, example_args))
                messages.append(engine.fun_result(fun, output))

            messages.append(engine.assistant_message(named_solution))

    assert len(messages) > 1
    messages.append(engine.user_message(spec))
    return messages

def extract(model_out, dir):
    error = ''
    model_out_lines = model_out.split('\n')

    if len(model_out_lines) == 1 and 'assist with that' in model_out:
        # e.g. "I'm sorry, but I can't assist with that."
        error = 'gave up'
        program = None
    else:
        program = extract_sources(model_out)
        if program == []:
            error = 'no filename provided'
        filenames = set()
        for filename, _ in program:
            if filename in filenames:
                error = f'duplicate filename {filename}'
                break
            filenames.add(filename)

    if error:
        print(f'bad response: {error}')
    else:
        assert program
        for name, text in program:
            write_to(f'{dir}/{name}', text)

    return program, error

MAX_QUERIES = 3

recodex_system_user = 'ad3d451f-41ef-4c70-a234-094d743511f3'

def recodex_query1(cmd):
    delay = 1
    while True:
        ret, out, stderr = run_with_stderr(f'recodex {cmd}')
        
        if 'Temporary failure in name resolution' in stderr:
            print('name resolution failure, retrying...')
            delay *= 1.5
        else:
            return ret, out, stderr

def recodex_query(cmd):
    ret, out, stderr = recodex_query1(cmd)
    if ret > 0:
        print(stderr)
        assert False, 'recodex command failed'
    return out

def submit_to_recodex(id, runtime, dir, program):
    paths = [f'{dir}/{name}' for name, _ in program]
    if runtime == 'cs-dotnet-core':
        paths.append('lang/global_implicit.cs')
             
    for sol in json.loads(recodex_query(f'exercises get-ref-solutions --json {id}')):
        if sol['authorId'] == recodex_system_user and sol['description'].startswith(model_prefix):
            recodex_query(f'exercises delete-ref-solution {sol["id"]}')

    cmd = ('exercises add-reference-solution ' +
                f'-r {runtime} -e {id} -n {model} {" ".join(paths)}')
    exit_code, stdout, stderr = recodex_query1(cmd)
    if exit_code > 0:
        print(stderr)
        m = re.search(r'RuntimeError: Received error from API: (.*)\n', stderr)
        assert m
        assert 'You cannot create reference solutions' not in m[1]
        return (None, m[1])

    solution_id = stdout.strip()
    if solution_id == '':
        return (None, 'no solution id')

    delay = 1
    while True:
        time.sleep(delay)
        eval_json = recodex_query(f'exercises get-ref-solution-evaluations --json {solution_id}')
        # print(eval_json)
        eval_block = json.loads(eval_json)[0]
        if eval_block['evaluationStatus'] != 'work-in-progress':
            break
        print('evaluation unavailable, retrying...')
        delay *= 1.5

    e = eval_block['evaluation']
    return (e, '') if e else (None, 'no evaluation')

@dataclass
class Evaluation:
    score: float = 0
    tests: int = 0
    passed: int = 0
    compile_error: int = 0
    compile_error_text: str = ''
    runtime_error: int = 0
    wrong_output: int = 0
    time_limit: int = 0
    memory_limit: int = 0
    other_error: int = 0
    error_msg: str = ''

def recodex_eval(id, runtime, dir, program):
    res, error_msg = submit_to_recodex(id, runtime, dir, program)
    eval = Evaluation()

    if not res:
        print(f'evaluation failed: {error_msg}')
        eval.tests = 1
        eval.other_error = 1
        eval.error_msg = error_msg
    else:
        test_results = res['testResults']
        eval.compile_error_text = res['initiationOutputs']

        eval.score = float(res['score'])
        eval.tests = len(test_results)

        for r in test_results:
            if r['score'] == 1.0:
                eval.passed += 1
            elif r['status'] == 'SKIPPED':
                eval.compile_error += 1
            else:
                assert r['status'] == 'FAILED'
                if r['cpuTimeExceeded'] or r['wallTimeExceeded']:
                    eval.time_limit += 1
                elif r['memoryExceeded']:
                    eval.memory_limit += 1
                elif r['exitCode'] > 0 or r['exitSignal'] > 0:
                    eval.runtime_error += 1
                else:
                    eval.wrong_output += 1

    print(f'score: {eval.score:.2f} ({eval.passed}/{eval.tests} passed)\n')
    return eval

def add_nudge(eval, query):
    most = max(eval.compile_error, eval.runtime_error, eval.wrong_output,
               eval.time_limit, eval.memory_limit, eval.other_error)
    tests = ('Some' if most < eval.tests else 'All') + ' test cases'
    match most:
        case eval.compile_error:
            error_text = ''
            for line in eval.compile_error_text.split('\n'):
                s = error_text + line + '\n'
                if len(s) > 2000:
                    error_text += '...\n'
                    break
                error_text = s
            n = 'The program failed to compile:\n\n' + error_text
        case eval.runtime_error:
            n = f'{tests} produced a runtime error.'
        case eval.wrong_output:
            n = f'{tests} produced incorrect output.'
        case eval.time_limit:
            n = f'{tests} exceeded the time limit.'
        case eval.memory_limit:
            n = f'{tests} exceeded the memory limit.'
        case eval.other_error:
            n = 'The program failed to compile.  Some file extensions may be invalid.'
        case _:
            assert False

    msg = ('Your program is incorrect.\n' + n +
           '\nPlease fix the program and output a new version.\n' + format_prompt)
    print(msg)
    query.append(engine.user_message(msg))

def interact(cdir, gres, query):
    if gres.funcall != '':
        if gres.funcall == prog_lang_id:
            output = run_program(program, extension, gres.input)
        elif gres.funcall == f'{prog_lang_id}_eval':
            output = eval_expression(program, extension, gres.expr)
        else:
            assert False, 'unknown function'

        print('** output: **\n' + output)
        write_to(f'{cdir}/output', output)

        assert(isinstance(engine, GPT))
        query.append(engine.fun_result(gres.funcall, output))

def output_line(file, e, num_attachments, submitted_attachments, gresults, eval):
    in_tokens = out_tokens = total_tokens = icalls = ecalls = 0
    if is_gpt:
        for gres in gresults:
            in_tokens += gres.in_tokens
            out_tokens += gres.out_tokens
            total_tokens += gres.total_tokens

            if gres.input != None:
                icalls += 1
            if gres.expr != None:
                ecalls += 1
        
    line = (
        f'{datetime.now().isoformat()},' +
        (f'{gresults[0].fingerprint},{seed()},' if is_gpt else '') +
        f'{e.id},{enc(e.group_name_1)},{enc(e.group_name_2)},{enc(e.name)},{e.runtime},{e.lang},' +
        f'{num_attachments},{submitted_attachments},' +
        (f'{in_tokens},{out_tokens},{total_tokens},' if is_gpt else ''))
    if interactive:
        line += f'{icalls},{ecalls},'
    if nudge or interactive:
        line += f'{len(gresults)},'

    if eval:
        line += (
            f'{eval.score:.2f},{eval.tests},{eval.passed},' +
            f'{eval.compile_error},{eval.runtime_error},{eval.wrong_output},' +
            f'{eval.time_limit},{eval.memory_limit},{eval.other_error},{eval.error_msg}')
    else:
        assert len(gresults) == 1
        line += f'0.0,1,0,0,0,0,0,0,1,{gresults[0].error}'

    file.write(line + '\n')
    file.flush()

exercises = read_all_exercises()
done, results_out = open_results()
os.makedirs('solutions', exist_ok = True)

for e in exercises:
    if e.id in done or 'pascal' in e.runtime:
        continue

    (prog_lang, _, extension) = languages[e.runtime]
    if only_ext and extension != only_ext or only_lang and e.lang != only_lang:
        continue

    count = len(done) + 1
    if stop_count >= 0 and count > stop_count:
        break
    print(f'== [{count}] {e.name} ({prog_lang}) ==\n')

    dir = f'solutions/{model_boost()}/{e.id}'
    new_dir(dir)

    spec, num_attachments, submitted_attachments = build_spec(e)
    assert spec != None, 'specification is too long'
    print(spec)

    (prog_lang, prog_lang_id, extension) = languages[e.runtime]
    query = build_query(spec, prog_lang, prog_lang_id, extension)

    funs = functions(prog_lang, prog_lang_id, extension) if can_interact(extension) else None

    gpt_results = []
    programs = []
    evals = []

    max_queries = MAX_QUERIES if nudge or interactive else 1
    for i in range(max_queries):
        if max_queries > 1:
            cdir = f'{dir}/{i + 1}'
            os.makedirs(cdir)
            label = f'{count}/{i + 1}'
        else:
            cdir = dir
            label = f'{count}'

        print(f'[{label}] querying {model}...')
        gres = engine.query(seed(), query, funs, verbose)
        gres.program = gres.program.replace('\r', '')
        gres.program = '\n'.join(line for line in gres.program.split('\n')
                                 if not line.startswith('```'))

        gpt_results.append(gres)
        if gres.error:
            print(f'error: {gres.error}')
            break

        print('\n** program: **\n' + gres.program)
        write_to(f'{cdir}/model_output', gres.program)

        if isinstance(gres, GptResult) and gres.funcall != None:
            print(f'model is calling function {gres.funcall}()')
            if gres.funcall == prog_lang_id:
                if gres.input == None:
                    print('No input provided!  Skipping function call.')
                    gres.funcall = None
                else:
                    print('\n** input: **\n' + gres.input)
                    write_to(f'{cdir}/input', gres.input)
            elif gres.funcall == f'{prog_lang_id}_eval':
                if not gres.expr:
                    print('No expression provided!  Skipping function call.')
                    gres.funcall = None
                else:
                    print(f'** expression: {gres.expr}')
                    write_to(f'{cdir}/expr', gres.expr)
            else:
                print('Unknown function.  Skipping function call.')
                gres.funcall = None

        program, gres.error = extract(gres.program, cdir)
        if gres.error:
            break

        programs.append(program)

        if i == 0 or program != programs[i - 1]:
            eval = recodex_eval(e.id, e.runtime, cdir, program)
            evals.append(eval)
            if eval.score == 1.0:
                break
        else:
            evals.append(evals[-1])

        if i < max_queries - 1:
            if nudge:
                add_nudge(eval, query)

            if interactive:
                assert isinstance(gres, GptResult)
                if gres.funcall != None:
                    interact(cdir, gres, query)
                else:
                    break

    i = 0
    while i < len(gpt_results):
        eval = evals[i] if i < len(evals) else None
        j = i + 1
        while j < len(programs) and programs[j] == programs[i]:
            j += 1
        output_line(results_out, e, num_attachments, submitted_attachments,
                    gpt_results[i : j], eval)
        i = j
        
    done.add(e.id)
    if only_one:
        break

results_out.close()
