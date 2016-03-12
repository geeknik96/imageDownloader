__author__ = 'somenkov'

"""Downloader for images from from file url"""

from threading import Thread as thread
import argparse
import os
import urllib.request
import urllib.parse
import urllib.error
import time
import glob
import imghdr

progress = 0
all_ = 0
miss = 0
start = time.time()
already_downloaded = None
timeout = None
stubbornness = None


def get_img(url):
    global timeout
    global stubbornness
    status = 'Unknown error'
    for _ in range(stubbornness):
        try:
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent',
                      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.107 Safari/537.36')]
            return opener.open(url, timeout=timeout).read()
        except Exception as e:
            status = str(e)
            time.sleep(0.5)
    raise Exception(status)


def download_process(n, urls, ft):
    global progress
    global all_
    global miss
    global already_downloaded
    zero_fill = len(str(all_))
    print('Hi, thread', n, 'count =', len(urls))
    log_template = 'Thread {0}: url {1} success="{2}" loaded: [{3}/{4}({5} miss)], work {6} sec'
    file_log_template = '{0}\t{1}\t{2}\n'
    for line, url in urls:
        success = 'OK'
        try:
            image = get_img(url)
            fmt = imghdr.what(None, image)
            if fmt is None:
                raise Exception('It is not picture')
        except Exception as e:
            success = e
            miss += 1
        else:
            with open(ft.format(str(line).zfill(zero_fill), fmt), 'wb') as file:
                file.write(image)
            progress += 1
        already_downloaded.write(file_log_template.format(line, url,str(success).split('\n')[0]))
        already_downloaded.flush()
        run_time = round(time.time() - start)
        print(log_template.format(n, line, success, progress, all_, miss, run_time))


def main(path, numthreads, download_root):
    global progress
    global all_
    global already_downloaded
    global miss
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        print('Path is not correct!')
        return -1

    files = [fp for fp in glob.glob(os.path.join(path, '*.txt'))]

    for file in sorted(files):
        filename = os.path.basename(file)
        print('Download form', filename)
        name = filename[:filename.rfind('.')]
        with open(file) as file_urls:
            urls = [url[:-1] for url in file_urls]
        name = name.replace(' ', '_')
        dpath = os.path.join(download_root, name)
        os.makedirs(dpath, exist_ok=True)
        fn_template = os.path.join(dpath, name) + '_{0}.{1}'

        dict_urls = { url: len(urls) - i for i, url in enumerate(urls[::-1], 1) }
        urls = [key_val[::-1] for key_val in dict_urls.items()]

        open(fn_template.format('downloaded', 'txt'), 'a').close()

        downloaded = []
        with open(fn_template.format('downloaded', 'txt')) as dfile:
            for line in dfile:
                info = line[:-1].split('\t')
                downloaded.append((int(info[0]), info[1]))

        already_downloaded = open(fn_template.format('downloaded', 'txt'), 'a')

        urls = list(set(urls) - set(downloaded))
        urls.sort(key=lambda x: x[0])
        progress, miss, all_ = 0, 0, len(urls)

        step = round(len(urls) / numthreads)
        if step == 0: continue
        ranges = [(a, a + step) for a in range(0, len(urls), step)]
        threads = []
        for i, (a, b) in enumerate(ranges):
            arg = (i, urls[a:b], fn_template)
            t = thread(target=download_process, args=arg)
            threads.append(t)
            t.start()
        for t in threads: t.join()
        already_downloaded.close()


if __name__ == '__main__':
    arguments_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arguments_parser.add_argument('-p', '--path', help='path with files with urls', type=str, default='.')
    arguments_parser.add_argument('-n', '--threads', help='count of threads', type=int, default=1)
    arguments_parser.add_argument('-s', '--stubbornness', help='count of attempts', type=int, default=1)
    arguments_parser.add_argument('-t', '--timeout', help='timeout for urllib', type=int, default=4)
    arguments_parser.add_argument('-d', '--downloaddir', help='directory where downloads will be stored', type=str)

    args = arguments_parser.parse_args()

    stubbornness = args.stubbornness
    timeout = args.timeout

    main(args.path, args.threads, args.downloaddir)
