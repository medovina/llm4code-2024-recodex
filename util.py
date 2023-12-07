import os
from os import path
import shutil
import subprocess
from subprocess import PIPE, STDOUT
import unicodedata

def indent_by(n, s):
    return '\n'.join(' ' * n + line for line in s.split('\n'))

def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                        if unicodedata.category(c) != 'Mn')

def new_dir(dir):
    if path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)

def run(cmd):
    print(cmd)
    return subprocess.run(cmd, stdout = PIPE, shell = True, check = True, text = True).stdout

def run_with_exit_code(cmd):
    print(cmd)
    c = subprocess.run(cmd, stdout = PIPE, stderr = STDOUT, shell = True, text = True)
    return (c.returncode, c.stdout)

def run_with_stderr(cmd):
    print(cmd)
    c = subprocess.run(cmd, stdout = PIPE, stderr = PIPE, shell = True, text = True)
    return (c.returncode, c.stdout, c.stderr)

def enc(s):
    return f'"{s}"' if ',' in s else s

def fix(text):
    if text != '' and text[-1] != '\n':
        text += '\n'
    return text

def read_all(filename):
    with open(filename) as f:
        return fix(f.read())

def write_to(filename, text):
    with open(filename, 'w') as f:
        f.write(text + '\n')
