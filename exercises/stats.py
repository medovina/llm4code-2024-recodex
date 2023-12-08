import mylib
import sys


def courses(file):
    data = mylib.load_csv(file)
    res = {}
    for e in data:
        year = e["course_year"]
        course = e["course"]
        res[year] = res.get(year, {})
        res[year][course] = res[year].get(course, [0,0,0,0,0])
        res[year][course][0] += 1
        if e["refs_min_locs"] != '':
            locs = float(e["refs_min_locs"])
            res[year][course][1] += locs
            res[year][course][2] += 1
        if e["avg_best_score"] != '':
            score = float(e["avg_best_score"])
            res[year][course][3] += score
            res[year][course][4] += 1

    data = []
    years = list(res.keys())
    years.sort()
    for y in years:
        courses = list(res[y].keys())
        courses.sort()
        for c in courses:
            alocs = res[y][c][1] / float(res[y][c][2])
            ascore = res[y][c][3] / float(res[y][c][4])
            data.append({ "course": c, "year": y, "exercises": res[y][c][0], "avg_locs": alocs, "avg_best_score": ascore })

    mylib.print_csv(data)


def years(file):
    data = mylib.load_csv(file)
    res = {}
    for e in data:
        year = e["course_year"]
        res[year] = res.get(year, 0)
        res[year] += 1

    data = []
    years = list(res.keys())
    years.sort()
    for y in years:
        data.append({ "year": y, "exercises": res[y] })
    
    mylib.print_csv(data)


def runtimes(file):
    data = mylib.load_csv(file)
    rtes = {}
    for e in data:
        rte = e["runtime"]
        rtes[rte] = rtes.get(rte, 0)
        rtes[rte] += 1

    data = []
    rs = list(rtes.keys())
    rs.sort()
    for r in rs:
        data.append({ "runtime": r, "exercises": rtes[r] })

    mylib.print_csv(data)


def runtimes_years(file):
    data = mylib.load_csv(file)
    years = {}
    for e in data:
        year = e["course_year"]
        rte = e["runtime"]
        years[year] = years.get(year, {})
        years[year][rte] = years[year].get(rte, 0)
        years[year][rte] += 1

    data = []
    ys = list(years.keys())
    ys.sort()
    for y in ys:
        rs = list(years[y].keys())
        rs.sort()
        for r in rs:
            data.append({ "year": y, "runtime": r, "exercises": years[y][r] })

    mylib.print_csv(data)


if __name__ == "__main__":
    sys.argv.pop(0)
    command = sys.argv.pop(0)
    fnc = globals().get(command)
    if fnc is not None and callable(fnc):
        fnc(*sys.argv)
    else:
        print("Unknown command {}".format(command))
