# -*- coding: utf-8 -*-

'''
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
'''

import datetime
import json
import random
import re
import sys
import time
import urllib
import urlparse
#import lambdascrapers
import exoscrapers

from resources.lib.modules import (cleantitle, client, control, debrid,
                                   log_utils, source_utils, trakt, tvmaze,
                                   workers)

try:
    from sqlite3 import dbapi2 as database
except Exception:
    from pysqlite2 import dbapi2 as database

try:
    import urlresolver
except Exception:
    pass

try:
    import xbmc
except Exception:
    pass


class sources:
    def __init__(self):
        self.getConstants()
        self.sources = []

    def play(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, meta, select):
        try:

            url = None

            items = self.getSources(title, year, imdb, tvdb, season, episode, tvshowtitle, premiered)
            select = control.setting('hosts.mode') if select is None else select
            title = tvshowtitle if not tvshowtitle is None else title

            if control.window.getProperty('PseudoTVRunning') == 'True':
                return control.resolve(int(sys.argv[1]), True, control.item(path=str(self.sourcesDirect(items))))

            if len(items) > 0:

                if select == '1' and 'plugin' in control.infoLabel('Container.PluginName'):
                    control.window.clearProperty(self.itemProperty)
                    control.window.setProperty(self.itemProperty, json.dumps(items))

                    control.window.clearProperty(self.metaProperty)
                    control.window.setProperty(self.metaProperty, meta)

                    control.sleep(200)

                    return control.execute('Container.Update(%s?action=addItem&title=%s)' %
                                           (sys.argv[0],
                                            urllib.quote_plus(title)))

                elif select == '0' or select == '1':
                    url = self.sourcesDialog(items)

                else:
                    url = self.sourcesDirect(items)

            if url is None:
                return self.errorForSources()

            try:
                meta = json.loads(meta)
            except Exception:
                pass

            from resources.lib.modules.player import player
            player().run(title, year, season, episode, imdb, tvdb, url, meta)
        except Exception:
            pass

    def addItem(self, title):
        control.playlist.clear()

        items = control.window.getProperty(self.itemProperty)
        items = json.loads(items)

        if items is None or len(items) == 0:
            control.idle()
            sys.exit()

        meta = control.window.getProperty(self.metaProperty)
        meta = json.loads(meta)

        # (Kodi bug?) [name,role] is incredibly slow on this directory, [name] is barely tolerable, so just nuke it for speed!
        if 'cast' in meta:
            del(meta['cast'])

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        downloads = True if control.setting('downloads') == 'true' and not (control.setting(
            'movie.download.path') == '' or control.setting('tv.download.path') == '') else False

        systitle = sysname = urllib.quote_plus(title)

        if 'tvshowtitle' in meta and 'season' in meta and 'episode' in meta:
            sysname += urllib.quote_plus(' S%02dE%02d' % (int(meta['season']), int(meta['episode'])))
        elif 'year' in meta:
            sysname += urllib.quote_plus(' (%s)' % meta['year'])

        poster = meta['poster3'] if 'poster3' in meta else '0'
        if poster == '0':
            poster = meta['poster'] if 'poster' in meta else '0'

        fanart = meta['fanart2'] if 'fanart2' in meta else '0'
        if fanart == '0':
            fanart = meta['fanart'] if 'fanart' in meta else '0'

        thumb = meta['thumb'] if 'thumb' in meta else '0'
        if thumb == '0':
            thumb = poster
        if thumb == '0':
            thumb = fanart

        banner = meta['banner'] if 'banner' in meta else '0'
        if banner == '0':
            banner = poster

        if poster == '0':
            poster = control.addonPoster()
        if banner == '0':
            banner = control.addonBanner()
        if not control.setting('fanart') == 'true':
            fanart = '0'
        if fanart == '0':
            fanart = control.addonFanart()
        if thumb == '0':
            thumb = control.addonFanart()

        sysimage = urllib.quote_plus(poster.encode('utf-8'))

        downloadMenu = control.lang(32403).encode('utf-8')

        for i in range(len(items)):
            try:
                label = items[i]['label']

                syssource = urllib.quote_plus(json.dumps([items[i]]))

                sysurl = '%s?action=playItem&title=%s&source=%s' % (sysaddon, systitle, syssource)

                cm = []

                if downloads is True:
                    cm.append((downloadMenu, 'RunPlugin(%s?action=download&name=%s&image=%s&source=%s)' %
                               (sysaddon, sysname, sysimage, syssource)))

                item = control.item(label=label)

                item.setArt({'icon': thumb, 'thumb': thumb, 'poster': poster, 'banner': banner})

                item.setProperty('Fanart_Image', fanart)

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                item.addContextMenuItems(cm)
                item.setInfo(type='Video', infoLabels=meta)

                control.addItem(handle=syshandle, url=sysurl, listitem=item, isFolder=False)
            except Exception:
                pass

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=True)

    def playItem(self, title, source):
        try:
            meta = control.window.getProperty(self.metaProperty)
            meta = json.loads(meta)

            year = meta['year'] if 'year' in meta else None
            season = meta['season'] if 'season' in meta else None
            episode = meta['episode'] if 'episode' in meta else None

            imdb = meta['imdb'] if 'imdb' in meta else None
            tvdb = meta['tvdb'] if 'tvdb' in meta else None

            next = []
            prev = []
            total = []

            for i in range(1, 1000):
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total:
                        raise Exception()
                    total.append(u)
                    u = dict(urlparse.parse_qsl(u.replace('?', '')))
                    u = json.loads(u['source'])[0]
                    next.append(u)
                except Exception:
                    break
            for i in range(-1000, 0)[::-1]:
                try:
                    u = control.infoLabel('ListItem(%s).FolderPath' % str(i))
                    if u in total:
                        raise Exception()
                    total.append(u)
                    u = dict(urlparse.parse_qsl(u.replace('?', '')))
                    u = json.loads(u['source'])[0]
                    prev.append(u)
                except Exception:
                    break

            items = json.loads(source)
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog if control.setting(
                'progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    try:
                        if progressDialog.iscanceled():
                            break
                        progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
                    except Exception:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))

                    if items[i]['source'] == block:
                        raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    offset = 60 * 2 if items[i].get('source') in self.hostcapDict else 0

                    m = ''

                    for x in range(3600):
                        try:
                            if xbmc.abortRequested is True:
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30 + offset) and not k:
                            break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30 + offset) and not k:
                            break
                        time.sleep(0.5)

                    for x in range(30):
                        try:
                            if xbmc.abortRequested is True:
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        if m == '':
                            break
                        if w.is_alive() is False:
                            break
                        time.sleep(0.5)

                    if w.is_alive() is True:
                        block = items[i]['source']

                    if self.url is None:
                        raise Exception()

                    try:
                        progressDialog.close()
                    except Exception:
                        pass

                    control.sleep(200)
                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')

                    from resources.lib.modules.player import player
                    player().run(title, year, season, episode, imdb, tvdb, self.url, meta)

                    return self.url
                except Exception:
                    pass

            try:
                progressDialog.close()
            except Exception:
                pass

            self.errorForSources()
        except Exception:
            pass

    def getSources(self, title, year, imdb, tvdb, season, episode, tvshowtitle, premiered, quality='HD', timeout=30):

        progressDialog = control.progressDialog if control.setting(
            'progress.dialog') == '0' else control.progressDialogBG
        progressDialog.create(control.addonInfo('name'), '')
        progressDialog.update(0)

        self.prepareSources()

        sourceDict = self.sourceDict

        progressDialog.update(0, control.lang(32600).encode('utf-8'))

        content = 'movie' if tvshowtitle is None else 'episode'
        if content == 'movie':
            sourceDict = [(i[0], i[1], getattr(i[1], 'movie', None)) for i in sourceDict]
            genres = trakt.getGenre('movie', 'imdb', imdb)
        else:
            sourceDict = [(i[0], i[1], getattr(i[1], 'tvshow', None)) for i in sourceDict]
            genres = trakt.getGenre('show', 'tvdb', tvdb)

        sourceDict = [(i[0], i[1], i[2]) for i in sourceDict if not hasattr(i[1], 'genre_filter')
                      or not i[1].genre_filter or any(x in i[1].genre_filter for x in genres)]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] is None]

        language = self.getLanguage()
        sourceDict = [(i[0], i[1], i[1].language) for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if any(x in i[2] for x in language)]

        try:
            sourceDict = [(i[0], i[1], control.setting('provider.' + i[0])) for i in sourceDict]
        except Exception:
            sourceDict = [(i[0], i[1], 'true') for i in sourceDict]
        sourceDict = [(i[0], i[1]) for i in sourceDict if not i[2] == 'false']

        sourceDict = [(i[0], i[1], i[1].priority) for i in sourceDict]

        random.shuffle(sourceDict)
        sourceDict = sorted(sourceDict, key=lambda i: i[2])

        threads = []

        if content == 'movie':
            title = self.getTitle(title)
            localtitle = self.getLocalTitle(title, imdb, tvdb, content)
            aliases = self.getAliasTitles(imdb, localtitle, content)
            for i in sourceDict:
                threads.append(workers.Thread(self.getMovieSource, title, localtitle, aliases, year, imdb, i[0], i[1]))
        else:
            tvshowtitle = self.getTitle(tvshowtitle)
            localtvshowtitle = self.getLocalTitle(tvshowtitle, imdb, tvdb, content)
            aliases = self.getAliasTitles(imdb, localtvshowtitle, content)
            # Disabled on 11/11/17 due to hang. Should be checked in the future and possible enabled again.
            # season, episode = thexem.get_scene_episode_number(tvdb, season, episode)
            for i in sourceDict:
                threads.append(workers.Thread(self.getEpisodeSource, title, year, imdb, tvdb, season,
                                              episode, tvshowtitle, localtvshowtitle, aliases, premiered, i[0], i[1]))

        s = [i[0] + (i[1],) for i in zip(sourceDict, threads)]
        s = [(i[3].getName(), i[0], i[2]) for i in s]

        mainsourceDict = [i[0] for i in s if i[2] == 0]
        sourcelabelDict = dict([(i[0], i[1].upper()) for i in s])

        [i.start() for i in threads]

        string1 = control.lang(32404).encode('utf-8')
        string2 = control.lang(32405).encode('utf-8')
        string3 = control.lang(32406).encode('utf-8')
        string4 = control.lang(32601).encode('utf-8')
        string5 = control.lang(32602).encode('utf-8')
        string6 = control.lang(32606).encode('utf-8')
        string7 = control.lang(32607).encode('utf-8')

        try:
            timeout = int(control.setting('scrapers.timeout.1'))
        except Exception:
            pass

        quality = control.setting('hosts.quality')
        if quality == '':
            quality = '0'

        line1 = line2 = line3 = ""

        debrid_only = control.setting('debrid.only')

        pre_emp =  control.setting('preemptive.termination')
        pre_emp_limit = control.setting('preemptive.limit')

        source_4k = d_source_4k = 0
        source_1080 = d_source_1080 = 0
        source_720 = d_source_720 = 0
        source_sd = d_source_sd = 0
        total = d_total = 0

        debrid_list = debrid.debrid_resolvers
        debrid_status = debrid.status()

        total_format = '[COLOR %s][B]%s[/B][/COLOR]'
        pdiag_format = ' 4K: %s | 1080p: %s | 720p: %s | SD: %s | %s: %s'.split('|')
        pdiag_bg_format = '4K:%s(%s)|1080p:%s(%s)|720p:%s(%s)|SD:%s(%s)|T:%s(%s)'.split('|')

        for i in range(0, 4 * timeout):
            if str(pre_emp) == 'true':
                if quality in ['0','1']:
                    if (source_1080 + d_source_1080) >= int(pre_emp_limit): break
                elif quality in ['2']:
                    if (source_720 + d_source_720) >= int(pre_emp_limit): break
                elif quality in ['3']:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit): break
                else:
                    if (source_sd + d_source_sd) >= int(pre_emp_limit): break

            try:
                if xbmc.abortRequested == True: return sys.exit()

                try:
                    if progressDialog.iscanceled():
                        break
                except Exception:
                    pass

                if len(self.sources) > 0:
                    if quality in ['0']:
                        source_4k = len([e for e in self.sources if e['quality'] == '4K' and e['debridonly'] is False])
                        source_1080 = len([e for e in self.sources if e['quality'] in [
                                          '1440p', '1080p'] and e['debridonly'] is False])
                        source_720 = len([e for e in self.sources if e['quality'] in [
                                         '720p', 'HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    elif quality in ['1']:
                        source_1080 = len([e for e in self.sources if e['quality'] in [
                                          '1440p', '1080p'] and e['debridonly'] is False])
                        source_720 = len([e for e in self.sources if e['quality'] in [
                                         '720p', 'HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    elif quality in ['2']:
                        source_1080 = len([e for e in self.sources if e['quality']
                                           in ['1080p'] and e['debridonly'] is False])
                        source_720 = len([e for e in self.sources if e['quality'] in [
                                         '720p', 'HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    elif quality in ['3']:
                        source_720 = len([e for e in self.sources if e['quality'] in [
                                         '720p', 'HD'] and e['debridonly'] is False])
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])
                    else:
                        source_sd = len([e for e in self.sources if e['quality'] == 'SD' and e['debridonly'] is False])

                    total = source_4k + source_1080 + source_720 + source_sd

                    if debrid_status:
                        if quality in ['0']:
                            for d in debrid_list:
                                d_source_4k = len([e for e in self.sources if e['quality']
                                                   == '4K' and d.valid_url(str(e['url']), e['source'])])
                                d_source_1080 = len([e for e in self.sources if e['quality'] in [
                                                    '1440p', '1080p'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in [
                                                   '720p', 'HD'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality']
                                                   == 'SD' and d.valid_url(str(e['url']), e['source'])])
                        elif quality in ['1']:
                            for d in debrid_list:
                                d_source_1080 = len([e for e in self.sources if e['quality'] in [
                                                    '1440p', '1080p'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in [
                                                   '720p', 'HD'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality']
                                                   == 'SD' and d.valid_url(str(e['url']), e['source'])])
                        elif quality in ['2']:
                            for d in debrid_list:
                                d_source_1080 = len([e for e in self.sources if e['quality'] in [
                                                    '1080p'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_720 = len([e for e in self.sources if e['quality'] in [
                                                   '720p', 'HD'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality']
                                                   == 'SD' and d.valid_url(str(e['url']), e['source'])])
                        elif quality in ['3']:
                            for d in debrid_list:
                                d_source_720 = len([e for e in self.sources if e['quality'] in [
                                                   '720p', 'HD'] and d.valid_url(str(e['url']), e['source'])])
                                d_source_sd = len([e for e in self.sources if e['quality']
                                                   == 'SD' and d.valid_url(str(e['url']), e['source'])])
                        else:
                            for d in debrid_list:
                                d_source_sd = len([e for e in self.sources if e['quality']
                                                   == 'SD' and d.valid_url(str(e['url']), e['source'])])

                        d_total = d_source_4k + d_source_1080 + d_source_720 + d_source_sd

                if debrid_status:
                    d_4k_label = total_format % (
                        'red', d_source_4k) if d_source_4k == 0 else total_format % (
                        'lime', d_source_4k)
                    d_1080_label = total_format % (
                        'red', d_source_1080) if d_source_1080 == 0 else total_format % (
                        'lime', d_source_1080)
                    d_720_label = total_format % (
                        'red', d_source_720) if d_source_720 == 0 else total_format % (
                        'lime', d_source_720)
                    d_sd_label = total_format % (
                        'red', d_source_sd) if d_source_sd == 0 else total_format % (
                        'lime', d_source_sd)
                    d_total_label = total_format % (
                        'red', d_total) if d_total == 0 else total_format % (
                        'lime', d_total)

                source_4k_label = total_format % (
                    'red', source_4k) if source_4k == 0 else total_format % (
                    'lime', source_4k)
                source_1080_label = total_format % (
                    'red', source_1080) if source_1080 == 0 else total_format % (
                    'lime', source_1080)
                source_720_label = total_format % (
                    'red', source_720) if source_720 == 0 else total_format % (
                    'lime', source_720)
                source_sd_label = total_format % (
                    'red', source_sd) if source_sd == 0 else total_format % (
                    'lime', source_sd)
                source_total_label = total_format % ('red', total) if total == 0 else total_format % ('lime', total)

                if (i / 2) < timeout:
                    try:
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is
                                    True and x.getName() in mainsourceDict]
                        info = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is True]
                        if i >= timeout and len(mainleft) == 0 and len(self.sources) >= 100 * len(info):
                            break  # improve responsiveness
                        if debrid_status:
                            if quality in ['0']:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format)) % (string6, d_4k_label,
                                                                                d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format)) % (string7, source_4k_label,
                                                                                source_1080_label, source_720_label, source_sd_label, str(string4),
                                                                                source_total_label)
                                    print line1, line2
                                else:
                                    line1 = '|'.join(
                                        pdiag_bg_format[: -1]) % (
                                        source_4k_label, d_4k_label, source_1080_label, d_1080_label, source_720_label,
                                        d_720_label, source_sd_label, d_sd_label)
                            elif quality in ['1']:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = (
                                        '%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = (
                                        '%s:' + '|'.join(pdiag_format[1:])) % (
                                        string7, source_1080_label, source_720_label, source_sd_label, str(string4),
                                        source_total_label)
                                else:
                                    line1 = '|'.join(
                                        pdiag_bg_format[1:]) % (
                                        source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label,
                                        d_sd_label, source_total_label, d_total_label)
                            elif quality in ['2']:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = (
                                        '%s:' + '|'.join(pdiag_format[1:])) % (string6, d_1080_label, d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = (
                                        '%s:' + '|'.join(pdiag_format[1:])) % (
                                        string7, source_1080_label, source_720_label, source_sd_label, str(string4),
                                        source_total_label)
                                else:
                                    line1 = '|'.join(
                                        pdiag_bg_format[1:]) % (
                                        source_1080_label, d_1080_label, source_720_label, d_720_label, source_sd_label,
                                        d_sd_label, source_total_label, d_total_label)
                            elif quality in ['3']:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[2:])) % (string6,
                                                                                    d_720_label, d_sd_label, str(string4), d_total_label)
                                    line2 = (
                                        '%s:' + '|'.join(pdiag_format[2:])) % (string7, source_720_label, source_sd_label, str(string4), source_total_label)
                                else:
                                    line1 = '|'.join(
                                        pdiag_bg_format[2:]) % (
                                        source_720_label, d_720_label, source_sd_label, d_sd_label, source_total_label,
                                        d_total_label)
                            else:
                                if not progressDialog == control.progressDialogBG:
                                    line1 = ('%s:' + '|'.join(pdiag_format[3:])) % (string6,
                                                                                    d_sd_label, str(string4), d_total_label)
                                    line2 = ('%s:' + '|'.join(pdiag_format[3:])) % (string7,
                                                                                    source_sd_label, str(string4), source_total_label)
                                else:
                                    line1 = '|'.join(
                                        pdiag_bg_format[3:]) % (
                                        source_sd_label, d_sd_label, source_total_label, d_total_label)
                        else:
                            if quality in ['0']:
                                line1 = '|'.join(pdiag_format) % (source_4k_label, source_1080_label,
                                                                  source_720_label, source_sd_label, str(string4), source_total_label)
                            elif quality in ['1']:
                                line1 = '|'.join(
                                    pdiag_format[1:]) % (
                                    source_1080_label, source_720_label, source_sd_label, str(string4),
                                    source_total_label)
                            elif quality in ['2']:
                                line1 = '|'.join(
                                    pdiag_format[1:]) % (
                                    source_1080_label, source_720_label, source_sd_label, str(string4),
                                    source_total_label)
                            elif quality in ['3']:
                                line1 = '|'.join(
                                    pdiag_format[2:]) % (
                                    source_720_label, source_sd_label, str(string4),
                                    source_total_label)
                            else:
                                line1 = '|'.join(pdiag_format[3:]) % (source_sd_label, str(string4), source_total_label)

                        if debrid_status:
                            if len(info) > 6:
                                line3 = string3 % (str(len(info)))
                            elif len(info) > 0:
                                line3 = string3 % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1, line2, line3)
                            else:
                                progressDialog.update(max(1, percent), line1, line3)
                        else:
                            if len(info) > 6:
                                line2 = string3 % (str(len(info)))
                            elif len(info) > 0:
                                line2 = string3 % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5)
                            progressDialog.update(max(1, percent), line1, line2)
                    except Exception as e:
                        log_utils.log('Exception Raised: %s' % str(e), log_utils.LOGERROR)
                else:
                    try:
                        mainleft = [sourcelabelDict[x.getName()] for x in threads if x.is_alive() is
                                    True and x.getName() in mainsourceDict]
                        info = mainleft
                        if debrid_status:
                            if len(info) > 6:
                                line3 = 'Waiting for: %s' % (str(len(info)))
                            elif len(info) > 0:
                                line3 = 'Waiting for: %s' % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            if not progressDialog == control.progressDialogBG:
                                progressDialog.update(max(1, percent), line1, line2, line3)
                            else:
                                progressDialog.update(max(1, percent), line1, line3)
                        else:
                            if len(info) > 6:
                                line2 = 'Waiting for: %s' % (str(len(info)))
                            elif len(info) > 0:
                                line2 = 'Waiting for: %s' % (', '.join(info))
                            else:
                                break
                            percent = int(100 * float(i) / (2 * timeout) + 0.5) % 100
                            progressDialog.update(max(1, percent), line1, line2)
                    except Exception:
                        break

                time.sleep(0.5)
            except Exception:
                pass

        try:
            progressDialog.close()
        except Exception:
            pass

        self.sourcesFilter()

        return self.sources

    def prepareSources(self):
        try:
            control.makeFile(control.dataPath)

            self.sourceFile = control.providercacheFile

            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
            dbcur.execute(
                "CREATE TABLE IF NOT EXISTS rel_url ("
                "source TEXT, "
                "imdb_id TEXT, "
                "season TEXT, "
                "episode TEXT, "
                "rel_url TEXT, "
                "UNIQUE(source, imdb_id, season, episode)"
                ");")
            dbcur.execute(
                "CREATE TABLE IF NOT EXISTS rel_src ("
                "source TEXT, "
                "imdb_id TEXT, "
                "season TEXT, "
                "episode TEXT, "
                "hosts TEXT, "
                "added TEXT, "
                "UNIQUE(source, imdb_id, season, episode)"
                ");")
        except Exception:
            pass

    def getMovieSource(self, title, localtitle, aliases, year, imdb, source, call):

        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except Exception:
            pass

        ''' Fix to stop items passed with a 0 IMDB id pulling old unrelated sources from the database. '''
        if imdb == '0':
            try:
                dbcur.execute(
                    "DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                    (source, imdb, '', ''))
                dbcur.execute(
                    "DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                    (source, imdb, '', ''))
                dbcon.commit()
            except Exception:
                pass
        ''' END '''

        try:
            sources = []
            dbcur.execute(
                "SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, '', ''))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update is False:
                sources = eval(match[4].encode('utf-8'))
                return self.sources.extend(sources)
        except Exception:
            pass

        try:
            url = None
            dbcur.execute(
                "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = eval(url[4].encode('utf-8'))
        except Exception:
            pass

        try:
            if url is None:
                url = call.movie(imdb, title, localtitle, aliases, year)
            if url is None:
                raise Exception()
            dbcur.execute(
                "DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            sources = []
            sources = call.sources(url, self.hostDict, self.hostprDict)
            if sources is None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources:
                i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute(
                "DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, '',
                                                                            '', repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except Exception:
            pass

    def getEpisodeSource(
            self, title, year, imdb, tvdb, season, episode, tvshowtitle, localtvshowtitle, aliases, premiered, source,
            call):
        try:
            dbcon = database.connect(self.sourceFile)
            dbcur = dbcon.cursor()
        except Exception:
            pass

        try:
            sources = []
            dbcur.execute(
                "SELECT * FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, season, episode))
            match = dbcur.fetchone()
            t1 = int(re.sub('[^0-9]', '', str(match[5])))
            t2 = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            update = abs(t2 - t1) > 60
            if update is False:
                sources = eval(match[4].encode('utf-8'))
                return self.sources.extend(sources)
        except Exception:
            pass

        try:
            url = None
            dbcur.execute(
                "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, '', ''))
            url = dbcur.fetchone()
            url = eval(url[4].encode('utf-8'))
        except Exception:
            pass

        try:
            if url is None:
                url = call.tvshow(imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year)
            if url is None:
                raise Exception()
            dbcur.execute(
                "DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, '', ''))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, '', '', repr(url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            ep_url = None
            dbcur.execute(
                "SELECT * FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, season, episode))
            ep_url = dbcur.fetchone()
            ep_url = eval(ep_url[4].encode('utf-8'))
        except Exception:
            pass

        try:
            if url is None:
                raise Exception()
            if ep_url is None:
                ep_url = call.episode(url, imdb, tvdb, title, premiered, season, episode)
            if ep_url is None:
                raise Exception()
            dbcur.execute(
                "DELETE FROM rel_url WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_url Values (?, ?, ?, ?, ?)", (source, imdb, season, episode, repr(ep_url)))
            dbcon.commit()
        except Exception:
            pass

        try:
            sources = []
            sources = call.sources(ep_url, self.hostDict, self.hostprDict)
            if sources is None or sources == []:
                raise Exception()
            sources = [json.loads(t) for t in set(json.dumps(d, sort_keys=True) for d in sources)]
            for i in sources:
                i.update({'provider': source})
            self.sources.extend(sources)
            dbcur.execute(
                "DELETE FROM rel_src WHERE source = '%s' AND imdb_id = '%s' AND season = '%s' AND episode = '%s'" %
                (source, imdb, season, episode))
            dbcur.execute("INSERT INTO rel_src Values (?, ?, ?, ?, ?, ?)", (source, imdb, season,
                                                                            episode, repr(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
            dbcon.commit()
        except Exception:
            pass

    def alterSources(self, url, meta):
        try:
            if control.setting('hosts.mode') == '2':
                url += '&select=1'
            else:
                url += '&select=2'
            control.execute('RunPlugin(%s)' % url)
        except Exception:
            pass

    def clearSources(self):
        try:
            control.idle()

            yes = control.yesnoDialog(control.lang(32407).encode('utf-8'), '', '')
            if not yes:
                return

            control.makeFile(control.dataPath)
            dbcon = database.connect(control.providercacheFile)
            dbcur = dbcon.cursor()
            dbcur.execute("DROP TABLE IF EXISTS rel_src")
            dbcur.execute("DROP TABLE IF EXISTS rel_url")
            dbcur.execute("VACUUM")
            dbcon.commit()

            control.infoDialog(control.lang(32408).encode('utf-8'), sound=True, icon='INFO')
        except Exception:
            pass

    def sourcesFilter(self):
        provider = control.setting('hosts.sort.provider')
        if provider == '':
            provider = 'false'

        debrid_only = control.setting('debrid.only')
        if debrid_only == '': 
            debrid_only = 'false'

        sortthemup = control.setting('torrent.sort.them.up')
        if sortthemup == '':
            sortthemup = 'false'

        quality = control.setting('hosts.quality')
        if quality == '':
            quality = '0'

        captcha = control.setting('hosts.captcha')
        if captcha == '':
            captcha = 'true'

        HEVC = control.setting('HEVC')

        random.shuffle(self.sources)

        if provider == 'true':
            self.sources = sorted(self.sources, key=lambda k: k['provider'])


        for i in self.sources:
            if 'checkquality' in i and i['checkquality'] is True:
                if not i['source'].lower() in self.hosthqDict and i['quality'] not in ['SD', 'SCR', 'CAM']:
                    i.update({'quality': 'SD'})

        local = [i for i in self.sources if 'local' in i and i['local'] is True]
        for i in local:
            i.update({'language': self._getPrimaryLang() or 'en'})
        self.sources = [i for i in self.sources if i not in local]

        filter = []
        filter += [i for i in self.sources if i['direct'] is True]
        filter += [i for i in self.sources if i['direct'] is False]
        self.sources = filter

        filter = []

        for d in debrid.debrid_resolvers:
            valid_hoster = set([i['source'] for i in self.sources])
            valid_hoster = [i for i in valid_hoster if d.valid_url('', i)]
            if sortthemup == 'true':
                filter += [dict(i.items() + [('debrid', d.name)]) for i in self.sources if str(i['url']).startswith('magnet:')]
                filter += [dict(i.items() + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster and 'magnet:' not in str(i['url'])]
            else:
                filter += [dict(i.items() + [('debrid', d.name)]) for i in self.sources if i['source'] in valid_hoster or str(i['url']).startswith('magnet:')]
#        filter += [i for i in self.sources if not i['source'].lower() in self.hostprDict and i['debridonly'] is False]
        if debrid_only == 'false' or  debrid.status() == False:
            filter += [i for i in self.sources if not i['source'].lower() in self.hostprDict and i['debridonly'] is False]
        self.sources = filter

        for i in range(len(self.sources)):
            q = self.sources[i]['quality']
            if q == 'HD':
                self.sources[i].update({'quality': '720p'})

        filter = []
        filter += local

        if quality in ['0']:
            filter += [i for i in self.sources if i['quality'] == '4K' and 'debrid' in i]
        if quality in ['0']:
            filter += [i for i in self.sources if i['quality'] == '4K' and 'debrid' not in i and 'memberonly' in i]
        if quality in ['0']:
            filter += [i for i in self.sources if i['quality'] == '4K' and 'debrid' not in i and 'memberonly' not in i]

        if quality in ['0', '1']:
            filter += [i for i in self.sources if i['quality'] == '1440p' and 'debrid' in i]
        if quality in ['0', '1']:
            filter += [i for i in self.sources if i['quality'] == '1440p' and 'debrid' not in i and 'memberonly' in i]
        if quality in ['0', '1']:
            filter += [i for i in self.sources if i['quality'] ==
                       '1440p' and 'debrid' not in i and 'memberonly' not in i]

        if quality in ['0', '1', '2']:
            filter += [i for i in self.sources if i['quality'] == '1080p' and 'debrid' in i]
        if quality in ['0', '1', '2']:
            filter += [i for i in self.sources if i['quality'] == '1080p' and 'debrid' not in i and 'memberonly' in i]
        if quality in ['0', '1', '2']:
            filter += [i for i in self.sources if i['quality'] ==
                       '1080p' and 'debrid' not in i and 'memberonly' not in i]

        if quality in ['0', '1', '2', '3']:
            filter += [i for i in self.sources if i['quality'] == '720p' and 'debrid' in i]
        if quality in ['0', '1', '2', '3']:
            filter += [i for i in self.sources if i['quality'] == '720p' and 'debrid' not in i and 'memberonly' in i]
        if quality in ['0', '1', '2', '3']:
            filter += [i for i in self.sources if i['quality'] ==
                       '720p' and 'debrid' not in i and 'memberonly' not in i]

        filter += [i for i in self.sources if i['quality'] in ['SD', 'SCR', 'CAM']]
        self.sources = filter

        if not captcha == 'true':
            filter = [i for i in self.sources if i['source'].lower() in self.hostcapDict and 'debrid' not in i]
            self.sources = [i for i in self.sources if i not in filter]

        filter = [i for i in self.sources if i['source'].lower() in self.hostblockDict and 'debrid' not in i]
        self.sources = [i for i in self.sources if i not in filter]

        multi = [i['language'] for i in self.sources]
        multi = [x for y, x in enumerate(multi) if x not in multi[:y]]
        multi = True if len(multi) > 1 else False

        if multi is True:
            self.sources = [i for i in self.sources if not i['language'] ==
                            'en'] + [i for i in self.sources if i['language'] == 'en']

        self.sources = self.sources[:4000]

        extra_info = control.setting('sources.extrainfo')

        prem_identify = control.setting('prem.identify')
        if prem_identify == '':
            prem_identify = 'blue'
        prem_identify = self.getPremColor(prem_identify)

        torr_identify = control.setting('torrent.identify')
        if torr_identify == '':
            torr_identify = 'magenta'
        torr_identify = self.getPremColor(torr_identify)

        for i in range(len(self.sources)):

            if extra_info == 'true':
                t = source_utils.getFileType(self.sources[i]['url'])
            else:
                t = None

            u = self.sources[i]['url']

            p = self.sources[i]['provider']

            q = self.sources[i]['quality']

            s = self.sources[i]['source']

            s = s.rsplit('.', 1)[0]

            l = self.sources[i]['language']

            try:
                f = (' | '.join(['[I]%s [/I]' % info.strip() for info in self.sources[i]['info'].split('|')]))
            except Exception:
                f = ''

            try:
                d = self.sources[i]['debrid']
            except Exception:
                d = self.sources[i]['debrid'] = ''

            if d.lower() == 'real-debrid':
                d = 'RD'

            if not d == '':
                label = '%02d | [B]%s | %s[/B] | ' % (int(i+1), d, p)
            else:
                label = '%02d | [B]%s[/B] | ' % (int(i+1), p)

            if multi is True and not l == 'en':
                label += '[B]%s[/B] | ' % l

            if t:
                if q in ['4K', '1440p', '1080p', '720p']:
                    label += '%s | [B][I]%s [/I][/B] | [I]%s[/I] | %s' % (s, q, t, f)
                elif q == 'SD':
                    label += '%s | %s | [I]%s[/I]' % (s, f, t)
                else:
                    label += '%s | %s | [I]%s [/I] | [I]%s[/I]' % (s, f, q, t)
            else:
                if q in ['4K', '1440p', '1080p', '720p']:
                    label += '%s | [B][I]%s [/I][/B] | %s' % (s, q, f)
                elif q == 'SD':
                    label += '%s | %s' % (s, f)
                else:
                    label += '%s | %s | [I]%s [/I]' % (s, f, q)
            label = label.replace('| 0 |', '|').replace(' | [I]0 [/I]', '')
            label = re.sub('\[I\]\s+\[/I\]', ' ', label)
            label = re.sub('\|\s+\|', '|', label)
            label = re.sub('\|(?:\s+|)$', '', label)

            if d:
                if 'torrent' in s.lower():
                    if not torr_identify == 'nocolor':
                        self.sources[i]['label'] = ('[COLOR %s]' % (torr_identify)) + label.upper() + '[/COLOR]'
                    else:
                        self.sources[i]['label'] = label.upper()
                else:
                    if not prem_identify == 'nocolor':
                        self.sources[i]['label'] = ('[COLOR %s]' % (prem_identify)) + label.upper() + '[/COLOR]'
                    else:
                        self.sources[i]['label'] = label.upper()
            else:
                self.sources[i]['label'] = label.upper()

        try:
            if not HEVC == 'true':
                self.sources = [i for i in self.sources if 'HEVC' not in i['label']]
        except Exception:
            pass

        self.sources = [i for i in self.sources if 'label' in i]

        return self.sources

    def sourcesResolve(self, item, info=False):
        try:
            self.url = None

            u = url = item['url']

            d = item['debrid']
            direct = item['direct']
            local = item.get('local', False)

            provider = item['provider']
            call = [i[1] for i in self.sourceDict if i[0] == provider][0]
            u = url = call.resolve(url)
            if url is None or ('://' not in str(url) and not local and 'magnet:' not in str(url)):
                raise Exception()

            if not local:
                url = url[8:] if url.startswith('stack:') else url

                urls = []
                for part in url.split(' , '):
                    u = part
                    if not d == '':
                        part = debrid.resolver(part, d)
                    elif direct is not True:
                        hmf = urlresolver.HostedMediaFile(url=u, include_disabled=True, include_universal=False)
                        if hmf.valid_url() is True:
                            part = hmf.resolve()
                    urls.append(part)

                url = 'stack://' + ' , '.join(urls) if len(urls) > 1 else urls[0]

            if url is False or url is None:
                raise Exception()

            ext = url.split('?')[0].split('&')[0].split('|')[0].rsplit('.')[-1].replace('/', '').lower()
            if ext == 'rar':
                raise Exception()

            try:
                headers = url.rsplit('|', 1)[1]
            except Exception:
                headers = ''
            headers = urllib.quote_plus(headers).replace('%3D', '=') if ' ' in headers else headers
            headers = dict(urlparse.parse_qsl(headers))

            if url.startswith('http') and '.m3u8' in url:
                result = client.request(url.split('|')[0], headers=headers, output='geturl', timeout='20')
                if result is None:
                    raise Exception()

            elif url.startswith('http'):
                result = client.request(url.split('|')[0], headers=headers, output='chunk', timeout='20')
                if result is None:
                    raise Exception()

            self.url = url
            return url
        except Exception:
            if info is True:
                self.errorForSources()
            return

    def sourcesDialog(self, items):
        try:

            labels = [i['label'] for i in items]

            select = control.selectDialog(labels)
            if select == -1:
                return 'close://'

            next = [y for x, y in enumerate(items) if x >= select]
            prev = [y for x, y in enumerate(items) if x < select][::-1]

            items = [items[select]]
            items = [i for i in items+next+prev][:40]

            header = control.addonInfo('name')
            header2 = header.upper()

            progressDialog = control.progressDialog if control.setting(
                'progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            progressDialog.update(0)

            block = None

            for i in range(len(items)):
                try:
                    if items[i]['source'] == block:
                        raise Exception()

                    w = workers.Thread(self.sourcesResolve, items[i])
                    w.start()

                    try:
                        if progressDialog.iscanceled():
                            break
                        progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
                    except Exception:
                        progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))

                    m = ''

                    for x in range(3600):
                        try:
                            if xbmc.abortRequested is True:
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        k = control.condVisibility('Window.IsActive(virtualkeyboard)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30) and not k:
                            break
                        k = control.condVisibility('Window.IsActive(yesnoDialog)')
                        if k:
                            m += '1'
                            m = m[-1]
                        if (w.is_alive() is False or x > 30) and not k:
                            break
                        time.sleep(0.5)

                    for x in range(30):
                        try:
                            if xbmc.abortRequested is True:
                                return sys.exit()
                            if progressDialog.iscanceled():
                                return progressDialog.close()
                        except Exception:
                            pass

                        if m == '':
                            break
                        if w.is_alive() is False:
                            break
                        time.sleep(0.5)

                    if w.is_alive() is True:
                        block = items[i]['source']

                    if self.url is None:
                        raise Exception()

                    self.selectedSource = items[i]['label']

                    try:
                        progressDialog.close()
                    except Exception:
                        pass

                    control.execute('Dialog.Close(virtualkeyboard)')
                    control.execute('Dialog.Close(yesnoDialog)')
                    return self.url
                except Exception:
                    pass

            try:
                progressDialog.close()
            except Exception:
                pass

        except Exception as e:
            try:
                progressDialog.close()
            except Exception:
                pass
            log_utils.log('Error %s' % str(e), log_utils.LOGNOTICE)

    def sourcesDirect(self, items):
        filter = [i for i in items if i['source'].lower() in self.hostcapDict and i['debrid'] == '']
        items = [i for i in items if i not in filter]

        filter = [i for i in items if i['source'].lower() in self.hostblockDict and i['debrid'] == '']
        items = [i for i in items if i not in filter]

        items = [i for i in items if ('autoplay' in i and i['autoplay'] is True) or 'autoplay' not in i]

        if control.setting('autoplay.sd') == 'true':
            items = [i for i in items if i['quality'] not in ['4K', '1440p', '1080p', 'HD']]

        u = None

        header = control.addonInfo('name')
        header2 = header.upper()

        try:
            control.sleep(1000)

            progressDialog = control.progressDialog if control.setting(
                'progress.dialog') == '0' else control.progressDialogBG
            progressDialog.create(header, '')
            progressDialog.update(0)
        except Exception:
            pass

        for i in range(len(items)):
            try:
                if progressDialog.iscanceled():
                    break
                progressDialog.update(int((100 / float(len(items))) * i), str(items[i]['label']), str(' '))
            except Exception:
                progressDialog.update(int((100 / float(len(items))) * i), str(header2), str(items[i]['label']))

            try:
                if xbmc.abortRequested is True:
                    return sys.exit()

                url = self.sourcesResolve(items[i])
                if u is None:
                    u = url
                if url is not None:
                    break
            except Exception:
                pass

        try:
            progressDialog.close()
        except Exception:
            pass

        return u

    def errorForSources(self):
        control.infoDialog(control.lang(32401).encode('utf-8'), sound=False, icon='INFO')

    def getLanguage(self):
        langDict = {
            'English': ['en'],
            'German': ['de'],
            'German+English': ['de', 'en'],
            'French': ['fr'],
            'French+English': ['fr', 'en'],
            'Portuguese': ['pt'],
            'Portuguese+English': ['pt', 'en'],
            'Polish': ['pl'],
            'Polish+English': ['pl', 'en'],
            'Korean': ['ko'],
            'Korean+English': ['ko', 'en'],
            'Russian': ['ru'],
            'Russian+English': ['ru', 'en'],
            'Spanish': ['es'],
            'Spanish+English': ['es', 'en'],
            'Greek': ['gr'],
            'Italian': ['it'],
            'Italian+English': ['it', 'en'],
            'Greek+English': ['gr', 'en']}
        name = control.setting('providers.lang')
        return langDict.get(name, ['en'])

    def getLocalTitle(self, title, imdb, tvdb, content):
        lang = self._getPrimaryLang()
        if not lang:
            return title

        if content == 'movie':
            t = trakt.getMovieTranslation(imdb, lang)
        else:
            t = tvmaze.tvMaze().getTVShowTranslation(tvdb, lang)

        return t or title

    def getAliasTitles(self, imdb, localtitle, content):
        lang = self._getPrimaryLang()

        try:
            t = trakt.getMovieAliases(imdb) if content == 'movie' else trakt.getTVShowAliases(imdb)
            t = [i for i in t if i.get('country', '').lower() in [lang, '', 'us']
                 and i.get('title', '').lower() != localtitle.lower()]
            return t
        except Exception:
            return []

    def _getPrimaryLang(self):
        langDict = {
            'English': 'en', 'German': 'de', 'German+English': 'de', 'French': 'fr', 'French+English': 'fr',
            'Portuguese': 'pt', 'Portuguese+English': 'pt', 'Polish': 'pl', 'Polish+English': 'pl', 'Korean': 'ko',
            'Korean+English': 'ko', 'Russian': 'ru', 'Russian+English': 'ru', 'Spanish': 'es', 'Spanish+English': 'es',
            'Italian': 'it', 'Italian+English': 'it', 'Greek': 'gr', 'Greek+English': 'gr'}
        name = control.setting('providers.lang')
        lang = langDict.get(name)
        return lang

    def getTitle(self, title):
        title = cleantitle.normalize(title)
        return title

    def getConstants(self):
        self.itemProperty = 'plugin.video.exodus.container.items'

        self.metaProperty = 'plugin.video.exodus.container.meta'

	#from resources.lib.sources import sources
#	from lambdascrapers import sources
	from exoscrapers import sources

        self.sourceDict = sources()

        try:
            self.hostDict = urlresolver.relevant_resolvers(order_matters=True)
            self.hostDict = [i.domains for i in self.hostDict if '*' not in i.domains]
            self.hostDict = [i.lower() for i in reduce(lambda x, y: x+y, self.hostDict)]
            self.hostDict = [x for y, x in enumerate(self.hostDict) if x not in self.hostDict[:y]]
        except Exception:
            self.hostDict = []

        self.hostprDict = ['1fichier.com', 'oboom.com', 'rapidgator.net', 'rg.to', 'uploaded.net',
                           'uploaded.to', 'ul.to', 'filefactory.com', 'nitroflare.com', 'turbobit.net', 'uploadrocket.net']

        self.hostcapDict = ['hugefiles.net', 'kingfiles.net', 'openload.io', 'openload.co',
                            'oload.tv', 'thevideo.me', 'vidup.me', 'streamin.to', 'torba.se']

        self.hosthqDict = [
            'gvideo', 'google.com', 'openload.io', 'openload.co', 'oload.tv', 'thevideo.me', 'rapidvideo.com',
            'raptu.com', 'filez.tv', 'uptobox.com', 'uptobox.com', 'uptostream.com', 'xvidstage.com', 'streamango.com']

        self.hostblockDict = []

    def getPremColor(self, n):
        if n == '0':
            n = 'blue'
        elif n == '1':
            n = 'red'
        elif n == '2':
            n = 'yellow'
        elif n == '3':
            n = 'deeppink'
        elif n == '4':
            n = 'cyan'
        elif n == '5':
            n = 'lawngreen'
        elif n == '6':
            n = 'gold'
        elif n == '7':
            n = 'magenta'
        elif n == '8':
            n = 'yellowgreen'
        elif n == '9':
            n = 'nocolor'
        else:
            n == 'blue'
        return n
