__author__ = 'lukyanets'

import argparse
import os
from os import path
import shutil


def remove_whitespaces(f: str):
    return f.replace(' ', '_')


if __name__ == '__main__':
    arguments_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arguments_parser.add_argument('-r', '--root', help='path to folder which subfolders will be renamed', type=str)
    args = arguments_parser.parse_args()
    global_root = path.abspath(args.root)
    walk = os.walk(global_root, topdown=False)
    for root, dirs, files in walk:
        for fd in files + dirs:
            fd_wo_whitespaces = remove_whitespaces(fd)
            orig_path = path.join(root, fd)
            dst_path = path.join(root, fd_wo_whitespaces)
            if path.isdir(orig_path):
                print("Renaming " + fd + " to " + fd_wo_whitespaces)
            shutil.move(orig_path, dst_path)
