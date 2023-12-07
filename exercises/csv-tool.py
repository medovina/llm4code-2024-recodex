import mylib
import sys


def merge(key, *files):
    if len(files) == 0:
        return

    files = list(files)
    file = files.pop(0)
    fieldnames = mylib.load_csv_fields(file)
    data = mylib.load_csv(file, key)
    for file in files:
        add_fieldnames = mylib.load_csv_fields(file)
        if fieldnames != add_fieldnames:
            print("Incompatible CSV columns in file {}.".format(file))
            print(fieldnames)
            print(add_fieldnames)
            return

        add_data = mylib.load_csv(file, key)
        for k in add_data:
            if k not in data:
                data[k] = add_data[k]

    mylib.print_csv(data, fieldnames)


def join(key, *files):
    if len(files) == 0:
        return

    files = list(files)
    src_file = files.pop(0)
    data = mylib.load_csv(src_file, key)
    first = next(iter(data.values()))
    for file in files:
        add_fieldnames = list(filter(lambda f: f not in first,
                                     mylib.load_csv_fields(file)))
        if len(add_fieldnames) > 0:
            # make sure all rows have the new columns
            for exercise in data.values():
                for f in add_fieldnames:
                    exercise[f] = ''

            # add the columns
            add_data = mylib.load_csv(file)
            for add in add_data:
                id = add.get(key)
                if id in data:
                    for f in add_fieldnames:
                        data[id][f] = add[f]

    mylib.save_csv(src_file, data, first.keys())
    #mylib.print_csv(data, first.keys())


def cut(file, *cols):
    fieldnames = mylib.load_csv_fields(file)
    fieldnames = list(filter(lambda f: f in cols, fieldnames))
    if len(fieldnames) == 0:
        return

    data = mylib.load_csv(file)
    data = list(map(lambda d: {k: d[k] for k in fieldnames}, data))
    mylib.print_csv(data, fieldnames)


def diff(file1, file2, key_col, *cols):
    data1 = mylib.load_csv(file1, key_col)
    data2 = mylib.load_csv(file2, key_col)
    mutual_keys = []
    for k in data1:
        if k not in data2:
            print("Record {} missing in {}".format(k, file2))
        else:
            mutual_keys.append(k)

    for k in data2:
        if k not in data1:
            print("Record {} missing in {}".format(k, file1))
        else:
            mutual_keys.append(k)

    if len(cols) > 0:
        for k in mutual_keys:
            for c in cols:
                if data1[k].get(c, True) != data2[k].get(c, False):
                    print("Record {} differs on column {} ({} != {})".format(k, c, data1[k].get(c, "*MISSING*"), data2[k].get(c, "*MISSING*")))


def _filter(file, op_lambda):
    data = mylib.load_csv(file)
    data = list(filter(op_lambda, data))
    mylib.print_csv(data)


def filter_eq(col, value, file='-'):
    _filter(file, lambda e: e[col] == value)


def filter_neq(col, value, file='-'):
    _filter(file, lambda e: e[col] != value)


def filter_fle(col, value, file='-'):
    _filter(file, lambda e: float(e[col]) <= float(value))


def filter_flt(col, value, file='-'):
    _filter(file, lambda e: float(e[col]) < float(value))


def filter_fge(col, value, file='-'):
    _filter(file, lambda e: float(e[col]) >= float(value))


def filter_fgt(col, value, file='-'):
    _filter(file, lambda e: float(e[col]) > float(value))


def sort(col, file='-'):
    data = mylib.load_csv(file)
    data.sort(key=lambda e: e[col])
    mylib.print_csv(data)


if __name__ == "__main__":
    sys.argv.pop(0)
    command = sys.argv.pop(0)
    fnc = globals().get(command)
    if fnc is not None and callable(fnc):
        fnc(*sys.argv)
    else:
        print("Unknown command {}".format(command))
