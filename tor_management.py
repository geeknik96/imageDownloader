__author__ = 'lukyanets'

from urllib import request
import socks
import sockshandler
import os
from os import path
import stem.process
import stem.control
import subprocess
import socket
import time

# unset system proxy settings if any
original_proxies = {'http_proxy': os.environ.get('http_proxy', ''),
                    'https_proxy': os.environ.get('https_proxy', ''),
                    'ftp_proxy': os.environ.get('ftp_proxy', '')}
no_proxies = {'http_proxy': '',
              'https_proxy': '',
              'ftp_proxy': ''}
stc_proxies = {'http_proxy': 'proxy.stc:3128',
               'https_proxy': 'proxy.stc:3128',
               'ftp_proxy': 'proxy.stc:3128'}
os.environ.update(no_proxies)


def get_opener_for_proxy_port(port=9150):
    """Function for getting opener with given port.
    Using:
    get_opener_for_proxy_port(9150).open('https://ya.ru/')

    :param port: port number
    :return: opener
    """
    op = request.build_opener(sockshandler.SocksiPyHandler(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', port))
    op.addheaders = [('User-Agent',
                      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.107 Safari/537.36')]
    return op


def start_tor_with_config(tor_cmd: str='tor',
                          data_root_path: str='./',
                          proxy_port: int=9150,
                          control_port: int=9151,
                          init_msg_handler=lambda x: print(x)) \
        -> (request.OpenerDirector, socket.socket, subprocess.Popen):
    data_path = path.join(data_root_path, 'data_' + str(proxy_port))
    os.makedirs(data_path, exist_ok=True)
    process = stem.process.launch_tor_with_config(config={'SOCKSPort': str(proxy_port),
                                                          'ControlPort': str(control_port),
                                                          'HTTPProxy': stc_proxies['http_proxy'],
                                                          'HTTPSProxy': stc_proxies['https_proxy'],
                                                          'ReachableAddresses': ['*:80', '*:443'],
                                                          'DataDirectory': data_path},
                                                  tor_cmd=tor_cmd,
                                                  completion_percent=100,
                                                  init_msg_handler=init_msg_handler,
                                                  take_ownership=True)
    # setting control port
    control_sock = socket.socket()
    control_sock.connect(('localhost', control_port))
    control_sock.send(('AUTHENTICATE "{0}"\r\n'.format('NONE')).encode())

    opener = get_opener_for_proxy_port(proxy_port)

    return opener, control_sock, process


def wait_while_ip_updating(old_ip: str, opener, ip_getter) -> str:
    updated_ip = old_ip
    it = 0
    while old_ip == updated_ip:
        # TODO: add verbosity levels
        # print('Waited for IP got updated ' + str(it) + ' times (in thread ' + threading.current_thread().name + ')')
        it += 1
        try:
            updated_ip = ip_getter(opener=opener)
        except:
            # proxy seems to rebooting or smth like this, just wait
            time.sleep(2)
    # print('IP updated')
    return updated_ip


def update_ip(old_ip: str, opener, sock, ip_getter, log=lambda x: print(x)):
    sock.send('signal NEWNYM\r\n'.encode())
    log('Signal sent')
    wait_while_ip_updating(old_ip, opener, ip_getter)
