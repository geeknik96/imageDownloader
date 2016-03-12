__author__ = 'somenkov'

import downloaders.get_ip_helpers as ip_getter
import downloaders.tor_management as tor
import urllib.parse
import urllib.request
import urllib.error
import json


opener, csock, proc = tor.start_tor_with_config('C:/Tor/tor.exe', control_port=9149, proxy_port=9148)


aim = 'Musician'

def do_query(cur: str):
    query = [{
        'name': None,
        '/people/person/date_of_birth': None,
        'type': '/people/person',
        '/people/person/profession': aim
    }]
    params = {
        #'key': 'AIzaSyCHlq-t5Qn47YBxCzMus_NKdGpTRqNyHco',
        'query': json.dumps(query),
        'cursor': cur
    }
    service_url = 'https://www.googleapis.com/freebase/v1/mqlread'
    url = service_url + '?' + urllib.parse.urlencode(params)
    resp = opener.open(url).read()
    response = json.loads(resp.decode())
    pass
    return response['cursor'], response['result']


def dev_null(x):
    pass


names_count = 0
with open('lists_freebase.txt', 'w', encoding='utf-8') as res:
    res.write(aim + '\n')
    cursor, result = do_query('')
    count = 0
    while cursor:
        try:
            parse = lambda name: str(name.decode('utf-8'))
            for item in result:
                names_count += 1
                if item['/people/person/date_of_birth'] is None:
                    res.write(item['name'] + '\n')
                else:
                    res.write(item['name'] + '\t' + item['/people/person/date_of_birth'] + '\n')
            print('Get', names_count, 'names')
            res.flush()
            cursor, result = do_query(cursor)
        except urllib.error.HTTPError as e:
            cur_ip = ip_getter.get_current_ip_httpbin_org(opener=opener)
            print(e, 'changing IP ', cur_ip, end=' ')
            tor.update_ip(cur_ip, opener, csock, ip_getter.get_current_ip_httpbin_org, dev_null)
            cur_ip = ip_getter.get_current_ip_httpbin_org(opener=opener)
            print('->', cur_ip)
