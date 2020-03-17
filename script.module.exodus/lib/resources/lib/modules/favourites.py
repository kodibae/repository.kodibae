# -*- coding: utf-8 -*-

'''
    Specto Add-on
    Copyright (C) 2015 lambda

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
'''

try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

import json,os,xbmc,xbmcaddon

from resources.lib.modules import control

addonInfo = xbmcaddon.Addon().getAddonInfo
dataPath = xbmc.translatePath(addonInfo('profile')).decode('utf-8')
favouritesFile = os.path.join(dataPath, 'favourites.db')
progressFile = os.path.join(dataPath, 'progress.db')
def getFavourites(content):
    try:
        dbcon = database.connect(favouritesFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM %s" % content)
        items = dbcur.fetchall()
        items = [(i[0].encode('utf-8'), eval(i[1].encode('utf-8'))) for i in items]
    except:
        items = []

    return items
	
	
def getProgress(content):
    try:
        dbcon = database.connect(progressFile)
        dbcur = dbcon.cursor()
        dbcur.execute("SELECT * FROM %s" % content)
        items = dbcur.fetchall()
        items = [(i[0].encode('utf-8'), eval(i[1].encode('utf-8'))) for i in items]
    except:
        items = []

    return items


def addFavourite(meta, content):
    try:
        item = dict()
        meta = json.loads(meta)
        # print "META DUMP FAVOURITES %s" % meta
        try: id = meta['imdb']
        except: id = meta['tvdb']
        
        if 'title' in meta: title = item['title'] = meta['title']
        if 'tvshowtitle' in meta: title = item['title'] = meta['tvshowtitle']
        if 'year' in meta: item['year'] = meta['year']
        if 'poster' in meta: item['poster'] = meta['poster']
        if 'fanart' in meta: item['fanart'] = meta['fanart']
        if 'imdb' in meta: item['imdb'] = meta['imdb']
        if 'tmdb' in meta: item['tmdb'] = meta['tmdb']
        if 'tvdb' in meta: item['tvdb'] = meta['tvdb']
        if 'tvrage' in meta: item['tvrage'] = meta['tvrage']

        control.makeFile(dataPath)
        dbcon = database.connect(favouritesFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s (""id TEXT, ""items TEXT, ""UNIQUE(id)"");" % content)
        dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, id))
        dbcur.execute("INSERT INTO %s Values (?, ?)" % content, (id, repr(item)))
        dbcon.commit()

        control.refresh()
        control.infoDialog('Added to Watchlist', heading=title, icon=item['poster'])
    except:
        return

def addEpisodes(meta, content):
    try:
        item = dict()
        meta = json.loads(meta)
        content = "episode"
        try: id = meta['imdb']
        except: id = meta['tvdb']
        
        if 'title' in meta: title = item['title'] = meta['title']
        if 'tvshowtitle' in meta: title = item['tvshowtitle'] = meta['tvshowtitle']
        if 'year' in meta: item['year'] = meta['year']
        if 'poster' in meta: item['poster'] = meta['poster']
        if 'fanart' in meta: item['fanart'] = meta['fanart']
        if 'imdb' in meta: item['imdb'] = meta['imdb']
        if 'tmdb' in meta: item['tmdb'] = meta['tmdb']
        if 'tvdb' in meta: item['tvdb'] = meta['tvdb']
        if 'tvrage' in meta: item['tvrage'] = meta['tvrage']
        if 'episode' in meta: item['episode'] = meta['episode']
        if 'season' in meta: item['season'] = meta['season']
        if 'premiered' in meta: item['premiered'] = meta['premiered']
        if 'original_year' in meta: item['original_year'] = meta['original_year']

        control.makeFile(dataPath)
        dbcon = database.connect(favouritesFile)
        dbcur = dbcon.cursor()
        dbcur.execute("CREATE TABLE IF NOT EXISTS %s (""id TEXT, ""items TEXT, ""UNIQUE(id)"");" % content)
        dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, id))
        dbcur.execute("INSERT INTO %s Values (?, ?)" % content, (id, repr(item)))
        dbcon.commit()

        control.refresh()
        control.infoDialog('Added to Watchlist', heading=title)
    except:
        return
		
		
def deleteFavourite(meta, content):
    try:
        meta = json.loads(meta)
        if 'title' in meta: title = meta['title']
        if 'tvshowtitle' in meta: title = meta['tvshowtitle']

        try:
            dbcon = database.connect(favouritesFile)
            dbcur = dbcon.cursor()
            try: dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, meta['imdb']))
            except: pass
            try: dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, meta['tvdb']))
            except: pass
            try: dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, meta['tmdb']))
            except: pass
            dbcon.commit()
        except:
            pass

        control.refresh()
        control.infoDialog('Removed From Watchlist', heading=title)
    except:
        return


def deleteProgress(meta, content):
    try:
        meta = json.loads(meta)
        try:
            dbcon = database.connect(progressFile)
            dbcur = dbcon.cursor()
            try: dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, meta['imdb']))
            except: pass
            try: dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, meta['tvdb']))
            except: pass
            try: dbcur.execute("DELETE FROM %s WHERE id = '%s'" % (content, meta['tmdb']))
            except: pass
            dbcon.commit()
        except:
            pass

        control.refresh()

    except:
        return

