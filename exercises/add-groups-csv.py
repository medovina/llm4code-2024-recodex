import sys
import os
import csv
import shutil


def load_groups(file):
    if not os.path.isfile(file):
        raise Exception("CSV file {} does not exist.".format(file))

    res = {}
    with open(file, 'r', encoding='utf8') as fp:
        reader = csv.DictReader(fp, fieldnames=['eid', 'group_id_1', 'group_name_1', 'group_id_2', 'group_name_2'])
        for line in reader:
            res[line["eid"]] = line

    return res


def update_manifest(file, groups):
    if not os.path.isfile(file):
        raise Exception("Manifest file {} does not exist.".format(file))

    add_fields = ['group_id_1', 'group_name_1', 'group_id_2', 'group_name_2']

    data = []
    groups_used = {}
    with open(file, 'r', encoding='utf8') as fp:
        reader = csv.DictReader(fp)
        fieldnames = reader.fieldnames
        ok = True
        for line in reader:
            if groups.get(line["id"]) is None:
                print("Exercise {} not found!".format(line["id"]))
                ok = False
            else:
                eg = groups[line["id"]]
                for field in add_fields:
                    line[field] = eg[field]
                groups_used[eg["group_id_1"]] = eg["group_name_1"]
                groups_used[eg["group_id_2"]] = eg["group_name_2"]
                data.append(line)
        if not ok:
            exit(1)

    fieldnames += add_fields
    with open(file, 'w', encoding='utf8', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames)
        writer.writeheader()
        writer.writerows(data)

    for id in groups_used:
        print("{},{}".format(id, groups_used[id]))


def run(manifest_file, groups_file):
    if manifest_file is None or not os.path.isfile(manifest_file):
        print("Invalid manifest file given {}.".format(manifest_file))
        exit(1)

    if groups_file is None or not os.path.isfile(groups_file):
        print("Invalid groups file given {}.".format(groups_file))
        exit(1)

    print("Loading groups...")
    groups = load_groups(groups_file)

    print("Updating manifest...")
    update_manifest(manifest_file, groups)


if __name__ == "__main__":
    run(sys.argv[1] or None, sys.argv[2] or None)
