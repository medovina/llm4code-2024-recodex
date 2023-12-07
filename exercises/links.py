import mylib
import re
from urlextract import URLExtract


DATA_DIR = 'data'
EXERCISES_CSV = 'exercises.csv'
IGNORE= [
    'wikipedia.org',
    'wikimedia.org',
    'recodex.mff.cuni.cz',
    'nodejs.org',
    'php.net/manual',
    'www.w3.org',
    'developer.mozilla.org',
    'cppreference.com',
    'docs.scipy.org',
    'docs.microsoft.com',
    'jquery.com',
    'numpy.org/doc',
    'pypi.org',
    'www.yout-ube.com',
    'www.youtube.com',
    'youtu.be',
    'yaml.org',
    'www.boost.org',
    'mitpress.mit.edu/books',
    'www.last.fm',
    'www.notorm.com',
    'www.threadingbuildingblocks.org',
    'jeffe.cs.illinois.edu',
    'www.nezarka.net',
    'generator.lorem-ipsum.info',
    'kremer.cpsc.ucalgary.ca',
    'cgi/taz.cgi',
    'cunicz-my.sharepoint.com',
    'minesweeperonline.com',
    'webik.ms.mff.cuni.cz',
    'teaching/nswi170-web',
    'teaching/nprg042-web',
    'github.com/conda/pycosat',
    'www.gurobi.com/documentation',
    'www.muppetlabs.com',
    'github.com/python-constraint',
]

def _is_ignored(url):
    for pattern in IGNORE:
        if re.search(pattern, url) != None:
            return True
    return False


_extractor = None

def _get_extern_urls(str):
    global _extractor
    if _extractor is None:
        _extractor = URLExtract(extract_localhost=False)
        _extractor.add_enclosure('(', ')')
        _extractor.add_enclosure('`', '`')

    return _extractor.find_urls(str, with_schema_only=True)

    
    #res = re.findall('((https?|ftp)://(-\\.)?([^\\s/?\\.#-]+\\.?)+(/[^\\s]*)?)', str, flags=re.IGNORECASE)
    #res = re.findall('((https?://|ftp://|www\\.|[^\\s:=]+@www\\.).*?[a-z_\\/0-9\\-\\#=&])(?=(\\.|,|;|\\?|\\!)?("|\'|«|»|\\[|\\s|\\r|\\n|$))', str, flags=re.IGNORECASE)
    #urls = map(lambda r: r[0].rstrip(')]>}`"\'.,:'), res)
    #return list(filter(_is_extern, urls))


def print_links():
    exercises = mylib.load_csv(EXERCISES_CSV)
    index = {}
    for exercise in exercises:
        if exercise['exclude'] != '' or exercise['ok'] != '':
            continue
        file = DATA_DIR + '/' + exercise['id'] + '.md'
        text = mylib.file_read(file)
        for url in _get_extern_urls(text):
            index[url] = index.get(url, [])
            index[url].append(exercise['id'])
    
    urls = list(index.keys())
    urls.sort()
    for url in urls:
        if not _is_ignored(url):
            print(url)
            for id in index[url]:
                print("  https://recodex.mff.cuni.cz/app/exercises/{}".format(id))


def get_links_count():
    exercises = mylib.load_csv(EXERCISES_CSV)
    for exercise in exercises:
        file = DATA_DIR + '/' + exercise['id'] + '.md'
        text = mylib.file_read(file)
        urls = _get_extern_urls(text)
        exercise['links_extern'] = len(urls)
    mylib.save_csv(EXERCISES_CSV, exercises, exercises[0].keys())


def fix_ignored_links():
    exercises = mylib.load_csv(EXERCISES_CSV)
    for exercise in exercises:
        if exercise['exclude'] != '' or int(exercise['links_extern']) <= 0 or exercise['ok'] != '':
            continue
        file = DATA_DIR + '/' + exercise['id'] + '.md'
        text = mylib.file_read(file)
        urls = _get_extern_urls(text)
        urls = filter(lambda u: not _is_ignored(u), urls)
        if len(list(urls)) == 0:
            print("{} {}".format(exercise['id'], exercise['links_extern']))
            exercise["ok"] = 1
        mylib.save_csv(EXERCISES_CSV, exercises, exercises[0].keys())
    

if __name__ == "__main__":
    #print_links()
    #get_links_count()
    fix_ignored_links()
    print("Done.")
