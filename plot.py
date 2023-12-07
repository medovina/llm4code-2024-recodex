from collections import defaultdict
import csv
from dataclasses import dataclass
from itertools import combinations
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import re
from statistics import mean

import numpy as np

from exercises import *
from line_count import line_count
from models import find_model
from program import *
from results import *
from util import *

models = [find_model(n)[0] for n in ['llama', 'bison', 'gpt-3.5', 'gpt-4']]

def exclude_file(f):
    return 'best_of' in f or 'strong' in f or 'weak' in f

files = os.listdir('results')
scores = defaultdict(lambda: defaultdict(list))
all_results : dict[str, dict[str, list[Result]]] = defaultdict(lambda: defaultdict(list))
trials = defaultdict(int)
for model in models:
    n = 1
    while True:
        base = model if n == 1 else f'{model}_{n}'
        file = f'results/{base}.csv'
        if not os.path.exists(file):
            break
        with open(file) as f:
            results = list(map(parse_result, csv.DictReader(f)))
        if len(results) != len(id_exercises):
            print(f'warning: {file} has {len(results)} exercises, ' +
                    f'but {len(id_exercises)} were expected; ignoring')
        else:
            trials[model] += 1
            for r in results:
                scores[r.id][model].append(r.score)
                all_results[r.id][model].append(r)
        n += 1

@dataclass
class Tally:
    count: int = 0
    total_score: float = 0.0

    def avg(self):
        return self.total_score / self.count

def pass_at_k(n, c, k):
    if n - c < k: return 1.0
    return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

def max_of(vals, k):
    return mean(map(max, combinations(vals, k)))

def model_avg_at(model, k):
    return f'{model} (avg@{k})' if k > 1 else model

def group_by(f, all_by, avg):
    groups = defaultdict(lambda: defaultdict(Tally))
    for id in scores:
        group = f(id)
        for model, vals in scores[id].items():
            match all_by:
                case '1_to_n':
                    by = range(1, trials[model] + 1)
                case '1_and_n':
                    by = {1, trials[model]}
                case '1':
                    by = [1]
                case _:
                    assert False

            for k in by:
                m = model_avg_at(model, k)
                a = groups[group][m]
                a.count += 1
                if avg:
                    score = max_of(vals, k)     # avg@n
                else:
                    score = pass_at_k(len(vals), vals.count(1.0), k)
                a.total_score += score

    return groups

def save(name):
    plt.savefig(f'plots/{name}.svg')
    plt.savefig(f'plots/pdf/{name}.pdf', bbox_inches = 'tight', pad_inches = 0)
    plt.close()

def year_index(year):
    return int((year - 1.0) * 2)

def exercises_by_year():
    langs = defaultdict(lambda: [0] * 7)
    for e in id_exercises.values():
        lang = language(e.runtime)
        year = course_years[e.course]
        langs[lang][year_index(year)] += 1
    
    plt.figure(figsize = (10, 7))
    plt.title('Exercises by course year')
    xs = [x / 2 for x in range(2, 9)]
    total = [0] * 7
    for lang, nums in langs.items():
        plt.bar(xs, nums, 0.4, label = lang, bottom = total)
        total = [x + t for x, t in zip(total, nums)]

    plt.xlabel('Course year')
    plt.ylabel('Exercise count')
    plt.legend()
    save('exercises_by_year')

def base_name(model):
    return re.sub('@.*', '', model)

def avg_over_all():
    fig, axes = plt.subplots(2, 1, figsize = (8, 5))
    for i, ax in enumerate(axes):
        avg = i == 0
        all = group_by(lambda _: None, '1', avg = avg)
        mods = list(reversed(all[None].keys()))
        avg_scores = [t.avg() for t in reversed(all[None].values())]
        colors = [f'C{models.index(base_name(m))}' for m in mods]
        bars = ax.barh(mods, avg_scores, color = colors)
        ax.bar_label(bars, fmt = '%.3f')
        ax.set_xlim(0, 1)
        ax.set_xlabel('avg@1' if avg else 'pass@1')
        kind = 'Average scores' if avg else 'Pass rates'
        ax.set_title(f'{kind} over all exercises')
    plt.subplots_adjust(left = 0.3, hspace = 0.7)
    save('avg_all')

