__author__ = 'somenkov'

"""Test to run multiple one tor instance, but multiple threads that use it."""

from bs4 import BeautifulSoup
from downloaders import tor_management
import threading
import urllib.request
import time
import json
import argparse

start_name_time = time.time()
MAX_PAGE = 165
updating = True


def get_img_from_quary(quary, page, opener, result):
    url = 'https://yandex.ru/images/search?text=' + \
        urllib.request.quote(quary) + '&p=' + str(page)
    urls = set()
    try:
        soup = BeautifulSoup(opener.open(url,timeout=6).read(), 'html.parser')
        for div in soup.find_all('div', class_='serp-item'):
            data_bem = json.loads(div.attrs.get('data-bem'))
            urls.add(data_bem['serp-item']['dups'][0]['url'])
    except Exception as e:
        print(e)
    log = time.strftime('[%H:%M:%S - {0} sec in work] | {1} | Find: {2} | page: {3}', time.gmtime())
    print(log.format(int(time.time() - start_name_time), quary, len(urls), page))
    result |= urls


def update_ip(sock):
    print('ip change sig')
    sock.send('signal NEWNYM\r\n'.encode())
    if updating:
        threading.Timer(6, update_ip, [sock]).start()


def main(tor_cmd, data_root_path, thread_count, file_of_people):
    (opener, csock, subproc) = tor_management.start_tor_with_config(tor_cmd, data_root_path)
    update_ip(csock)

    with open(file_of_people) as fpeople:
        names = [line.split('\n')[0] for line in fpeople]

    images = dict().fromkeys(names, set())

    for name in names:
        for page in range(0, MAX_PAGE, thread_count):
            pages = [str(i) for i in range(page, page + thread_count)]
            threads = [threading.Thread(
                target=get_img_from_quary,
                args=(name, p, opener, images[name])) for p in pages]
            for thread in threads:
                thread.start()
            #for thread in threads:
            #    thread.join(6)
            time.sleep(6)
            print('-' * 60)
        with open('Images/' + name + '.txt', 'w') as result:
            result.write('\n'.join(images[name]))


if __name__ == '__main__':
    arguments_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arguments_parser.add_argument('-t', '--tor', help='path to tor executable', type=str, default='tor')
    arguments_parser.add_argument('-d', '--datapath', help='path to folder where Tor instances will store data',
                                  type=str, default='../data')
    arguments_parser.add_argument('-n', '--numthreads', help='number of downloader threads',
                                  type=int, default=1)
    arguments_parser.add_argument('-a', '--actors', help='path to file with actors', type=str, default='actors.txt')
    args = arguments_parser.parse_args()

    main(args.tor, args.datapath, args.numthreads, args.actors)
    global updating
    updating = False
