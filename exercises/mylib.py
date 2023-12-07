import csv
import os
import subprocess
import sys
import json
import io


def file_read(file_name):
    if not os.path.isfile(file_name):
        raise Exception("File {} does not exist.".format(file_name))

    with open(file_name, 'r', encoding='utf8') as fp:
        return fp.read()


def file_readlines(file_name):
    if not os.path.isfile(file_name):
        raise Exception("File {} does not exist.".format(file_name))

    with open(file_name, 'r', encoding='utf8') as fp:
        return [line.rstrip() for line in fp]


def file_writelines(file_name, lines):
    with open(file_name, 'w', encoding='utf8') as fp:
        fp.write("\n".join(lines) + "\n")


#
# CSV utils
#

STDIN_NAME = '-'
_stdin_cache = None


def _get_stdin_stream():
    global _stdin_cache
    if _stdin_cache is None:
        sys.stdin.reconfigure(encoding='utf-8')
        _stdin_cache = sys.stdin.read()
    return io.StringIO(_stdin_cache)


def _read_csv(fp, index_key=None, only_column=None):
    res = {} if index_key is not None else []
    reader = csv.DictReader(fp)
    for line in reader:
        value = line
        if only_column is not None:
            value = line.get(only_column)

        if index_key is not None:
            res[line[index_key]] = value
        else:
            res.append(value)

    return res


def load_csv(csv_file, index_key=None, only_column=None):
    '''
    Load CSV file as a list of dictionaries.
    If index key is given, a dictionary is returned where keys are extracted from a column with this name.
    '''
    if csv_file == STDIN_NAME:
        return _read_csv(_get_stdin_stream(), index_key, only_column)

    if not os.path.isfile(csv_file):
        raise Exception("CSV file {} does not exist.".format(csv_file))

    with open(csv_file, 'r', encoding='utf8') as fp:
        return _read_csv(fp, index_key, only_column)


def load_csv_fields(csv_file):
    '''
    Load CSV file field names from its header.
    '''
    if csv_file == STDIN_NAME:
        reader = csv.DictReader(_get_stdin_stream())
        return reader.fieldnames

    if not os.path.isfile(csv_file):
        raise Exception("CSV file {} does not exist.".format(csv_file))

    with open(csv_file, 'r', encoding='utf8') as fp:
        reader = csv.DictReader(fp)
        return reader.fieldnames


def _dump_csv(fp, data, fieldnames=None):
    if type(data) is dict:
        data = data.values()
    if len(data) == 0:
        return

    if fieldnames is None:
        fieldnames = data[0].keys()

    writer = csv.DictWriter(fp, fieldnames)
    writer.writeheader()
    writer.writerows(data)


def print_csv(data, fieldnames=None):
    '''
    Dump CSV content to stdout.
    '''
    sys.stdout.reconfigure(encoding='utf-8')
    _dump_csv(sys.stdout, data, fieldnames)


def save_csv(csv_file, data, fieldnames=None):
    '''
    Save data as CSV file. Data should be list/dict of dicts, where each dict should have fieldnames keys.
    '''
    with open(csv_file, 'w', encoding='utf8', newline='') as fp:
        _dump_csv(fp, data, fieldnames)


#
# ReCodEx CLI
#

# ID of the system account used to submit GPT solutions
SYS_USER_ID = 'ad3d451f-41ef-4c70-a234-094d743511f3'


def _recodex_call(args, **kwargs):
    '''
    Invoke recodex CLI process with given set of arguments.
    On success, stdout is returned as string. On error, None is returned and the message is printed out.
    '''
    res = subprocess.run(['recodex'] + args, capture_output=True, **kwargs)
    if res.returncode == 0:
        return res.stdout
    else:
        print(res.stderr.decode('utf8'), file=sys.stderr)
        raise Exception("Error calling recodex CLI with args: {}".format(" ".join(args)))


def _recodex_get_json(args, **kwargs):
    res = _recodex_call(args, **kwargs)
    return json.loads(res)


def recodex_get_ref_solutions(exercise_id):
    return _recodex_get_json(['exercises', 'get-ref-solutions', '--json', exercise_id])


def recodex_get_ref_solution(solution_id):
    return _recodex_get_json(['exercises', 'get-ref-solution', '--json', solution_id])


def recodex_resumit_ref_solution(solution_id):
    _recodex_call(['exercises', 'resubmit-ref-solution', solution_id])

