import mylib
import sys

def get_course(e):
    if e["group_name_1"] == "Algoritmizace":
        return "Introduction to Algorithms"
    if e["group_name_1"] == "Programming I and II":
        if e["runtime"] == "python3":
            return "Programming 1"
        elif e["runtime"] == "cs-dotnet-core":
            return "Programming 2"
        else:
            raise Exception("Unknown course")
    return e["group_name_1"]

def fix(file):
    data = mylib.load_csv(file)
    courses = mylib.load_csv("./courses.csv", "course")
    for e in data:
        if e["course"] == "":
            e["course"] = get_course(e)
        e["course_year"] = courses.get(e["course"])["year"]
    
    mylib.print_csv(data)


if __name__ == "__main__":
    sys.argv.pop(0)
    command = sys.argv.pop(0)
    fnc = globals().get(command)
    if fnc is not None and callable(fnc):
        fnc(*sys.argv)
    else:
        print("Unknown command {}".format(command))
