# -*- coding: utf-8 -*-

"""
    Exodus Add-on

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

import datetime
import json
import os
import re
import sys
import urllib
import urlparse
import xbmc

from resources.lib.modules import control
from resources.lib.modules import cleantitle

class lib_tools:
    @staticmethod
    def create_folder(folder):
        try:
            folder = xbmc.makeLegalFilename(folder)
            control.makeFile(folder)

            try:
                if not 'ftp://' in folder: raise Exception()
                from ftplib import FTP
                ftparg = re.compile('ftp://(.+?):(.+?)@(.+?):?(\d+)?/(.+/?)').findall(folder)
                ftp = FTP(ftparg[0][2], ftparg[0][0], ftparg[0][1])
                try:
                    ftp.cwd(ftparg[0][4])
                except:
                    ftp.mkd(ftparg[0][4])
                ftp.quit()
            except:
                pass
        except:
            pass

    @staticmethod
    def write_file(path, content):
        try:
            path = xbmc.makeLegalFilename(path)
            if not isinstance(content, basestring):
                content = str(content)

            file = control.openFile(path, 'w')
            file.write(str(content))
            file.close()
        except Exception as e:
            pass

    @staticmethod
    def nfo_url(media_string, ids):
        tvdb_url = 'http://thetvdb.com/?tab=series&id=%s'
        tmdb_url = 'https://www.themoviedb.org/%s/%s'
        imdb_url = 'http://www.imdb.com/title/%s/'

        if 'tvdb' in ids:
            return tvdb_url % (str(ids['tvdb']))
        elif 'tmdb' in ids:
            return tmdb_url % (media_string, str(ids['tmdb']))
        elif 'imdb' in ids:
            return imdb_url % (str(ids['imdb']))
        else:
            return ''

    @staticmethod
    def check_sources(title, year, imdb, tvdb=None, season=None, episode=None, tvshowtitle=None, premiered=None):
        try:
            from resources.lib.modules import sources
            src = sources.sources().getSources(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
            return src and len(src) > 5
        except:
            return False

    @staticmethod
    def legal_filename(filename):
        try:
            filename = filename.strip()
            filename = re.sub(r'(?!%s)[^\w\-_\.]', '.', filename)
            filename = re.sub('\.+', '.', filename)
            filename = re.sub(re.compile('(CON|PRN|AUX|NUL|COM\d|LPT\d)\.', re.I), '\\1_', filename)
            xbmc.makeLegalFilename(filename)
            return filename
        except:
            return filename

    @staticmethod
    def make_path(base_path, title, year='', season=''):
        show_folder = re.sub(r'[^\w\-_\. ]', '_', title)
        show_folder = '%s (%s)' % (show_folder, year) if year else show_folder
        path = os.path.join(base_path, show_folder)
        if season:
            path = os.path.join(path, 'Season %s' % season)
        return path

class libmovies:
    def __init__(self):
        self.library_folder = os.path.join(control.transPath(control.setting('library.movie')), '')

        self.check_setting = control.setting('library.check_movie') or 'false'
        self.library_setting = control.setting('library.update') or 'true'
        self.dupe_setting = control.setting('library.check') or 'true'
        self.silentDialog = False
        self.infoDialog = False


    def add(self, name, title, year, imdb, tmdb, range=False):
        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo')\
                and self.silentDialog is False:
            control.infoDialog(control.lang(32552).encode('utf-8'), time=10000000)
            self.infoDialog = True

        try:
            if not self.dupe_setting == 'true': raise Exception()

            id = [imdb, tmdb] if not tmdb == '0' else [imdb]
            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"filter":{"or": [{"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}, {"field": "year", "operator": "is", "value": "%s"}]}, "properties" : ["imdbnumber", "originaltitle", "year"]}, "id": 1}' % (year, str(int(year)+1), str(int(year)-1)))
            lib = unicode(lib, 'utf-8', errors='ignore')
            lib = json.loads(lib)['result']['movies']
            lib = [i for i in lib if str(i['imdbnumber']) in id or (i['originaltitle'].encode('utf-8') == title and str(i['year']) == year)][0]
        except:
            lib = []

        files_added = 0

        try:
            if not lib == []: raise Exception()

            if self.check_setting == 'true':
                src = lib_tools.check_sources(title, year, imdb, None, None, None, None, None)
                if not src: raise Exception()

            self.strmFile({'name': name, 'title': title, 'year': year, 'imdb': imdb, 'tmdb': tmdb})
            files_added += 1
        except:
            pass

        if range == True: return

        if self.infoDialog == True:
            control.infoDialog(control.lang(32554).encode('utf-8'), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
            control.execute('UpdateLibrary(video)')

    def silent(self, url):
        control.idle()

        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32552).encode('utf-8'), time=10000000)
            self.infoDialog = True
            self.silentDialog = True

        from resources.lib.indexers import movies
        items = movies.movies().get(url, idx=False)
        if items == None: items = []

        for i in items:
            try:
                if xbmc.abortRequested == True: return sys.exit()
                self.add('%s (%s)' % (i['title'], i['year']), i['title'], i['year'], i['imdb'], i['tmdb'], range=True)
            except:
                pass

        if self.infoDialog == True:
            self.silentDialog = False
            control.infoDialog("Trakt Movies Sync Complete", time=1)

    def range(self, url):
        control.idle()

        yes = control.yesnoDialog(control.lang(32555).encode('utf-8'), '', '')
        if not yes: return

        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32552).encode('utf-8'), time=10000000)
            self.infoDialog = True

        from resources.lib.indexers import movies
        items = movies.movies().get(url, idx=False)
        if items == None: items = []

        for i in items:
            try:
                if xbmc.abortRequested == True: return sys.exit()
                self.add('%s (%s)' % (i['title'], i['year']), i['title'], i['year'], i['imdb'], i['tmdb'], range=True)
            except:
                pass

        if self.infoDialog == True:
            control.infoDialog(control.lang(32554).encode('utf-8'), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo'):
            control.execute('UpdateLibrary(video)')


    def strmFile(self, i):
        try:
            name, title, year, imdb, tmdb = i['name'], i['title'], i['year'], i['imdb'], i['tmdb']

            sysname, systitle = urllib.quote_plus(name), urllib.quote_plus(title)

            transtitle = cleantitle.normalize(title.translate(None, '\/:*?"<>|'))

            content = '%s?action=play&name=%s&title=%s&year=%s&imdb=%s&tmdb=%s' % (sys.argv[0], sysname, systitle, year, imdb, tmdb)

            folder = lib_tools.make_path(self.library_folder, transtitle, year)

            lib_tools.create_folder(folder)
            lib_tools.write_file(os.path.join(folder, lib_tools.legal_filename(transtitle) + '.strm'), content)
            lib_tools.write_file(os.path.join(folder, 'movie.nfo'), lib_tools.nfo_url('movie', i))
        except:
            pass


class libtvshows:
    def __init__(self):
        self.library_folder = os.path.join(control.transPath(control.setting('library.tv')),'')

        self.version = control.version()

        self.check_setting = control.setting('library.check_episode') or 'false'
        self.include_unknown = control.setting('library.include_unknown') or 'true'
        self.library_setting = control.setting('library.update') or 'true'
        self.dupe_setting = control.setting('library.check') or 'true'

        self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        if control.setting('library.importdelay') != 'true':
            self.date = self.datetime.strftime('%Y%m%d')
        else:
            self.date = (self.datetime - datetime.timedelta(hours=24)).strftime('%Y%m%d')
        self.silentDialog = False
        self.infoDialog = False
        self.block = False


    def add(self, tvshowtitle, year, imdb, tvdb, range=False):
        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo')\
                and self.silentDialog is False:
            control.infoDialog(control.lang(32552).encode('utf-8'), time=10000000)
            self.infoDialog = True

        from resources.lib.indexers import episodes
        items = episodes.episodes().get(tvshowtitle, year, imdb, tvdb, idx=False)

        try: items = [{'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tvdb': i['tvdb'], 'season': i['season'], 'episode': i['episode'], 'tvshowtitle': i['tvshowtitle'], 'premiered': i['premiered']} for i in items]
        except: items = []

        try:
            if not self.dupe_setting == 'true': raise Exception()
            if items == []: raise Exception()

            id = [items[0]['imdb'], items[0]['tvdb']]

            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties" : ["imdbnumber", "title", "year"]}, "id": 1}')
            lib = unicode(lib, 'utf-8', errors='ignore')
            lib = json.loads(lib)['result']['tvshows']
            lib = [i['title'].encode('utf-8') for i in lib if str(i['imdbnumber']) in id or (i['title'].encode('utf-8') == items[0]['tvshowtitle'] and str(i['year']) == items[0]['year'])][0]

            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "tvshow", "operator": "is", "value": "%s"}]}, "properties": ["season", "episode"]}, "id": 1}' % lib)
            lib = unicode(lib, 'utf-8', errors='ignore')
            lib = json.loads(lib)['result']['episodes']
            lib = ['S%02dE%02d' % (int(i['season']), int(i['episode'])) for i in lib]

            items = [i for i in items if not 'S%02dE%02d' % (int(i['season']), int(i['episode'])) in lib]
        except:
            pass

        files_added = 0

        for i in items:
            try:
                if xbmc.abortRequested == True: return sys.exit()

                if self.check_setting == 'true':
                    if i['episode'] == '1':
                        self.block = True
                        src = lib_tools.check_sources(i['title'], i['year'], i['imdb'], i['tvdb'], i['season'], i['episode'], i['tvshowtitle'], i['premiered'])
                        if src: self.block = False
                    if self.block == True: raise Exception()

                premiered = i.get('premiered', '0')
                if (premiered != '0' and int(re.sub('[^0-9]', '', str(premiered))) > int(self.date)) or (premiered == '0' and not self.include_unknown):
                    continue

                self.strmFile(i)
                files_added += 1
            except:
                pass

        if range == True: return

        if self.infoDialog is True:
            control.infoDialog(control.lang(32554).encode('utf-8'), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
            control.execute('UpdateLibrary(video)')

    def silent(self, url):
        control.idle()

        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32608).encode('utf-8'), time=10000000)
            self.infoDialog = True
            self.silentDialog = True

        from resources.lib.indexers import tvshows
        items = tvshows.tvshows().get(url, idx=False)
        if items == None: items = []

        for i in items:
            try:
                if xbmc.abortRequested == True: return sys.exit()
                self.add(i['title'], i['year'], i['imdb'], i['tvdb'], range=True)
            except:
                pass

        if self.infoDialog is True:
            self.silentDialog = False
            control.infoDialog("Trakt TV Show Sync Complete", time=1)


    def range(self, url):
        control.idle()

        yes = control.yesnoDialog(control.lang(32555).encode('utf-8'), '', '')
        if not yes: return

        if not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32552).encode('utf-8'), time=10000000)
            self.infoDialog = True

        from resources.lib.indexers import tvshows
        items = tvshows.tvshows().get(url, idx=False)
        if items == None: items = []

        for i in items:
            try:
                if xbmc.abortRequested == True: return sys.exit()
                self.add(i['title'], i['year'], i['imdb'], i['tvdb'], range=True)
            except:
                pass

        if self.infoDialog == True:
            control.infoDialog(control.lang(32554).encode('utf-8'), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo'):
            control.execute('UpdateLibrary(video)')


    def strmFile(self, i):
        try:
            title, year, imdb, tvdb, season, episode, tvshowtitle, premiered = i['title'], i['year'], i['imdb'], i['tvdb'], i['season'], i['episode'], i['tvshowtitle'], i['premiered']

            episodetitle = urllib.quote_plus(title)
            systitle, syspremiered = urllib.quote_plus(tvshowtitle), urllib.quote_plus(premiered)

            transtitle = cleantitle.normalize(tvshowtitle.translate(None, '\/:*?"<>|'))

            content = '%s?action=play&title=%s&year=%s&imdb=%s&tvdb=%s&season=%s&episode=%s&tvshowtitle=%s&date=%s' % (sys.argv[0], episodetitle, year, imdb, tvdb, season, episode, systitle, syspremiered)

            folder = lib_tools.make_path(self.library_folder, transtitle, year)
            if not os.path.isfile(os.path.join(folder, 'tvshow.nfo')):
                lib_tools.create_folder(folder)
                lib_tools.write_file(os.path.join(folder, 'tvshow.nfo'), lib_tools.nfo_url('tv', i))

            folder = lib_tools.make_path(self.library_folder, transtitle, year, season)
            lib_tools.create_folder(folder)
            lib_tools.write_file(os.path.join(folder, lib_tools.legal_filename('%s S%02dE%02d' % (transtitle, int(season), int(episode))) + '.strm'), content)
        except:
            pass


class libepisodes:
    def __init__(self):
        self.library_folder = os.path.join(control.transPath(control.setting('library.tv')),'')

        self.library_setting = control.setting('library.update') or 'true'
        self.include_unknown = control.setting('library.include_unknown') or 'true'
        self.property = '%s_service_property' % control.addonInfo('name').lower()

        self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        if control.setting('library.importdelay') != 'true':
            self.date = self.datetime.strftime('%Y%m%d')
        else:
            self.date = (self.datetime - datetime.timedelta(hours=24)).strftime('%Y%m%d')

        self.infoDialog = False


    def update(self, query=None, info='true'):
        if not query == None: control.idle()

        try:

            items = []
            season, episode = [], []
            show = [os.path.join(self.library_folder, i) for i in control.listDir(self.library_folder)[0]]
            for s in show:
                try: season += [os.path.join(s, i) for i in control.listDir(s)[0]]
                except: pass
            for s in season:
                try: episode.append([os.path.join(s, i) for i in control.listDir(s)[1] if i.endswith('.strm')][-1])
                except: pass

            for file in episode:
                try:
                    file = control.openFile(file)
                    read = file.read()
                    read = read.encode('utf-8')
                    file.close()

                    if not read.startswith(sys.argv[0]): raise Exception()

                    params = dict(urlparse.parse_qsl(read.replace('?','')))

                    try: tvshowtitle = params['tvshowtitle']
                    except: tvshowtitle = None
                    try: tvshowtitle = params['show']
                    except: pass
                    if tvshowtitle == None or tvshowtitle == '': raise Exception()

                    year, imdb, tvdb = params['year'], params['imdb'], params['tvdb']

                    imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

                    try: tmdb = params['tmdb']
                    except: tmdb = '0'

                    items.append({'tvshowtitle': tvshowtitle, 'year': year, 'imdb': imdb, 'tmdb': tmdb, 'tvdb': tvdb})
                except:
                    pass

            items = [i for x, i in enumerate(items) if i not in items[x + 1:]]
            if len(items) == 0: raise Exception()
        except:
            return

        try:
            lib = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties" : ["imdbnumber", "title", "year"]}, "id": 1}')
            lib = unicode(lib, 'utf-8', errors='ignore')
            lib = json.loads(lib)['result']['tvshows']
        except:
            return

        if info == 'true' and not control.condVisibility('Window.IsVisible(infodialog)') and not control.condVisibility('Player.HasVideo'):
            control.infoDialog(control.lang(32553).encode('utf-8'), time=10000000)
            self.infoDialog = True

        try:
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.libcacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS tvshows (""id TEXT, ""items TEXT, ""UNIQUE(id)"");")
        except:
            return

        try:
            from resources.lib.indexers import episodes
        except:
            return

        files_added = 0

        # __init__ doesn't get called from services so self.date never gets updated and new episodes are not added to the library
        self.datetime = (datetime.datetime.utcnow() - datetime.timedelta(hours = 5))
        if control.setting('library.importdelay') != 'true':
            self.date = self.datetime.strftime('%Y%m%d')
        else:
            self.date = (self.datetime - datetime.timedelta(hours=24)).strftime('%Y%m%d')
        
        for item in items:
            it = None

            if xbmc.abortRequested == True: return sys.exit()

            try:
                dbcur.execute("SELECT * FROM tvshows WHERE id = '%s'" % item['tvdb'])
                fetch = dbcur.fetchone()
                it = eval(fetch[1].encode('utf-8'))
            except:
                pass

            try:
                if not it == None: raise Exception()

                it = episodes.episodes().get(item['tvshowtitle'], item['year'], item['imdb'], item['tvdb'], idx=False)

                status = it[0]['status'].lower()

                it = [{'title': i['title'], 'year': i['year'], 'imdb': i['imdb'], 'tvdb': i['tvdb'], 'season': i['season'], 'episode': i['episode'], 'tvshowtitle': i['tvshowtitle'], 'premiered': i['premiered']} for i in it]

                if status == 'continuing': raise Exception()
                dbcur.execute("INSERT INTO tvshows Values (?, ?)", (item['tvdb'], repr(it)))
                dbcon.commit()
            except:
                pass

            try:
                id = [item['imdb'], item['tvdb']]
                if not item['tmdb'] == '0': id += [item['tmdb']]

                ep = [x['title'].encode('utf-8') for x in lib if str(x['imdbnumber']) in id or (x['title'].encode('utf-8') == item['tvshowtitle'] and str(x['year']) == item['year'])][0]
                ep = control.jsonrpc('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"filter":{"and": [{"field": "tvshow", "operator": "is", "value": "%s"}]}, "properties": ["season", "episode"]}, "id": 1}' % ep)
                ep = unicode(ep, 'utf-8', errors='ignore')
                ep = json.loads(ep).get('result', {}).get('episodes', {})
                ep = [{'season': int(i['season']), 'episode': int(i['episode'])} for i in ep]
                ep = sorted(ep, key=lambda x: (x['season'], x['episode']))[-1]

                num = [x for x,y in enumerate(it) if str(y['season']) == str(ep['season']) and str(y['episode']) == str(ep['episode'])][-1]
                it = [y for x,y in enumerate(it) if x > num]
                if len(it) == 0: continue
            except:
                continue

            for i in it:
                try:
                    if xbmc.abortRequested == True: return sys.exit()

                    premiered = i.get('premiered', '0')
                    if (premiered != '0' and int(re.sub('[^0-9]', '', str(premiered))) > int(self.date)) or (premiered == '0' and not self.include_unknown):
                        continue

                    libtvshows().strmFile(i)
                    files_added += 1
                except:
                    pass

        if self.infoDialog == True:
            control.infoDialog(control.lang(32554).encode('utf-8'), time=1)

        if self.library_setting == 'true' and not control.condVisibility('Library.IsScanningVideo') and files_added > 0:
            control.execute('UpdateLibrary(video)')


    def service(self):
        try:
            lib_tools.create_folder(os.path.join(control.transPath(control.setting('library.movie')), ''))
            lib_tools.create_folder(os.path.join(control.transPath(control.setting('library.tv')), ''))
        except:
            pass
        
        try:
            control.makeFile(control.dataPath)
            dbcon = database.connect(control.libcacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("CREATE TABLE IF NOT EXISTS service (""setting TEXT, ""value TEXT, ""UNIQUE(setting)"");")
            dbcur.execute("SELECT * FROM service WHERE setting = 'last_run'")
            fetch = dbcur.fetchone()
            if fetch == None:
                serviceProperty = "1970-01-01 23:59:00.000000"
                dbcur.execute("INSERT INTO service Values (?, ?)", ('last_run', serviceProperty))
                dbcon.commit()
            else:
                serviceProperty = str(fetch[1])
            dbcon.close()
        except:
            try: return dbcon.close()
            except: return

        try: control.window.setProperty(self.property, serviceProperty)
        except: return

        while not xbmc.abortRequested:
            try:
                serviceProperty = control.window.getProperty(self.property)

                t1 = datetime.timedelta(hours=6)
                t2 = datetime.datetime.strptime(serviceProperty, '%Y-%m-%d %H:%M:%S.%f')
                t3 = datetime.datetime.now()

                check = abs(t3 - t2) > t1
                if check == False: raise Exception()

                if (control.player.isPlaying() or control.condVisibility('Library.IsScanningVideo')): raise Exception()

                serviceProperty = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

                control.window.setProperty(self.property, serviceProperty)

                try:
                    dbcon = database.connect(control.libcacheFile)
                    dbcur = dbcon.cursor()
                    dbcur.execute("CREATE TABLE IF NOT EXISTS service (""setting TEXT, ""value TEXT, ""UNIQUE(setting)"");")
                    dbcur.execute("DELETE FROM service WHERE setting = 'last_run'")
                    dbcur.execute("INSERT INTO service Values (?, ?)", ('last_run', serviceProperty))
                    dbcon.commit()
                    dbcon.close()
                except:
                    try: dbcon.close()
                    except: pass

                if not control.setting('library.service.update') == 'true': raise Exception()
                info = control.setting('library.service.notification') or 'true'
                self.update(info=info)
            except:
                pass

            control.sleep(10000)

