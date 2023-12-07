import csv
from dataclasses import dataclass
import math

@dataclass
class Exercise:
    id: str
    name: str
    runtime: str
    lang: str
    text_length: int
    attachments_count: int
    group_name_1: str
    group_name_2: str
    course: str
    avg_best_score: float
    refs_min_locs: float

id_exercises = {}

def to_float(s):
    return 0.0 if s == '' else float(s)

with open(f'exercises/exercises.csv') as f:
    for row in csv.DictReader(f):
        best_score = float(row['ref_best_score'])
        external_links = int(row['links_extern'])
        exclude = bool(row['exclude'])
        ok = row['ok'].strip().lower() == '1'
        assert not (exclude and ok)
        
        if best_score == 1.0 and not exclude and (ok or external_links == 0):
            id = row['id']
            runtime = row['runtime']
            course = row['course']
            group1, group2 = row['group_name_1'], row['group_name_2']
            if not course:
                assert group2 == ''
                match group1:
                    case 'Programming I and II':
                        p1_map = { 'python3' : 'Programming 1', 'cs-dotnet-core' : 'Programming 2' }
                        course = p1_map[runtime]
                    case 'Algoritmizace':
                        assert runtime == 'python3'
                        course = 'Introduction to Algorithms'
                    case _:
                        course = group1

            e = Exercise(id, row['name'], runtime, row['locale'],
                            int(row['text_length']), int(row['attachments_count']),
                            group1, group2, course,
                            to_float(row['avg_best_score']), to_float(row['refs_min_locs']))
            id_exercises[id] = e

with open('exercises/courses.csv') as f:
    course_years = dict((row['course'], float(row['year'])) for row in csv.DictReader(f))

def exercise_len(e):
    n = e.text_length
    return math.inf if n < 0 else n

def read_all_exercises():
    return list(sorted(id_exercises.values(), key = exercise_len))
