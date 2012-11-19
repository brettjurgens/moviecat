from __future__ import with_statement
from contextlib import closing
import sys
import os

# quit if python version too low
if sys.version_info < (2, 5):
    print "Sorry, Python 2.5+ Required"
    sys.exit()

# valid video formats/containers, and random other ones because wikipedia is a liar
validFormats = ['3gp', '3g2', 'asf', 'wma', 'wmv', 'avi', 'divx', 'evo', 'f4v', 'flv', 'iso', 'mkv', 'mk3d', 'mka', 'mks', 'mcf', 
                'mp4', 'mpg', 'mpeg', 'ps', 'ts', 'm2ts', 'mxf', 'ogg', 'mov', 'qt', 'rmvb', 'vob', 'webm']

# path, make dynamic later
path = "/Volumes/media/Movies/BDs"

# processQueue (queue used for adding movies)
from collections import deque
processQueue = deque()

# web serve
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
app = Flask(__name__)

# database config
DATABASE = os.path.dirname(__file__) + 'moviecat.db'
DEBUG = True
SECRET_KEY = '123omgsecret321'
USERNAME = 'admin'
PASSWORD = 'default'

# movie
from tmdb3 import Movie, set_key
set_key('a158113d4e983474500180058409852c')

def recurseIt(path):
    list = {}
    if os.path.isfile(path):
        if os.path.splitext(path)[1][1:].lower() in validFormats:
            list[os.path.basename(path)] = os.path.dirname(path)
        else:
            return {}
    else:
        if os.path.exists(path + "/BDMV"):
            list[os.path.basename(path)] = os.path.dirname(path)
        else:
            for file in os.listdir(path):
                if file[0] != ".":
                    list = dict(list.items() + recurseIt(path + '/' + file).items())
    return list


def addToDB(movieArr):
    g.db.execute('insert into movies (tmdbid, title, year, tagline, overview, runtime, rating, homepage, trailer, location, filename) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', movieArr)
    g.db.commit()

def downloadImages(path, movie):
    import requests

    count = 0

    if os.path.isfile(path):
        location = os.path.dirname(path)
    else:
        location = path

    for backdrop in movie.backdrops:
        img = requests.get(backdrop.geturl())
        if count is 0:
            stringy = ""
        else:
            stringy = str(count)
        with open(location + "/backdrop" + stringy + ".jpg", "wb") as image:
            image.write(img.content)
        print "Downloaded backdrop" + stringy + " to " + location
        count += 1
    
    img = requests.get(movie.poster.geturl())
    with open(location + "/folder.jpg", "wb") as image:
        image.write(img.content)
    print "Downloaded folder image to " + location
    # count = 0
    # for poster in movie.posters:
    #   img = requests.get(poster.geturl())
    #   if count is 0:
    #     stringy = ""
    #   else:
    #     stringy = str(count)
    #   with open(location + "/poster" + stringy + ".jpg", "wb") as image:
    #     image.write(img.content)
    #   print "Downloaded poster" + stringy + " to " + location
    #   count += 1



def tmdbFindEm(list):
    from tmdb3 import searchMovie

    count = 0

    notfound = []

    for movie,location in list.iteritems():

        filename = movie
        if os.path.isfile(movie):
            movie = os.path.splitext(movie)[0]

        if len(location.replace(path, '').replace('/', '')) > 0:
            movie = location.replace(path,'').replace('/','')

        res = searchMovie(movie)
        if len(res) is 0:
            movie = ''.join([c for c in movie if c not in '*-()/\\'])
            res = searchMovie(movie)
        if len(res) is not 0:
            print res[0]
            mov = res[0]
            if len(mov.youtube_trailers) is not 0:
                trailer = mov.youtube_trailers[0].geturl()
            else:
                trailer = None
            movieArr = [mov.id, mov.title, mov.releasedate.year, mov.tagline, mov.overview, mov.runtime, mov.userrating, mov.homepage, trailer, location, filename]
            addToDB(movieArr)
            count += 1
        else:
            notfound.append(movie)
    print "List size: " + str(len(list))
    print "Found size: " + str(count)
    print "Not found: "
    print notfound

