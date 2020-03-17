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

from resources.lib.modules import control
import sys, requests, json, urllib, urlparse, os

sysaddon = sys.argv[0] ; syshandle = int(sys.argv[1])
accepted_extensions = ['mkv','mp4','avi', 'm4v']

class furk:
    def __init__(self):
        self.base_link = "https://www.furk.net"
        self.meta_search_link = "/api/plugins/metasearch?api_key=%s&q=%s"
        self.get_user_files_link = "/api/file/get?api_key=%s"
        self.file_info_link = "/api/file/info?api_key%s"
        self.file_link_link = "/api/file/link?"
        self.protect_file_link = "/api/file/protect?"
        self.user_feeds_link = "/api/feed/get?"
        self.add_download_link = "/api/dl/add?"
        self.api_key = control.setting('furk.api')
        self.list = []

    def user_files(self):
        if self.api_key == '':
            return ''
        try:
            s = requests.Session()
            url = self.base_link + self.get_user_files_link % self.api_key
            p = s.get(url)
            p = json.loads(p.text)
            files = p['files']
            for i in files:
                name = i['name']
                id = i['id']
                url_dl = ''
                for x in accepted_extensions:
                    if i['url_dl'].endswith(x):
                       url_dl = i['url_dl']
                    else:
                        continue
                if url_dl == '':
                    continue
                if not int(i['files_num_video_player']) > 1:
                    if int(i['ss_num']) > 0:
                        thumb = i['ss_urls'][0]
                    else:
                        thumb = ''

                    self.addDirectoryItem(name , url_dl, thumb, '', False)

                else:
                    pass
            self.endDirectory()
            return ''
        except:
            pass
    def search(self):
        from resources.lib.indexers import navigator

        navigator.navigator().addDirectoryItem('New Search', 'furkSearchNew', 'search.png', 'search.png')
        try: from sqlite3 import dbapi2 as database
        except: from pysqlite2 import dbapi2 as database

        dbcon = database.connect(control.searchFile)
        dbcur = dbcon.cursor()

        try:
            dbcur.executescript("CREATE TABLE IF NOT EXISTS furk (ID Integer PRIMARY KEY AUTOINCREMENT, term);")
        except:
            pass

        dbcur.execute("SELECT * FROM furk ORDER BY ID DESC")
        lst = []

        delete_option = False
        for (id,term) in dbcur.fetchall():
            if term not in str(lst):
                delete_option = True
                navigator.navigator().addDirectoryItem(term, 'furkMetaSearch&url=%s' % term, 'search.png', 'search.png')
                lst += [(term)]
        dbcur.close()

        if delete_option:
            navigator.navigator().addDirectoryItem(32605, 'clearCacheSearch', 'tools.png', 'DefaultAddonProgram.png')

        navigator.navigator().endDirectory()

    def search_new(self):
            control.idle()

            t = control.lang(32010).encode('utf-8')
            k = control.keyboard('', t) ; k.doModal()
            q = k.getText() if k.isConfirmed() else None

            if (q == None or q == ''): return

            try: from sqlite3 import dbapi2 as database
            except: from pysqlite2 import dbapi2 as database

            dbcon = database.connect(control.searchFile)
            dbcur = dbcon.cursor()
            dbcur.execute("INSERT INTO furk VALUES (?,?)", (None,q))
            dbcon.commit()
            dbcur.close()
            url = urllib.quote_plus(q)
            url = '%s?action=furkMetaSearch&url=%s' % (sys.argv[0], urllib.quote_plus(url))
            control.execute('Container.Update(%s)' % url)

    def furk_meta_search(self, url):
        if self.api_key == '':
            return ''
        try:
            s = requests.Session()
            url = (self.base_link + self.meta_search_link % (self.api_key, url)).replace(' ', '+')
            p = s.get(url)
            p = json.loads(p.text)
            files = p['files']
            for i in files:
                name = i['name']
                id = i['id']
                url_dl = ''
                for x in accepted_extensions:
                    if 'url_dl' in i:
                        if i['url_dl'].endswith(x):
                            url_dl = i['url_dl']
                        else:
                            continue
                    else:
                        continue
                if url_dl == '':
                    continue
                if not int(i['files_num_video_player']) > 1:
                    if int(i['ss_num']) > 0:
                        thumb = i['ss_urls'][0]
                    else:
                        thumb = ''

                    self.addDirectoryItem(name, url_dl, thumb, '', False)

                else:
                    # print(i['name'])
                    # self.addDirectoryItem(i['name'].encode('utf-8'), i['url_dl'], '', '')
                    continue
            self.endDirectory()
            return ''
        except:
            pass

    def addDirectoryItem(self, name, query, thumb, icon, isAction=True):
        try:
            name = name.encode('utf-8')
            url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
            item = control.item(label=name)
            item.setArt({'icon': thumb, 'thumb': thumb})
            control.addItem(handle=syshandle, url=url, listitem=item)
        except:
            pass

    def endDirectory(self):
        control.content(syshandle, 'addons')
        control.directory(syshandle, cacheToDisc=True)
