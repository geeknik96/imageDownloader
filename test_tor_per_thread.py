__author__ = 'lukyanets'

"""Test to run multiple tor instances of tor, one per thread."""

# parsing
import bs4 as bs
import json

# networking
from urllib import parse
from urllib import error as urlerror
import http.client as httpclient

# multithreading
import threading
import queue

# misc
from os import path
import os
import argparse
import time
import enum

# local
import os
import glob
from downloaders import tor_management, get_ip_helpers, simple_logger

request_template = 'https://yandex.ru/images/search?text={0}&p={1}'
update_ip_queue = queue.Queue()
this_file_filepath = path.abspath(path.dirname(__file__))

checking_for_face = 0;

@enum.unique
class PageGetResult(enum.Enum):
    OK = 1
    HTTP404 = 2
    HTTPERROR = 3
    INCOMPLETEREAD = 4


@enum.unique
class PageParseResult(enum.Enum):
    OK = 1
    NORESULTS = 2
    TRYNEXT = 3


class Person:
    def __init__(self, name, date: str='0-0-0', occupation='?', top: str='?', base_image_url: str='?'):
        self.name = name
        if date != '?':
            self.byear, self.bmonth, self.bday = [int(i) for i in date.split('-')]
        else:
            self.byear, self.bmonth, self.bday = 0, 0, 0;
        self.occupation = occupation
        self.top = top
        self.base_image_url = base_image_url


def parse_page(html: str) -> [str]:
    soup = bs.BeautifulSoup(html, 'html.parser')

    divs = soup.find_all('div', class_='serp-item')
    data_bems = [json.loads(div.attrs.get('data-bem')) for div in divs]
    try:
        urls = [db['serp-item']['dups'][0]['url'] for db in data_bems]
        return urls
    except IndexError:
        return []


def get_search_url_for_query(query: str, page: int=0) -> str:
    return request_template.format(parse.quote_plus(query), page)


def get_html_with_opener(opener, url) -> (PageGetResult, str, str):
    for _ in range(5):
        try:
            b = opener.open(url).read()
            html = b.decode('utf-8')
            return PageGetResult.OK, html, ''
        except urlerror.HTTPError as e:
            error = PageGetResult.HTTP404 if e.code == 404 else PageGetResult.HTTPERROR
            return error, '', 'Got HTTPError with message: ' + str(e)
        except httpclient.IncompleteRead:
            continue
        except urlerror.URLError:
            continue
        except Exception:
            continue
    return PageGetResult.INCOMPLETEREAD, '', ''


def get_persons_list(persons_list_filepath, already_download: set,limit=None,  ) -> [Person]:
    with open(persons_list_filepath, encoding='utf-8') as f:
        lines = f.readlines()
        persons = []
        for l in lines:
            if not l:
                continue # зачем?
            name, date, occupation, top, url = [p.strip() for p in l.split('\t')]
            if name in already_download:
                continue
            persons.append(Person(name, date, occupation, top, url))
        if not isinstance(limit, int) or limit <= 0:
            return persons
        else:
            return persons[0:limit]


class Worker(threading.Thread):
    def __init__(self, tid: int, proxy_port: int, control_port: int, persons_to_process: [str], opener, sock,
                 current_ip: str, results: [(str, [str])], logger: simple_logger.SimpleLogger,
                 save_path: str='results'):
        threading.Thread.__init__(self)
        self.tid = tid
        self.logger = logger
        self.proxy_port = proxy_port
        self.control_port = control_port
        self.persons = persons_to_process
        self.opener = opener
        self.sock = sock
        self.results = results
        self.update_ip_lock = threading.Lock()
        self.update_ip_lock.acquire()
        self.current_ip = current_ip
        self.save_path = save_path
        os.makedirs(self.save_path, exist_ok=True)
        self.first_person_downloading = True

    def write_person_urls_to_file(self, name: str, results_for_person: [str]):
        person_filepath = path.normpath(path.join(self.save_path, name + '.txt'))
        with open(person_filepath, 'w+', encoding='utf-8') as person_file:
            for url in results_for_person:
                person_file.write(url + '\n')

    def update_ip_this_thread(self, update_try=1):
        update_ip_queue.put(self.tid)
        self.update_ip_lock.release()
        old_ip = self.current_ip
        new_ip = tor_management.wait_while_ip_updating(self.current_ip, self.opener,
                                                       get_ip_helpers.get_current_ip_httpbin_org)
        self.logger.log(old_ip=old_ip, new_ip=new_ip, update_try=update_try)
        self.update_ip_lock.acquire()

    def process_page(self, url: str) -> (PageParseResult, [str]):
        try_number = 0
        while try_number < 5:
            # give it a chance: let's try from different IPs
            status, html, error_msg = get_html_with_opener(self.opener, url)
            if status is PageGetResult.HTTP404:
                return PageParseResult.NORESULTS, []
            elif status is PageGetResult.HTTPERROR:
                self.logger.log(error_msg)
                continue
            elif status is PageGetResult.OK:
                urls = parse_page(html)
                if urls:
                    return PageParseResult.OK, urls
                else:
                    # we got yandex block, let's try to change IP and repeat
                    self.update_ip_this_thread(update_try=try_number + 1)
                    # IP updated, let's try one more time
                    try_number += 1
                    continue
            elif status is PageGetResult.INCOMPLETEREAD:
                # sometimes we just cannot read page for 5 times in a row, let's try to change IP and retry
                self.update_ip_this_thread(update_try=try_number + 1)
                try_number += 1
                continue
            else:
                try_number += 1
                continue
        # we tried but failed, nothing to do here
        return PageParseResult.TRYNEXT, []

    def process_person(self, person: Person) -> [str]:
        if self.first_person_downloading:
            self.first_person_downloading = False
        else:
            self.update_ip_this_thread()
        result = []
        page_number = 0
        while True:
            status, urls = self.process_page(
                get_search_url_for_query(person.name + ' ' + person.occupation, page_number))

            if status is PageParseResult.OK:
                result += urls
                page_number += 1
                self.logger.log('Got {0} images for {1}'.format(len(result), person.name), occupation=person.occupation,
                                top=person.top)
            elif status is PageParseResult.TRYNEXT:
                self.logger.log(
                    'Tried several times for search page {0} but failed, let\'s try for next page'.format(page_number))
                page_number += 1
            elif status is PageParseResult.NORESULTS:
                self.logger.log(
                    'Got 404 on {0} page of {1} search, going to download next person'.format(page_number, person.name))
                break
            else:
                raise Exception('Unexpected result for image parsing')
        self.write_person_urls_to_file(person.name, result)
        return result

    def run(self):
        number_of_persons_to_process = len(self.persons)
        self.logger.log(
            'Hi from thread # {0} processing {1} person{2}'.format(self.tid, number_of_persons_to_process,
                                                                   '' if number_of_persons_to_process == 1 else 's'))

        for index, person_name in enumerate(self.persons):
            self.logger.update_prefix('{0}/{1}'.format(index + 1, number_of_persons_to_process))
            images_urls = self.process_person(person_name)
            self.results.append((person_name, images_urls))


