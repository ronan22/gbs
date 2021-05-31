#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Samsung Electronics.Co.Ltd.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2 of the License
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""This script is used to provide usefull functions"""

import os
import sys
import re
import time
import contextlib
import subprocess
import threading
import fnmatch
import tempfile
import shutil
import socket

try:
    import http.server
    import socketserver
except ImportError:
    import SimpleHTTPServer
    import SocketServer

from datetime import datetime, timedelta


def console(text, level='INFO', verbose=False):
    """logging wrapper"""
    if verbose is True:
        print('[{}] {}'.format(level, text))
        sys.stdout.flush()


@contextlib.contextmanager
def pushd(new_dir):
    """Wrapper for chdir with auto close with"""

    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)


@contextlib.contextmanager
def temporary_directory(prefix=None):
    """Create temporary directory and delete after use"""

    name = tempfile.mkdtemp(dir=prefix)
    try:
        yield name
    finally:
        shutil.rmtree(name)


def rsync(source, destination):
    """ sync srouce to destination, support local filesystem,
        ssh and rsync protocol.
        Note: access to destination server must be use key authentication
              or anonymous
    """

    # Through rsync protocol
    if destination.startswith('rsync:'):

        # Cut trailing slash due to error (attempt to hack rsync failed)
        if os.path.isdir(source):
            if source.endswith("/"):
                source = source[:-1]
            source = "%s/*" % source

        cmd = "rsync -av --delay-updates %s %s" % (source, destination)
        ret_code = subprocess.call(cmd, shell=True)

        return ret_code

    return None


def extract_ip_address_port_path(url):
    """Find IP address, Port number and it's url path"""

    host = None
    port = None
    path = None

    try:
        host, port, path = re.search( \
            r'(http.*://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:[0-9]+)?/(.*)', \
            url).groups()
        if port and ':' in port:
            port = port.replace(':', '')
    except AttributeError:
        try:
            host_prefix, full_path = re.search(r'(http.*)://(.*)', url).groups()
            host = full_path.split('/')[0]
            path = '/'.join(full_path.split('/')[1:])
            if ':' in host:
                host, port = host.split(':')
            host = '{}://{}'.format(host_prefix, host)
        except AttributeError:
            pass

    return host, port, path


def worker_executor(worker_f, th_result, sem, args):
    """Execute user function inside thread"""

    sem.acquire()

    ret = worker_f(args)
    if ret != 0:
        th_result.append('WORKER_THREAD - error: {}'.format(ret))

    sem.release()


def thread_process(tasks, num_threads=8):
    """Create threads and run
    @tasks: [{'worker': user_callback_function,
              'key1': val1, 'key2': val2}]
    @num_threads: Number of threads for parallel processing
    """

    sem = threading.Semaphore(num_threads)

    th_result = []
    threads = []
    for data in tasks:
        space = threading.Thread(target=worker_executor, \
                                 args=(data.get('worker'), th_result, sem, data))
        threads.append(space)
    for space in threads:
        space.start()
    for space in threads:
        space.join()

    if th_result:
        return 1

    return 0


def str_to_date(time_str, tz_hours=0):
    """Convert string to datetime"""

    unit_date = datetime.strptime(time_str, '%a %b %d %H:%M:%S %Z %Y')
    return unit_date + timedelta(hours=tz_hours)


def date_to_str(date_obj):
    """Convert datetime to formatted string"""

    return datetime.strftime(date_obj, '%Y-%m-%d %H:%M:%S')


def to_timestamp(date_inst):
    """Date to timestamp integer"""

    return int(time.mktime(date_inst.timetuple()))


def list_all_directories(url, fname_match='*'):
    """Retrieve all directories from url or local"""

    def get_files(source_dir, fn_match):
        """Get file list"""
        matches = []
        for root, _, filenames in os.walk(source_dir):
            for filename in fnmatch.filter(filenames, fn_match):
                if os.path.join(root, filename) not in matches:
                    matches.append(os.path.join(root, filename))
        return matches

    if url.startswith('http'):
        mediate_list = []
        with temporary_directory(prefix=os.getcwd()) as tmp_f:
            with pushd(tmp_f):
                ar_files = '-R index.htm* -A "repomd.xml"'
                options = 'wget -q -r -nH -np -l 10'
                main_command = '{} {} {}/'.format(options, ar_files, url)
                subprocess.call('{}'.format(main_command), \
                                stdout=sys.stdout, stderr=sys.stderr, shell=True)
            _, _, path = extract_ip_address_port_path(url)
            for item in get_files(tmp_f, fname_match):
                mediate_list.append(item.replace(tmp_f + '/', url.replace(path, '')))
            return mediate_list
    elif os.path.isdir(url):
        return get_files(url, fname_match)

    return []


def json_datetime_serializer(value):
    """JSON datetime serializer for stroing json data into file"""

    if isinstance(value, (int, str)):
        return value
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError('not JSON serializable')


def get_ip_address():
    """Retrieve IPv4 address"""

    address_list = socket.gethostbyname_ex(socket.gethostname())[-1]
    for ip_addr in address_list:
        if ip_addr.split('.')[0] in ['127', '168', '255']:
            continue
        if ip_addr.endswith('.0.1'):
            continue
        # Return first matching address
        return ip_addr

    return '127.0.0.1'


def serve_web(port, root_dir):
    """Simple http server"""

    console('\n\n{}\n'.format('*' * 20), verbose=True)
    console('Report will be served here: http://{}:{}'.format(
        get_ip_address(), port), verbose=True)

    with pushd(root_dir):
        try:
            handler = http.server.SimpleHTTPRequestHandler
            httpd = socketserver.TCPServer(("", port), handler)
        except NameError:
            handler = SimpleHTTPServer.SimpleHTTPRequestHandler
            handler.extensions_map.update({'.webapp': 'application/x-web-app-manifest+json'})
            httpd = SocketServer.TCPServer(("", port), handler)
        httpd.allow_reuse_address = True
        httpd.serve_forever()
