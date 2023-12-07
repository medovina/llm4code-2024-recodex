import sys
import os
import csv
import shutil


def load_manifest(dir):
    manifest = dir + "/manifest.csv"
    if not os.path.isfile(manifest):
        raise Exception("Manifest file {} does not exist.".format(manifest))

    res = {}
    with open(manifest, 'r', encoding='utf8') as fp:
        reader = csv.DictReader(fp)
        res[''] = reader.fieldnames
        for line in reader:
            res[line["id"]] = line

    return res


def save_manifest(dir, manifest, fieldnames):
    with open(dir + '/manifest.csv', 'w', encoding='utf8', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames)
        writer.writeheader()
        writer.writerows(manifest.values())


def run(dest_dir, src_dir):
    if dest_dir is None or not os.path.isdir(dest_dir) or not os.path.isfile(dest_dir + '/manifest.csv'):
        print("Invalid dest dir {}.".format(dest_dir))
        exit(1)

    if src_dir is None or not os.path.isdir(src_dir) or not os.path.isfile(src_dir + '/manifest.csv'):
        print("Invalid src dir {}.".format(src_dir))
        exit(1)

    print("Loading src manifest...")
    src_manifest = load_manifest(src_dir)

    print("Loading dest manifest...")
    dest_manifest = load_manifest(dest_dir)

    src_fields = src_manifest.pop('')
    dest_fields = dest_manifest.pop('')
    if src_fields != dest_fields:
        print("Incompatible manifest files.")
        print(src_fields)
        print(dest_fields)
        exit(1)

    for id in src_manifest:
        if dest_manifest.get(id) is not None:
            continue
        dest_manifest[id] = src_manifest[id]
        text_file = src_dir + "/" + id + ".md"
        if os.path.isfile(text_file):
            print("Copying {}.md file...".format(id))
            shutil.copy(text_file, dest_dir)
        
        attach_dir = src_dir + "/" + id
        if os.path.isdir(attach_dir):
            print("Copying {} attachments dir...".format(id))
            shutil.copytree(attach_dir, dest_dir + '/' + id)

        save_manifest(dest_dir, dest_manifest, dest_fields)


if __name__ == "__main__":
    run(sys.argv[1] or None, sys.argv[2] or None)