def start_download(tor: str, datapath: str, numthreads: int, persons_list_filepath: str, results_path: str):
    def chunks(l, n):
        lists = [[] for _ in range(n)]
        for i, item in enumerate(l):
            lists[i % n].append(item)
        return lists

    main_logger = simple_logger.SimpleLogger()

    already_got_links = glob.glob(os.path.join(results_path, '*.txt'))
    get_name = lambda x: os.path.splitext(os.path.basename(x))[0]
    name_got_links = set([get_name(fn) for fn in already_got_links])

    persons_list = get_persons_list(persons_list_filepath, name_got_links)
    numthreads = min(numthreads, len(persons_list))
    main_logger.log(persons=len(persons_list), numthreads=numthreads)
    persons_per_thread = chunks(persons_list, numthreads)
    results = [list() for _ in range(numthreads)]
    threads = []

    for i in range(numthreads):
        proxy_port = 9150 + 2 * i
        control_port = proxy_port + 1
        logger = simple_logger.SimpleLogger('Thread ' + str(i))
        opener, sock, subprocess = tor_management.start_tor_with_config(tor, datapath, proxy_port, control_port,
                                                                        lambda s: logger.log(s))
        current_ip = get_ip_helpers.get_current_ip_httpbin_org(opener=opener)
        thread = Worker(i, proxy_port, control_port, persons_per_thread[i], opener, sock, current_ip, results[i],
                        logger, results_path)
        thread.start()
        threads.append(thread)

    while True:
        threads_finished = all(not thread.is_alive() for thread in threads)
        if threads_finished:
            break
        try:
            tid = update_ip_queue.get(True, 1)
            threads[tid].update_ip_lock.acquire()
            main_logger.log('Updating IP for thread ' + str(tid))
            tor_management.update_ip(threads[tid].current_ip, threads[tid].opener, threads[tid].sock,
                                     get_ip_helpers.get_current_ip_httpbin_org, main_logger.log)
            threads[tid].current_ip = get_ip_helpers.get_current_ip_httpbin_org(opener=threads[tid].opener)
            threads[tid].update_ip_lock.release()
            update_ip_queue.task_done()
        except queue.Empty:
            time.sleep(0.5)
            continue

    for thread in threads:
        thread.join()

    flatten_results = [item for sublist in results for item in sublist]

    for res in flatten_results:
        main_logger.log('Found {0} images for {1}'.format(len(res[1]), res[0]))


if __name__ == '__main__':
    arguments_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arguments_parser.add_argument('-t', '--tor', help='path to tor executable', type=str, default='tor')
    arguments_parser.add_argument('-d', '--datapath', help='path to folder where Tor instances will store data',
                                  type=str, default=path.abspath(path.join(this_file_filepath, '../data')))
    arguments_parser.add_argument('-n', '--numthreads', help='number of downloader threads (and Tor instances)',
                                  type=int, default=1)
    arguments_parser.add_argument('-p', '--persons', help='path to file with persons', type=str,
                                  default=path.abspath(
                                      path.join(this_file_filepath, '../lists/turtleluck_filtered_wo_imdb.txt')))
    arguments_parser.add_argument('-r', '--results_path',
                                  help='path to directory where resulting .txt files will be stored', type=str,
                                  default=path.abspath(path.join(this_file_filepath, '../results/default/')))
    arguments_parser.add_argument('-c', '--check_for_face', help='face detection on url with help online service',
                                  type=int, default=0)
    args = arguments_parser.parse_args()

    global checking_for_face
    checking_for_face = args.check_for_face

    start_download(args.tor, args.datapath, args.numthreads, args.persons, args.results_path)