def tmdbFindOne(list):
    from tmdb3 import searchMovie
    
    movie = list.keys()[0]
    location = list.values()[0]

    filename = movie
    if os.path.isfile(movie):
        movie = os.path.splitext(movie)[0]

    if len(location.replace(path, '').replace('/', '')) > 0:
        movie = location.replace(path,'').replace('/','')

    res = searchMovie(movie)
    if len(res) is 0:
        movie = ''.join([c for c in movie if c not in '*-()/\\'])
        res = searchMovie(movie)
    if len(res) is not 0:
        return res
    else:
        return None

def acceptTmdbResult(tmdbid, path):
    location = os.path.basename(path)
    filename = os.path.dirname(path)
    mov = Movie(tmdbid)
    if len(mov.youtube_trailers) is not 0:
        trailer = mov.youtube_trailers[0].geturl()
    else:
        trailer = None
    movieArr = [mov.id, mov.title, mov.releasedate.year, mov.tagline, mov.overview, mov.runtime, mov.userrating, mov.homepage, trailer, location, filename]
    addToDB(movieArr)

def searchDatShiz():
    
    if os.path.exists(path):
        print "path valid"
    else:
        print "path invalid"
        sys.exit()

    list = {}
    list = recurseIt(path)

    # why not sort it?
    import collections
    list = collections.OrderedDict(sorted(list.items()))

    tmdbFindEm(list)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
        g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
        g.db.close()


@app.route('/')
def show_entries():
    cur = g.db.execute('select title, id from movies order by upper(title) asc')
    list = [dict(title=row[0], id=row[1]) for row in cur.fetchall()]
    return render_template('show_entries.html', movies=list)

@app.route('/setup')
def setup():
    return render_template('setup_directory.html')

@app.route('/add_dir', methods=['POST'])
def add_dir():
    # return str(request.form['directory'])
    dir = request.form['directory']
    if dir is None or len(dir) <= 0:
        return "directory null"
    g.db.execute('insert into directories (location) values (?)', [dir])
    g.db.commit()
    return "added directory"

@app.route('/search_dir')
def search_dir():
    cur = g.db.execute('select location from directories order by id desc limit 1')
    dir = cur.fetchone()
    list = recurseIt(str(dir[0]))
    import collections
    list = collections.OrderedDict(sorted(list.items()))
    return render_template('search_directory.html', list=list)

@app.route('/add_movies', methods=["POST"])
def add_movies_to_queue():
    movies = request.form
    for movie in movies:
        processQueue.append(movie)
    return str(movies)

@app.route('/process_movie_queue')
def process_movie_queue():
    if len(processQueue) == 0:
        return "nothing in queue..."
    else:
        list = {}
        path = processQueue[0]
        list[os.path.basename(path)] = os.path.dirname(path)
        movies = tmdbFindOne(list)
        posters = {}
        # empty the list, so we can reuse it
        list.clear()
        for movie in movies:
            list[movie.id] = movie.title
            if len(movie.posters) > 0:
                posters[movie.id] = movie.poster.geturl()
        return render_template('search_movie.html', path = path, movies=list, posters=posters)

@app.route('/acceptMovie', methods=["POST"])
def accept_movie():
    moviename = request.form["addedname"]
    tmdbid = request.form["radio"]
    path = request.form["path"]
    accepted = processQueue.popleft()
    if len(processQueue) > 0:
        acceptTmdbResult(tmdbid, path)
        flash('Added ' + moviename)
        return redirect(url_for('process_movie_queue'))

@app.route('/movie/<id>')
def show_movie(id):
    cur = g.db.execute('select * from movies where id=? limit 1', [id])
    movie = cur.fetchone()
    return render_template('show_movie.html', movie=movie)

@app.route('/updateDB')
def update():
    searchDatShiz()
    return "updated..."

@app.route('/downloadmeta/<id>')
def download_meta(id):
    cur = g.db.execute('select tmdbid, location, filename from movies where id=? limit 1', [id])
    record = cur.fetchone()
    movie = Movie(record[0])
    downloadImages(record[1] + '/' + record[2], movie)
    return "downloaded metadata..."

app.config.from_object(__name__)
if __name__ == '__main__':
    app.run()