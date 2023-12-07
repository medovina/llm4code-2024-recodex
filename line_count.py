c_comments = ('//', '/*', '*/')

delim = {
    'arduino-gcc' : c_comments,
    'c-gcc-linux' : c_comments,
    'cs-dotnet-core' : c_comments,
    'cxx-gcc-linux' : c_comments,
    'haskell' : ('--', '{-', '-}'),
    'java' : c_comments,
    'node-linux' : c_comments,
    'php-linux' : ('//', '/*', '*/'),
    'prolog' : ('%', '/*', '*/'),
    'python3' : ('#', None, None)
}

def line_count(text, runtime, count_multi):
    single, multi_start, multi_end = delim[runtime]
    
    in_multi = False

    count = 0
    for line in text.split('\n'):
        line = line.strip()
        if in_multi:
            if line.endswith(multi_end):
                in_multi = False
        else:
            if count_multi and multi_start and line.startswith(multi_start):
                if not multi_end in line:
                    in_multi = True
            elif line != '' and not line.startswith(single):
                count += 1

    if in_multi:
        print('warning: multi-line comment was not terminated')
    return count
