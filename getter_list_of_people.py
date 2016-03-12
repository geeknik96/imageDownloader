__author__ = 'somenkov'


from urllib import request as req
from downloaders import tor_management
import bs4


def get_job_list():

    pass


def main(opener):
    url = 'http://www.turtleluck.com/famous-people/#'
    data = 'Page={0}'
    f = open('../lists/turtleluck2.txt', 'w')
    for page in range(1, 1000):
        f.flush()
        try:
            html = req.urlopen(url, data=data.format(page).encode(), timeout=10)
            soup = bs4.BeautifulSoup(html, 'html.parser')
            for line in soup.find_all('tr'):
                info = line.text.split('\n')[2:5]
                f.write('\t'.join(info))
                f.write('\n')
                print(info)
        except Exception as e:
            print(e)
            f.close()
            return
    f.close()




if __name__ == '__main__':
    opener, cport, proc = tor_management.start_tor_with_config('C:/Tor/tor')
    main(opener)