# -*- coding: utf-8 -*-



import re,urlparse,json
from resources.lib.modules import client

def resolve(url):
    try:
        if '/vod/' in url:
            url = re.compile('/(\d+)').findall(url)[-1]
            url = 'http://www.filmon.com/vod/info/%s' % url
        elif '/tv/' in url:
            url = url.replace('/tv/', '/channel/')
        elif not '/channel/' in url:
            raise Exception()


        headers = {'X-Requested-With': 'XMLHttpRequest'}

        cookie = client.request(url, output='cookie')

        cid = client.request(url, headers=headers)
        cid = json.loads(cid)['id']
        

        headers = {'X-Requested-With': 'XMLHttpRequest', 'Referer': url}

        url = 'http://www.filmon.com/ajax/getChannelInfo?channel_id=%s' % cid

        result = client.request(url, cookie=cookie, headers=headers)

        result = json.loads(result)
        try:
            result = result['streams']
        except:
            result = result['data']['streams']
            result = [i[1] for i in result.items()]

        url = [(i['url'], int(i['watch-timeout'])) for i in result]
        url = [i for i in url if '.m3u8' in i[0]]
        
        url.sort()
        url = url[-1][0]

        return url
    except:
        return

