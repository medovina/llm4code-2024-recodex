import sys
import os
import csv
import shutil
import mylib


def update_manifest(manifest_file, remove_ids):
    fieldnames = mylib.load_csv_fields(manifest_file)
    data = mylib.load_csv(manifest_file)
    data = list(filter(lambda e: e['id'] not in remove_ids, data))
    mylib.save_csv(manifest_file, data, fieldnames)


def run(dir, list_file, manifest_file=None):
    if dir is None or not os.path.isdir(dir):
        print("Invalid directory given {}.".format(dir))
        exit(1)

    if manifest_file is None:
        manifest_file = dir + "/manifest.csv"
    
    ids = mylib.file_readlines(list_file)
    ids_index = {}
    for id in ids:
        ids_index[id] = True
        file = "{}/{}.md".format(dir, id)
        if not os.path.isfile(file):
            print("File {} not found.".format(file))
            continue

        print("Deleting file {} ...".format(file))
        os.unlink(file)
        
        attachments = dir + "/" + id
        if os.path.isdir(attachments):
            print("Deleting dir {} recursively ...".format(attachments))
            shutil.rmtree(attachments)

    print("Updating manifest...")
    update_manifest(manifest_file, ids_index)


if __name__ == "__main__":
    args = sys.argv[1:]
    print(args)
    run(*args)
