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
    course: str
    avg_best_score: float
    refs_min_locs: float

id_exercises = {}

def to_float(s):
    return 0.0 if s == '' else float(s)

with open(f'exercises/exercises.csv') as f:
    for row in csv.DictReader(f):
        id = row['id']
        runtime = row['runtime']
        course = row['course']

        e = Exercise(id, row['name'], runtime, row['locale'],
                        int(row['text_length']), int(row['attachments_count']),
                        course,
                        to_float(row['avg_best_score']), to_float(row['refs_min_locs']))
        id_exercises[id] = e

with open('exercises/courses.csv') as f:
    course_years = dict((row['course'], float(row['year'])) for row in csv.DictReader(f))

def exercise_len(e):
    n = e.text_length
    return math.inf if n < 0 else n

def read_all_exercises():
    return list(sorted(id_exercises.values(), key = exercise_len))
