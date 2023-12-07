import csv
from dataclasses import dataclass

from program import *

@dataclass
class Result:
    id: str
    name: str
    runtime: str
    lang: str
    num_attachments: int
    submitted_attachments: int
    in_tokens: int
    out_tokens: int
    total_tokens: int
    score: float
    boosted: bool
    tests: int
    passed: int
    compile_error: int
    runtime_error: int
    wrong_output: int
    time_limit: int
    memory_limit: int
    other_error: int

def parse_result(row):
    r = Result(row['id'], row['name'], row['runtime'], row['lang'],
                int(row['num_atts']), int(row['sub_atts']),
                int(row.get('in_tokens', '0')),
                int(row.get('out_tokens', '0')),
                int(row.get('total_tokens', '0')),
                float(row['score']), False, int(row['tests']), int(row['passed']),
                int(row['comp_err']), int(row['rt_err']), int(row['wrong_output']),
                int(row['time_limit']), int(row['mem_limit']), int(row['other_err']))
    if e := row.get('gpt_err'):      # old field
        r.other_error += int(e)
    return r
