__author__ = 'lukyanets'

from downloaders import tor_management
import json
from bs4 import BeautifulSoup
from urllib import request
import os

def get_req_through_stc_proxy(addr: str):
    os.environ.update(tor_management.stc_proxies)
    req = request.urlopen(addr)
    os.environ.update(tor_management.no_proxies)
    return req

def get_current_ip_checkip_dyn_com() -> str:
    """
    Get ip address using http://checkip.dyn.com/
    :return: str with public IP
    """
    html = get_req_through_stc_proxy('http://checkip.dyn.com').read()
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find("body").text.split(' ')[-1]

def get_current_ip_json(addr, port=None, field='ip', opener=None):
    if opener is not None:
        req = opener.open(addr)
    elif port is not None:
        req = tor_management.get_opener_for_proxy_port(port).open(addr)
    else:
        req = get_req_through_stc_proxy(addr)

    return json.loads(req.read().decode('utf-8'))[field].split(' ')[-1]


def get_current_ip_jsonip_com(port=None, opener=None) -> str:
    """
    Get ip address using http://jsonip.com/
    :return: str with public IP
    """
    addr = 'http://jsonip.com'
    return get_current_ip_json(addr, port, 'ip', opener)

def get_current_ip_httpbin_org(port=None, opener=None) -> str:
    """
    Get ip address using http://httpbin.org/
    :return: str with public IP
    """
    addr = 'http://httpbin.org/ip'
    return get_current_ip_json(addr, port, 'origin', opener)

def get_current_ip_ipify_org(port=None, opener=None) -> str:
    """
    Get ip address using https://www.ipify.org/
    :return: str with public IP
    """
    addr = 'https://api.ipify.org?format=json'
    return get_current_ip_json(addr, port, 'ip', opener)