def avg_k():
    i = 0
    for model in models:
        if model.startswith('gpt'):
            for avg in [True, False]:
                kind = 'avg' if avg else 'pass'
                all = group_by(lambda _: None, '1_to_n', avg = avg)
                mods = list(reversed(all[None].keys()))
                avg_scores = [t.avg() for t in reversed(all[None].values())]
                t = trials[model]
                xs = range(1, t + 1)
                ys = [avg_scores[mods.index(model_avg_at(model, k))] for k in xs]
                dash = '-' if avg else '--'
                style = f'o{dash}C{i}'
                plt.plot(xs, ys, style, label = f'{model}: {kind}@k')
            i += 1
    plt.title(f'Avg@k and pass@k by number of samples k')
    plt.xticks(range(1, trials[gpt4] + 1))
    plt.ylim(0.15, 0.75)
    plt.xlabel('Number of samples = k')
    plt.grid(axis = 'y')
    plt.legend()
    plt.subplots_adjust(hspace = 0.7)
    save('avg_k')

def avg_by_year(all_by):
    years = group_by(lambda id: course_years[id_exercises[id].course],
                     '1_to_n' if all_by else '1_and_n', avg = True)
    xs = [y for y, tallies in years.items() if tallies[models[0]].count >= 5]
    xs.sort()

    plt.figure(figsize = (6.5, 4))
    for model in years[xs[0]].keys():
        ys = [years[x][model].avg() for x in xs]
        plt.plot(xs, ys, '.-', label = model)
    plt.xlabel('Year')
    plt.ylabel('Average score')
    plt.legend()
    plt.grid()
    plt.title('Average scores by year of study')

    save('avg_by_year' + ('_all' if all_by else ''))

abbrevs = {
    'Advanced C++ Programming' : 'Advanced C++',
    'C# Language and .NET Framework' : 'C# Language and .NET',
    'Non-Procedural Programming' : 'Non-Proc. Programming'
}

def abbrev(s):
    s = s.replace('Introduction', 'Intro')
    return abbrevs.get(s, s)

def year_ys(courses):
    ys = []
    year = 1
    y = 0
    for c in courses:
        if course_years[c] != year:
            y += 1
            year = course_years[c]
        ys.append(y)
        y += 1
    return ys

def avg_by_course(full):
    def exclude(c, tallies):
        return (tallies[models[0]].count < (2 if full else 5) or
                not full and 'advanced' in c)
    course_map = group_by(lambda id: id_exercises[id].course, '1_and_n', avg = True)
    courses = [c for c, tallies in course_map.items() if not exclude(c, tallies)]
    courses.sort(key = lambda c: course_years[c])

    ys = year_ys(courses)

    plt.figure(figsize = (10, 8))

    mods = list(course_map[courses[0]].keys())
    bar_width = 0.8 / len(mods)
    for i, model in enumerate(mods):
        xs = [course_map[c][model].avg() for c in courses]
        plt.barh([y + i * bar_width for y in ys], xs, bar_width, label = model)

    plt.xlim(0, 1)
    plt.ylim(ys[-1] + 0.8, - .8)
    plt.xlabel('Average score')
    plt.yticks([y + (len(mods) - 1) * bar_width / 2 for y in ys], list(map(abbrev, courses)))
    plt.subplots_adjust(left = 0.4)
    plt.legend()
    plt.grid(axis = 'x')
    plt.title('Average scores by course')

    save('avg_by_course' + ('_full' if full else ''))

gpt4 = find_model('gpt-4')[0]
gpt4_boost = f'{gpt4}@{trials[gpt4]}'

def avg_by_prog_lang():
    map = group_by(lambda id: language(id_exercises[id].runtime), '1', avg = True)
    langs = list(map.keys())
    langs.sort(key = lambda l: map[l][gpt4].avg())
    num_langs = len(langs)
    bar_width = 0.8 / len(models)
    plt.figure(figsize = (6.5, 4))
    for i, model in enumerate(models):
        j = len(models) - i
        xs = [map[l][model].avg() for l in langs]
        plt.barh([y - 0.5 + bar_width * j for y in range(num_langs)], xs, bar_width, label = model)
    plt.xlabel('Average score')
    plt.yticks(range(num_langs), langs)
    plt.legend()
    plt.title('Average scores by programming language')
    save('avg_by_prog_lang')

buckets = ['0.0', '.01-.09'] + [f'.{d}0-.{d}9' for d in range(1, 10)] + ['1.0']

def bucket(score):
    if score == 0:
        return 0
    if score == 1.0:
        return 11
    return int(score * 10) + 1

