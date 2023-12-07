import re

from util import *

languages = {
    'arduino-gcc' : ('Arduino (a variant of C++)', 'arduino', 'ino'),
    'c-gcc-linux' : ('C', 'c', 'c'),
    'cs-dotnet-core' : ('C#', 'csharp', 'cs'),
    'cxx-gcc-linux' : ('C++', 'cpp', 'cpp'),
    'haskell' : ('Haskell', 'haskell', 'hs'),
    'java' : ('Java', 'java', 'java'),
    'node-linux' : ('Node.js', 'node', 'js'),
    'php-linux' : ('PHP', 'php', 'php'),
    'prolog' : ('Prolog', 'prolog', 'pl'),
    'python3' : ('Python', 'python', 'py')
}

def language(r):
    return languages[r][0].split()[0]

def extract_sources(program_text):
    lines = program_text.split('\n')
    program = []

    filename = None
    text = ''

    def finish():
        nonlocal filename
        if filename != None:
            name_text = (strip_accents(path.basename(filename)), text)
            program.append(name_text)
            filename = None

    for line in lines:
        if re.fullmatch('=+', line):
            finish()
        elif m := re.fullmatch(r' *=+ ?([^ ]+) ?=+|[fF]ilename: ?(.*)', line):
            finish()
            filename = m[1] or m[2]
            text = ''
        else:
            if filename != None:
                text += line + '\n'

    finish()
    return program
