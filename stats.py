from collections import defaultdict
import csv
import itertools
import sys

from exercises import *
from models import *
from program import *
from results import *

def usage():
    print(f'usage: py {sys.argv[0]} <model> [args...]')
    print(f'  -b <suffixes>: return best results from given files')
    print(f'  -i: use interactive results file')
    print(f'  -m <num>: only use first <num> results in computing statistics')
    print(f'  -n: use nudge results file')
    print(f'  -ps: use results file with strong prompt')
    print(f'  -pw: use results file with weak prompt')
    print(f'  -v: verbose')
    exit()

if len(sys.argv) < 2:
    usage()

model = find_model(sys.argv[1])[0]
is_gpt = model.startswith('gpt-')
suffix = ''
boost = verbose = False
best = None
first_n = None

i = 2
while i < len(sys.argv):
    match sys.argv[i]:
        case '-b':
            i += 1
            best = sys.argv[i].split(',')
        case '-i':
            boost = True
            suffix = '_interact'
        case '-m':
            i += 1
            first_n = int(sys.argv[i])
        case '-n':
            boost = True
            suffix = '_nudge'
        case '-ps':
            suffix = '_strong'
        case '-pw':
            suffix = '_weak'
        case '-v':
            verbose = True
        case _:
            usage()
    i += 1

if first_n != None:
    only_ids = {e.id for e in read_all_exercises()[:first_n]}
else:
    only_ids = None

def write_header(f, key, boosted):
    f.write(f'{key},count,')
    if boosted:
        f.write('boosted,')
    f.write('avg_score,passed,' +
            'compile_error,runtime_error,wrong_output,time_limit,mem_limit,' +
            'other_error\n')

def write_stats(f, key_val, results, boosted):
    count = len(results)
    avg_score = sum(r.score for r in results) / count
    tests = sum(r.tests for r in results)

    passed = sum(r.passed for r in results)
    compile_error = sum(r.compile_error for r in results)
    runtime_error = sum(r.runtime_error for r in results)
    wrong_output = sum(r.wrong_output for r in results)
    time_limit = sum(r.time_limit for r in results)
    memory_limit = sum(r.memory_limit for r in results)
    other_error = sum(r.other_error for r in results)

    def per(x):
        p = 100 * x / tests
        return f'{p:.1f}%'

    f.write(f'{key_val},{count},')
    if boosted:
        b = sum(r.boosted for r in results)
        f.write(f'{b},')
    f.write(f'{avg_score:.2f},{per(passed)},' +
            f'{per(compile_error)},{per(runtime_error)},{per(wrong_output)},' +
            f'{per(time_limit)},{per(memory_limit)},{per(other_error)}\n')

def write_by(all_results, f, key, key_fun, boosted):
    f.write(f'\n=== by {key} ===\n\n')
    write_header(f, key, boosted)

    for key_val in sorted(set(map(key_fun, all_results))):
        write_stats(f, key_val, [r for r in all_results if key_fun(r) == key_val], boosted)

def attachment_status(r):
    if r.num_attachments == 0:
        return 'none'
    return 'all' if r.submitted_attachments == r.num_attachments else 'partial'

def get_results(suffix, boosted):
    all_results = []
    with open(f'results/{model}{suffix}.csv') as f:
        for id, rows in itertools.groupby(map(parse_result, csv.DictReader(f)), lambda r: r.id):
            if only_ids and id not in only_ids:
                continue
            rows = list(rows)
            if boosted:
                row = max(rows, key = lambda r: r.score)
                row.boosted = row.score > rows[0].score
                row.in_tokens = sum(r.in_tokens for r in rows) 
                row.out_tokens = sum(r.out_tokens for r in rows) 
                row.total_tokens = sum(r.total_tokens for r in rows) 
            else:
                row = rows[0]

            all_results.append(row)
    
    return all_results

def prog_lang(r):
    return language(r.runtime).lower()

def write_all_stats(f, all_results, boosted):
    f.write('\n=== all exercises ===\n\n')
    write_header(f, '', boosted)
    write_stats(f, '(all)', all_results, boosted)

    write_by(all_results, f, 'language', lambda r: r.lang, boosted)
    write_by(all_results, f, 'runtime', lambda r: r.runtime, boosted)
    write_by(all_results, f, 'attachments', attachment_status, boosted)

    by_course = defaultdict(list)
    for r in all_results:
        course = id_exercises[r.id].course
        year = course_years[course]
        by_course[(year, course, prog_lang(r))].append(r)

    f.write(f'\n=== by course ===\n\n')
    write_header(f, 'course,year,prog_lang', boosted)
    
    for (year, course, runtime), results in sorted(by_course.items()):
        write_stats(f, f'{course},{year},{runtime}', results, boosted)

first_suffix = f'_{first_n}' if first_n != None else ''

def gen_stats(extra, boosted):
    all_results = get_results(suffix, boosted)

    os.makedirs('stats', exist_ok = True)
    with open(f'stats/{model}{suffix}{extra}{first_suffix}.csv', 'w') as f:
        if is_gpt:
            in_tokens = sum(r.in_tokens for r in all_results)
            out_tokens = sum(r.out_tokens for r in all_results)
            total_tokens = sum(r.total_tokens for r in all_results)
            
            f.write('=== tokens ===\n\n')
            f.write(f'total_in_tokens,{in_tokens}\n')
            f.write(f'total_out_tokens,{out_tokens}\n')
            f.write(f'total_inout_tokens,{total_tokens}\n')

            # cost of gpt-3.5-turbo-1106, gpt-4-1106-preview
            cost_gpt_3_5 = in_tokens / 1000 * 0.001 + out_tokens / 1000 * 0.002
            cost_gpt_4 = in_tokens / 1000 * 0.01 + out_tokens / 1000 * 0.03
            f.write(f'"cost (GPT 3.5, 16K)",${cost_gpt_3_5:.2f}\n')
            f.write(f'"cost (GPT 4, 128K)",${cost_gpt_4:.2f}\n')

        write_all_stats(f, all_results, boosted)

if best:
    result_map = defaultdict(list)
    fieldnames = None
    for suffix in best:
        if suffix != '':
            suffix = '_' + suffix
        with open(f'results/{model}{suffix}.csv') as f:
            reader = csv.DictReader(f)
            if not fieldnames:
                assert reader.fieldnames
                fieldnames = list(reader.fieldnames)
            for r in reader:
                id = r['id']
                if only_ids and id not in only_ids:
                    continue
                result_map[id].append(r)

    assert fieldnames
    s = fieldnames.index('score')
    fieldnames.insert(s, 'scores')
    full_name = f'{model}_best_of_{len(best)}{first_suffix}.csv'

    with open(f'results/{full_name}', 'w') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        best_results = []
        for id, results in result_map.items():
            scores = [float(r['score']) for r in results]
            max_score = max(scores)
            i = scores.index(max_score)
            best = results[i]
            best['scores'] = str(scores)
            writer.writerow(best)
            best_results.append(parse_result(best))

    with open(f'stats/{full_name}', 'w') as f:
        write_all_stats(f, best_results, False)
elif boost:
    gen_stats('_pre', False)
    gen_stats('', True)
else:
    gen_stats('', False)