def dist_gpt_scores(by, f):
    groups = defaultdict(lambda: [0] * 12)

    for id, tallies in scores.items():
        group = f(id)
        max_score = max(tallies[gpt4])
        groups[group][bucket(max_score)] += 1

    plt.figure(figsize = (10, 7))
    total = [0] * 12
    for group in sorted(groups.keys()):
        counts = groups[group]
        plt.bar(buckets, counts, 0.8, label = group, bottom = total)
        total = [x + t for x, t in zip(total, counts)]

    plt.legend()
    plt.xlabel('GPT score')
    plt.ylabel('Count')
    plt.title(f'Distribution of GPT scores by {by} ({gpt4_boost})')
    save(f'dist_by_{by}')
    
all_loc = defaultdict(lambda: defaultdict(list))

def compute_all_loc():
    for id in scores.keys():
        runtime = id_exercises[id].runtime
        for model in models:
            for i in range(1, trials[model] + 1):
                suffix = '' if i == 1 else f'_{i}'
                dir = f'solutions/{model}{suffix}/{id}'
                file = f'{dir}/model_output'
                if not os.path.exists(file):
                    file = f'{dir}/gpt_output'
                if os.path.exists(file):
                    text = read_all(file)
                    program = extract_sources(text)
                    count = sum(line_count(source, runtime, False) for _, source in program)
                else:
                    count = -1
                all_loc[id][model].append(count)

gpt4_loc = {}

def compute_gpt4_loc():
    for id, tallies in scores.items():
        vals = tallies[gpt4]
        max_score = max(vals)
        i = vals.index(max_score)
        gpt4_loc[id] = all_loc[id][gpt4][i]

def score_vs_students():
    success_rate = []
    score = []
    for id, tallies in scores.items():
        avg_best = id_exercises[id].avg_best_score
        if avg_best > 0:
            success_rate.append(avg_best)
            score.append(max(tallies[gpt4]))

    plt.figure(figsize = (10, 7))
    plt.title(f'GPT score vs. avg student score ({gpt4_boost})')
    plt.xlim(0, 1)
    plt.plot(success_rate, score, 'x')
    plt.xlabel('Average student score')
    plt.ylabel('GPT score')
    plt.grid()
    save('score_vs_students')

kinds = {
    'other' : ['node-linux', 'php-linux', 'prolog', 'python3'],
    'C or C++' : ['arduino-gcc', 'c-gcc-linux', 'cxx-gcc-linux'],
    'C# or Java' : ['cs-dotnet-core', 'java'],
    'Haskell' : ['haskell']
}

def avg_by_loc():
    BUCKET = 25
    MAX_BUCKET = 250
    num_buckets = MAX_BUCKET // BUCKET + 1

    def bucket_name(i):
        n = i * BUCKET
        return f'{n}+' if n == MAX_BUCKET else f'{n}-{n + BUCKET - 1}'

    plt.figure(figsize = (10, 4))

    bar_width = 0.8 / len(models)
    for i, model in enumerate(models):
        buckets = defaultdict(Tally)
        for id, score_map in scores.items():
            for n, score in zip(all_loc[id][model], score_map[model]):
                if n != -1:
                    n = min(n, MAX_BUCKET)
                    b = n // BUCKET
                    buckets[b].count += 1
                    buckets[b].total_score += score

        xs = list(buckets.keys())
        ys = [buckets[x].avg() for x in xs]
        plt.bar([x - 0.5 + (i + 1) * bar_width for x in xs], ys, bar_width, label = model)

    plt.xlabel('Lines of code')
    plt.ylabel('Average score')
    plt.xticks(range(num_buckets), [bucket_name(i) for i in range(num_buckets)])
    plt.grid(axis = 'y')
    plt.legend()
    plt.title('Average score by lines of code in solution')
    save('avg_by_loc')

def box_loc():
    locs = []
    for model in models:
        loc = []
        for id, score_map in scores.items():
            for n, score in zip(all_loc[id][model], score_map[model]):
                if n != -1 and score == 1.0:
                    loc.append(n)
        locs.append(loc)
    plt.figure(figsize = (8, 4))
    plt.boxplot(locs, labels = models)
    plt.xlabel('Model')
    plt.ylabel('Lines of code')
    plt.grid(axis = 'y')
    plt.title('Distribution of lines of code of successful solutions')
    save('box_loc')

