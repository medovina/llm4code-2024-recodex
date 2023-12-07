import sys
import os
import glob
import unicodedata
import re
import csv

WHITESPACE_REX = re.compile(r"\s+")


def normalize(str):
    str = unicodedata.normalize('NFKD', str).encode('ascii', 'ignore').decode('utf-8')
    return WHITESPACE_REX.sub(" ", str).strip().lower()


def load_manifest(dir):
    manifest = dir + "/manifest.csv"
    if not os.path.isfile(manifest):
        raise Exception("Manifest file {} does not exist.".format(manifest))

    res = {}
    with open(manifest, 'r', encoding='utf8') as fp:
        reader = csv.DictReader(fp)
        for line in reader:
            res[line["id"]] = line

    return res


def run(dir):
    if dir is None or not os.path.isdir(dir):
        print("Invalid directory given '{}'.".format(dir))
        exit(1)

    manifest = load_manifest(dir)
    data = {}
    for file in glob.glob("{}/*.md".format(dir)):
        key = os.path.splitext(os.path.basename(file))[0]
        with open(file, "r", encoding='utf8') as fp:
            content = fp.read()
        data[key] = normalize(content)

    counter = 0
    while len(data) > 0:
        key = next(iter(data))
        content = data.pop(key)
        for k in data:
            #if content == data[k]:
            if normalize(manifest[key]["name"]) == normalize(manifest[k]["name"]):
                counter += 1
                if manifest[key]["forked_from"] == k:
                    print("{}".format(key))
                elif manifest[k]["forked_from"] == key:
                    print("{}".format(k))
                else:
                    print("Duplicity detected {} == {}".format(key, k))
                    print("\t{} is forked from {}".format(key, manifest[key]["forked_from"]))
                    print("\t{} is forked from {}".format(k, manifest[k]["forked_from"]))

    print("Total: {}".format(counter))


if __name__ == "__main__":
    run(sys.argv[1] or None)
