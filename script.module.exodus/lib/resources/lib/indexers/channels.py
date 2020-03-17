# -*- coding: utf-8 -*-

'''
    Covenant Add-on

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


from resources.lib.modules import cleangenre
from resources.lib.modules import control
from resources.lib.modules import client
from resources.lib.modules import metacache
from resources.lib.modules import workers
from resources.lib.modules import trakt

import sys,re,json,urllib,urlparse,datetime

params = dict(urlparse.parse_qsl(sys.argv[2].replace('?',''))) if len(sys.argv) > 1 else dict()

action = params.get('action')

class channels:
    def __init__(self):
        self.list = [] ; self.items = []

        self.uk_datetime = self.uk_datetime()
        self.systime = (self.uk_datetime).strftime('%Y%m%d%H%M%S%f')
        self.tm_img_link = 'https://image.tmdb.org/t/p/w%s%s'
        self.lang = control.apiLanguage()['trakt']

        self.sky_now_link = 'http://epgservices.sky.com/5.1.1/api/2.0/channel/json/%s/now/nn/0'
        self.sky_programme_link = 'http://tv.sky.com/programme/channel/%s/%s/%s.json'


    def get(self):
        channels = [
            ('01', 'Sky Premiere', '4021'),
            ('02', 'Sky Premiere +1', '1823'),
            ('03', 'Sky Showcase', '4033'),
            ('04', 'Sky Greats', '1815'),
            ('05', 'Sky Disney', '4013'),
            ('06', 'Sky Family', '4018'),
            ('07', 'Sky Action', '4014'),
            ('08', 'Sky Comedy', '4019'),
            ('09', 'Sky Crime', '4062'),
            ('10', 'Sky Drama', '4016'),
            ('11', 'Sky Sci Fi', '4017'),
            ('12', 'Sky Select', '4020'),
            ('13', 'Film4', '4044'),
            ('14', 'Film4 +1', '1629'),
            ('15', 'TCM', '3811'),
            ('16', 'TCM +1', '5275')
        ]

        threads = []
        for i in channels: threads.append(workers.Thread(self.sky_list, i[0], i[1], i[2]))
        [i.start() for i in threads]
        [i.join() for i in threads]

        threads = []
        for i in range(0, len(self.items)): threads.append(workers.Thread(self.items_list, self.items[i]))
        [i.start() for i in threads]
        [i.join() for i in threads]

        self.list = metacache.local(self.list, self.tm_img_link, 'poster2', 'fanart')

        try: self.list = sorted(self.list, key=lambda k: k['num'])
        except: pass

        self.channelDirectory(self.list)
        return self.list


    def sky_list(self, num, channel, id):
        try:
            url = self.sky_now_link % id
            result = client.request(url, timeout='10')
            result = json.loads(result)
            match = result['listings'][id][0]['url']

            dt1 = (self.uk_datetime).strftime('%Y-%m-%d')
            dt2 = int((self.uk_datetime).strftime('%H'))
            if (dt2 < 6): dt2 = 0
            elif (dt2 >= 6 and dt2 < 12): dt2 = 1
            elif (dt2 >= 12 and dt2 < 18): dt2 = 2
            elif (dt2 >= 18): dt2 = 3

            url = self.sky_programme_link % (id, str(dt1), str(dt2))
            result = client.request(url, timeout='10')
            result = json.loads(result)
            result = result['listings'][id]
            result = [i for i in result if i['url'] == match][0]

            year = result['d']
            year = re.findall('[(](\d{4})[)]', year)[0].strip()
            year = year.encode('utf-8')

            title = result['t']
            title = title.replace('(%s)' % year, '').strip()
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            self.items.append((title, year, channel, num))
        except:
            pass


    def items_list(self, i):
        try:
            item = trakt.SearchAll(i[0], i[1], True)[0]

            content = item.get('movie')
            if not content: content = item.get('show')
            item = content

            title = item.get('title')
            title = client.replaceHTMLCodes(title)

            originaltitle = title

            year = item.get('year', 0)
            year = re.sub('[^0-9]', '', str(year))

            imdb = item.get('ids', {}).get('imdb', '0')
            imdb = 'tt' + re.sub('[^0-9]', '', str(imdb))

            tmdb = str(item.get('ids', {}).get('tmdb', 0))

            premiered = item.get('released', '0')
            try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            except: premiered = '0'

            genre = item.get('genres', [])
            genre = [x.title() for x in genre]
            genre = ' / '.join(genre).strip()
            if not genre: genre = '0'

            duration = str(item.get('Runtime', 0))

            rating = item.get('rating', '0')
            if not rating or rating == '0.0': rating = '0'

            votes = item.get('votes', '0')
            try: votes = str(format(int(votes), ',d'))
            except: pass

            mpaa = item.get('certification', '0')
            if not mpaa: mpaa = '0'

            tagline = item.get('tagline', '0')

            plot = item.get('overview', '0')

            people = trakt.getPeople(imdb, 'movies')

            director = writer = ''
            if 'crew' in people and 'directing' in people['crew']:
                director = ', '.join([director['person']['name'] for director in people['crew']['directing'] if director['job'].lower() == 'director'])
            if 'crew' in people and 'writing' in people['crew']:
                writer = ', '.join([writer['person']['name'] for writer in people['crew']['writing'] if writer['job'].lower() in ['writer', 'screenplay', 'author']])

            cast = []
            for person in people.get('cast', []):
                cast.append({'name': person['person']['name'], 'role': person['character']})
            cast = [(person['name'], person['role']) for person in cast]

            try:
                if self.lang == 'en' or self.lang not in item.get('available_translations', [self.lang]): raise Exception()

                trans_item = trakt.getMovieTranslation(imdb, self.lang, full=True)

                title = trans_item.get('title') or title
                tagline = trans_item.get('tagline') or tagline
                plot = trans_item.get('overview') or plot
            except:
                pass

            self.list.append({'title': title, 'originaltitle': originaltitle, 'year': year, 'premiered': premiered, 'genre': genre, 'duration': duration, 'rating': rating, 'votes': votes, 'mpaa': mpaa, 'director': director, 'writer': writer, 'cast': cast, 'plot': plot, 'tagline': tagline, 'imdb': imdb, 'tmdb': tmdb, 'poster': '0', 'channel': i[2], 'num': i[3]})
        except:
            pass


    def uk_datetime(self):
        dt = datetime.datetime.utcnow() + datetime.timedelta(hours = 0)
        d = datetime.datetime(dt.year, 4, 1)
        dston = d - datetime.timedelta(days=d.weekday() + 1)
        d = datetime.datetime(dt.year, 11, 1)
        dstoff = d - datetime.timedelta(days=d.weekday() + 1)
        if dston <=  dt < dstoff:
            return dt + datetime.timedelta(hours = 1)
        else:
            return dt


    def channelDirectory(self, items):
        if items == None or len(items) == 0: control.idle() ; sys.exit()

        sysaddon = sys.argv[0]

        syshandle = int(sys.argv[1])

        addonPoster, addonBanner = control.addonPoster(), control.addonBanner()

        addonFanart, settingFanart = control.addonFanart(), control.setting('fanart')

        try: isOld = False ; control.item().getArt('type')
        except: isOld = True

        isPlayable = 'true' if not 'plugin' in control.infoLabel('Container.PluginName') else 'false'

        playbackMenu = control.lang(32063).encode('utf-8') if control.setting('hosts.mode') == '2' else control.lang(32064).encode('utf-8')

        queueMenu = control.lang(32065).encode('utf-8')

        refreshMenu = control.lang(32072).encode('utf-8')


        for i in items:
            try:
                label = '[B]%s[/B] : %s (%s)' % (i['channel'].upper(), i['title'], i['year'])
                sysname = urllib.quote_plus('%s (%s)' % (i['title'], i['year']))
                systitle = urllib.quote_plus(i['title'])
                imdb, tmdb, year = i['imdb'], i['tmdb'], i['year']

                meta = dict((k,v) for k, v in i.iteritems() if not v == '0')
                meta.update({'code': imdb, 'imdbnumber': imdb, 'imdb_id': imdb})
                meta.update({'tmdb_id': tmdb})
                meta.update({'mediatype': 'movie'})
                meta.update({'trailer': '%s?action=trailer&name=%s' % (sysaddon, sysname)})
                #meta.update({'trailer': 'plugin://script.extendedinfo/?info=playtrailer&&id=%s' % imdb})
                meta.update({'playcount': 0, 'overlay': 6})
                try: meta.update({'genre': cleangenre.lang(meta['genre'], self.lang)})
                except: pass

                sysmeta = urllib.quote_plus(json.dumps(meta))


                url = '%s?action=play&title=%s&year=%s&imdb=%s&meta=%s&t=%s' % (sysaddon, systitle, year, imdb, sysmeta, self.systime)
                sysurl = urllib.quote_plus(url)


                cm = []

                cm.append((queueMenu, 'RunPlugin(%s?action=queueItem)' % sysaddon))

                cm.append((refreshMenu, 'RunPlugin(%s?action=refresh)' % sysaddon))

                cm.append((playbackMenu, 'RunPlugin(%s?action=alterSources&url=%s&meta=%s)' % (sysaddon, sysurl, sysmeta)))

                if isOld == True:
                    cm.append((control.lang2(19033).encode('utf-8'), 'Action(Info)'))


                item = control.item(label=label)

                art = {}

                if 'poster2' in i and not i['poster2'] == '0':
                    art.update({'icon': i['poster2'], 'thumb': i['poster2'], 'poster': i['poster2']})
                elif 'poster' in i and not i['poster'] == '0':
                    art.update({'icon': i['poster'], 'thumb': i['poster'], 'poster': i['poster']})
                else:
                    art.update({'icon': addonPoster, 'thumb': addonPoster, 'poster': addonPoster})

                art.update({'banner': addonBanner})

                if settingFanart == 'true' and 'fanart' in i and not i['fanart'] == '0':
                    item.setProperty('Fanart_Image', i['fanart'])
                elif not addonFanart == None:
                    item.setProperty('Fanart_Image', addonFanart)

                item.setArt(art)
                item.addContextMenuItems(cm)
                item.setProperty('IsPlayable', isPlayable)
                item.setInfo(type='Video', infoLabels = meta)

                video_streaminfo = {'codec': 'h264'}
                item.addStreamInfo('video', video_streaminfo)

                control.addItem(handle=syshandle, url=url, listitem=item, isFolder=False)
            except:
                pass

        control.content(syshandle, 'files')
        control.directory(syshandle, cacheToDisc=True)


