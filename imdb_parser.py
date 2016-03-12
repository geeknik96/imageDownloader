# coding=utf-8
__author__ = 'somenkov'

"""getting list of actors and actress"""

from urllib import request as req
from urllib import error
from urllib import parse
import json
import bs4
import argparse
import time
from threading import Thread as thread


file_result = open('../actors+info.txt', 'w', encoding='utf-8')


def parse_imdb(html):
    try:
        soup = bs4.BeautifulSoup(html.read(), 'html.parser')
    except:
        return '?', '?', '?', '?'

    born = soup.find('time')
    born = '?' if born is None else born.get('datetime')

    job = soup.find('span', attrs={'itemprop':'jobTitle'})
    job = '?' if job is None else job.text[1:]

    img_url = soup.find('img', attrs={'id':'name-poster'})
    img_url = '?' if img_url is None else img_url.get('src')

    position = soup.find('a', attrs={'id': 'meterRank'})
    position = '?' if position is None else position.text
    position = '?' if position == 'SEE RANK' else position

    return born, job, position, img_url


def get_id(json_data, name: str) -> str:
    name = name.lower()
    data = json.loads(json_data)
    ids = [(res['name'], res['id']) for val in data.values() for res in val]
    for iname, id in ids:
        parse_name = bs4.BeautifulSoup(iname, 'html.parser').text.lower().encode().lower()
        if parse_name == name:
           return id
        elif len(parse_name) == len(name):
            not_equal = 0
            for c1, c2 in zip(parse_name, name):
                not_equal += 1 if c1 != c2 else 0
            if not_equal < 3:
                return id
    return ''


def get_information(name: str):
    page_url = 'http://www.imdb.com/name/{0}/'
    url = 'http://www.imdb.com/xml/find?json=1&nr=1&nm=on&q=' + parse.quote_plus(name)
    for i in range(5):
        try:
            id = get_id(req.urlopen(url).read().decode(), name)
            html = req.urlopen(page_url.format(id))
            return parse_imdb(html)
        except error.HTTPError:
            time.sleep(1)
            if i == 4:
                return '?', '?', '?', '?'
        except Exception as e:
            print(e)
            return '?', '?', '?', '?'


def get_informations(n: int, names: list):
    global file_result
    counter = 0
    print('Hi, thread', n, len(names))
    for name in names:
        result = get_information(name)
        print('Thread {0}: get {1} name {2} {3}'.format(n, counter, str(name), str(result)))
        file_result.write((str(name.decode()) + '\t' + '\t'.join(i for i in result) + '\n'))
        file_result.flush()
        counter += 1


def main(actors, numthread):
    with open(actors, encoding='utf-8') as file:
        names = [name[:-1].encode() for name in file]

    step = round(len(names) / numthread)
    ranges = [(a, a + step) for a in range(0, len(names), step)]
    threads = [thread(target=get_informations, args=(n, names[a:b])) for n, (a, b) in enumerate(ranges)]
    [t.start() for t in threads]
    [t.join() for t in threads]

if __name__ == '__main__':
    arguments_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arguments_parser.add_argument('-a', '--actors', help='path to file with actors', type=str, default='../lists/wiki/filtered/_all_actors.txt')
    arguments_parser.add_argument('-n', '--numthread', help='num of threads', type=int, default=1)
    args = arguments_parser.parse_args()
    main(args.actors, args.numthread)