def score_vs_loc():
    loc = defaultdict(list)
    score = defaultdict(list)
    for id, tallies in scores.items():
        runtime = id_exercises[id].runtime
        max_score = max(tallies[gpt4])
        lines = gpt4_loc[id]
        for kind, runtimes in kinds.items():
            if runtime in runtimes:
                break
        else:
            assert False, 'language not found'
        if lines > 0:
            loc[kind].append(lines)
            score[kind].append(max_score)

    plt.figure(figsize = (11, 8))
    plt.title(f'GPT score vs. lines of code ({gpt4_boost})')
    for kind in kinds.keys():
        plt.plot(loc[kind], score[kind], 'x', label = kind)
    plt.xlabel("Lines of code in GPT's solution")
    plt.ylabel('GPT score')
    plt.grid()
    plt.legend()
    save('score_vs_loc')

def loc_vs_ref_loc(max_lines, xy_line, name, with_unsuccessful):
    kinds = ['score = 0', '0 < score < 1', 'score = 1']
    n_kinds = len(kinds)
    gpt_loc = [[] for _ in range(n_kinds)]
    ref_loc = [[] for _ in range(n_kinds)]
    for id, tallies in scores.items():
        max_score = max(tallies[gpt4])
        if max_score == 0.0:
            k = 0
        elif max_score < 1.0:
            k = 1
        else:
            k = 2
        g = gpt4_loc[id]
        r = id_exercises[id].refs_min_locs
        if 0 < g and 0 < r < max_lines:
            gpt_loc[k].append(g)
            ref_loc[k].append(r)
    plt.figure(figsize = (7, 4))
    plt.plot([0, xy_line], [0, xy_line], 'k--')
    for k in range(n_kinds) if with_unsuccessful else [2]:
        plt.plot(ref_loc[k], gpt_loc[k], 'x', label = kinds[k])
    plt.title(f"Lines of code in GPT-4's solution vs. reference solution")
    plt.xlabel('Lines of code in reference solution')
    plt.ylabel("Lines of code in GPT-4's solution")
    if with_unsuccessful:
        plt.legend()
    save(name)

def failure_bar():
    count = defaultdict(int)
    outcomes = defaultdict(lambda: defaultdict(int))

    for id, result_map in all_results.items():
        e = id_exercises[id]
        for r in result_map[gpt4]:
            if r.score == 1.0:
                outcome = 'passed'
            elif r.other_error > 0:
                outcome = 'no program'
            elif r.compile_error > 0:
                outcome = 'compilation error'
            else:
                limit = r.time_limit + r.memory_limit
                m = max(limit, r.runtime_error, r.wrong_output)
                if m == limit:
                    outcome = 'time or memory limit'
                elif m == r.runtime_error:
                    outcome = 'runtime error'
                else:
                    outcome = 'wrong output'
            count[e.course] += 1
            outcomes[e.course][outcome] += 1

    plt.figure(figsize = (10, 7))
    courses = [course for course, n in reversed(count.items())
                      if n >= 5 * trials[gpt4] and 'advanced' not in course ]
    courses.sort(key = lambda c: course_years[c], reverse = True)

    ys = year_ys(courses)

    n_courses = len(courses)
    bottom = [0] * n_courses
    for out in ['no program', 'compilation error', 'time or memory limit',
                'wrong output', 'runtime error', 'passed']:
        fracs = [outcomes[c][out] / count[c] for c in courses]
        plt.barh(ys, fracs, 0.6, bottom, label = out)
        bottom = [b + f for b, f in zip(bottom, fracs)]

    plt.legend(ncols = 2)
    plt.ylim(0, max(ys) + 4)
    plt.yticks(ys, list(map(abbrev, courses)))
    plt.subplots_adjust(left = 0.3)
    plt.xlabel('Fraction of solutions')
    plt.title('GPT-4 solution outcomes')
    save('failure_bar')

os.makedirs('plots/pdf', exist_ok = True)
print('counting lines...')
compute_all_loc()
compute_gpt4_loc()
print('done')

exercises_by_year()
avg_over_all()
avg_k()
avg_by_year(False)
avg_by_year(True)
avg_by_course(False)
avg_by_course(True)
avg_by_prog_lang()
score_vs_students()
dist_gpt_scores('year', lambda id: 'year ' + str(course_years[id_exercises[id].course]))
dist_gpt_scores('language', lambda id: language(id_exercises[id].runtime))
avg_by_loc()
score_vs_loc()
box_loc()
loc_vs_ref_loc(250, 230, 'loc_vs_ref_loc_small', False)
loc_vs_ref_loc(1200, 350, 'loc_vs_ref_loc_all', False)
failure_bar()
