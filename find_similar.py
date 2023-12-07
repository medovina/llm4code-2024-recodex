from itertools import combinations, islice
import os
import sys

from Levenshtein import distance

from exercises import *
import util

anonlang = {}
eng = {}

n = int(sys.argv[1])
for id, e in islice(id_exercises.items(), n):
    for lang, map in [('al', anonlang), ('en', eng)]:
        p = f'exercises/download-{lang}/{id}.md'
        if os.path.exists(p):
            map[id] = util.read_all(p)

for map in [anonlang, eng]:
    print('anonlang' if map == anonlang else 'english')
    dist = []
    for (id1, text1), (id2, text2) in combinations(map.items(), 2):
        d = distance(text1, text2) / max(len(text1), len(text2))
        dist.append((d, id1, id2))
    dist.sort()
    for d, id1, id2 in dist[:25]:
        e1, e2 = id_exercises[id1], id_exercises[id2]
        print(f'{d:.3f}:')
        print(f'  {e1.name} ({id1})')
        print(f'  {e2.name} ({id2})')
