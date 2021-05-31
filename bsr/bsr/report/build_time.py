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

"""Parse build log files"""

import os
import sys
import re
import json
import shutil
import subprocess

from datetime import datetime

from bsr.utility.utils import pushd, extract_ip_address_port_path, str_to_date, console


class BuildTime:
    """Build Time"""

    verbose = False
    arch = None
    build_time = {}
    ref_build_time = {}
    profile_ref = None

    rxs = r'.*\].* (.*) .*started.*build (.*).spec.* at (.*).$'
    rxe = r'.*\].* (.*) (finished|failed).*build (.*).spec.* at (.*).$'
    rxc = r'.*Using BUILD_ROOT=.*[_.]([\d]+)'
    rxp = r'.* processing recipe .*/(.*)-([0-9a-zA-Z.+]+-[0-9.]+)/.*.spec .*'

    # pylint: disable=R0913
    def __init__(self, local_log_dir=None, reference_url=None, profile_ref=None, \
                 logtype=None, arch=None, verbose=False):
        """Initialize"""

        self.verbose = verbose
        self.arch = arch
        if logtype:
            self.switch_regex_patterns(logtype)

        self.build_time = self.process_local(local_log_dir)
        self.ref_build_time = self.process_reference(reference_url, profile_ref)

    def process_local(self, local_path):
        """Parse all the log files from local"""

        build_time = {}

        if local_path is None:
            return build_time

        # pylint: disable=W0703,W0612
        for log_type in ['GBS', 'OBS']:
            self.switch_regex_patterns(log_type)
            for item in self.get_all_files(local_path):
                try:
                    thread, package, start, end, build_status, release_version \
                        = self.parse_logfile(item)
                    build_time[package] = {
                        'thread': thread,
                        'package': package,
                        'version': release_version,
                        'status': build_status,
                        'start': start,
                        'end': end,
                        'duration': ((end - start).total_seconds())
                    }
                except Exception as err:
                    pass
            if len(build_time) > 1:
                break

        console(' + We have {} build time data'.format(len(build_time)), \
                verbose=self.verbose)

        return build_time

    def process_profile_ref(self, url):
        """Directly get the data from the previous profiling report"""

        src_filename = 'buildtime.json'
        if not url.endswith('/'):
            url = url + '/'
        url = url + 'sample_data/datasets/default/{}'.format(src_filename)

        console('Downloading build time data from the previous report... {}'.format(url), \
                verbose=self.verbose)

        ar_files = '-R index.htm* -A "{}"'.format(src_filename)
        options = 'wget -q -nH -np '
        output_filename = '.prev.rpt.{}'.format(src_filename)
        main_command = '{} {} {} -O {}'.format(options, ar_files, url, output_filename)
        ret = subprocess.call('{}'.format(main_command), \
                              stdout=sys.stdout, stderr=sys.stderr, shell=True)
        console('Download finished with {}'.format(ret), verbose=self.verbose)
        prev_data = {}
        if os.path.exists(output_filename):
            try:
                with open(output_filename, 'r') as prev_f:
                    prev_data = json.load(prev_f)
            except ValueError:
                prev_data = {}
            try:
                for pkg_name in prev_data:
                    prev_data[pkg_name]['end'] = datetime.strptime( \
                        prev_data[pkg_name]['end'], '%Y-%m-%d %H:%M:%S')
                    prev_data[pkg_name]['start'] = datetime.strptime( \
                        prev_data[pkg_name]['start'], '%Y-%m-%d %H:%M:%S')
            except KeyError:
                prev_data = {}
            console('Ref build time data... {}'.format(len(prev_data)), verbose=self.verbose)
            os.remove(output_filename)

        return prev_data

    def process_reference(self, remote_url=None, profile_ref=None):
        """Parse all the log files from reference"""

        if profile_ref is not None:
            return self.process_profile_ref(profile_ref)

        build_time = {}

        if remote_url is None:
            return build_time

        # Get logs from remote
        url, _, _ = extract_ip_address_port_path(remote_url)
        if url is not None:
            local_path = self.get_buildlogs_from_url(remote_url)
            build_time = self.process_local(local_path)
            shutil.rmtree(local_path, ignore_errors=True)
        elif os.path.exists(os.path.abspath(remote_url)):
            build_time = self.process_local(os.path.abspath(remote_url))

        console('Reference build time data: {}'.format(len(build_time)), \
                verbose=self.verbose)

        return build_time

    def get_all_files(self, local_path):
        """Find all text files"""

        candidates = []

        if os.path.isfile(local_path):
            candidates.append(local_path)
            return candidates

        if not os.path.isdir(local_path):
            return candidates

        for root, _, files in os.walk(local_path):
            for fname in files:
                if '/buildlogs/' in root:
                    if self.arch and '/{}/'.format(self.arch) not in root:
                        continue
                if fname.endswith('.txt'):
                    candidates.append(os.path.join(root, fname))

        console('Total {} files stacked...'.format(len(candidates)), verbose=self.verbose)
        return candidates

    def get_buildlogs_from_url(self, url):
        """Wget log files from url"""

        def check_builddata_root(url):
            # Check upper directory if this is not the snapshot root directory
            if '/repos/' in url:
                _url = url.split('/repos/')[0] + '/'
                main_command = 'wget -q --no-proxy {}/'.format(_url)
                subprocess.call('{}'.format(main_command), \
                                stdout=sys.stdout, stderr=sys.stderr, shell=True)
                if os.path.isfile('index.html'):
                    with open('index.html', 'r') as index_f:
                        if 'builddata' in index_f.read():
                            return _url
            return url

        if not url.endswith('/'):
            url = url + '/'

        console('Downloading log files from the url... {}'.format(url), \
                verbose=self.verbose)
        work_dir = os.path.join(os.getcwd(), \
                                '.snap_logs_{}'.format(datetime.now().strftime('%Y%m%d%H%M%S')))
        shutil.rmtree(work_dir, ignore_errors=True)
        os.makedirs(work_dir)

        with pushd(work_dir):
            _url = check_builddata_root(url)
            ar_files = '-R index.htm* -A "*.txt"'
            options = 'wget -q -r -nH -np -l 10 '
            main_command = '{} {} {}/'.format(options, ar_files, _url)
            ret = subprocess.call('{}'.format(main_command), \
                                  stdout=sys.stdout, stderr=sys.stderr, shell=True)
        console('Download finished with {}'.format(ret), verbose=self.verbose)

        return work_dir

    def switch_regex_patterns(self, log_type=None):
        """Different regex between OBS and GBS"""

        if log_type is None:
            if 'gbs' in self.rxp:
                log_type = 'GBS'
            else:
                log_type = 'OBS'

        if log_type == 'OBS':
            self.rxp = r'.* processing recipe .*/.*gbs:(.*).spec .*'
            self.rxs = r'.*\].* (.*) .*started.*:gbs:(.*).spec.* at (.*).$'
            self.rxe = r'.*\].* (.*) (finished|failed) (.*).spec.* at (.*).$'
        elif log_type == 'GBS':
            self.rxs = r'.*\].* (.*) .*started.*build (.*).spec.* at (.*).$'
            self.rxe = r'.*\].* (.*) (finished|failed).*build (.*).spec.* at (.*).$'
            self.rxp = r'.* processing recipe .*/(.*)-([0-9a-zA-Z.+]+-[0-9.]+)/.*.spec .*'

    def parse_logfile(self, logfile):
        """Parsing log file"""

        with open(logfile, 'r') as log_f:
            dump = log_f.readlines()
            hostname = None
            package = None
            start = None
            end = None
            thread = None
            build_result = None
            release_version = None

            for line in dump[0:20]:
                # Thread first
                if not thread:
                    item = re.search(self.rxc, line)
                    if item:
                        thread = item.groups()[0]
                        continue

                # Start time
                if thread and not hostname:
                    item = re.search(self.rxs, line)
                    if item:
                        hostname, _, start = item.groups()
                        continue

                # Package name
                item = re.search(self.rxp, line)
                if item and len(item.groups()) == 2:
                    package, release_version = item.groups()

            for line in dump[-10:-1]:
                item = re.search(self.rxe, line)
                if item and len(item.groups()) == 4:
                    end = item.groups()[3]
                    if item.groups()[1] == 'failed':
                        build_result = 'fail'
                    elif item.groups()[1] == 'finished':
                        build_result = 'pass'
                    break
            if hostname and package and start and end and thread:
                thread_no = '{}:{}'.format(hostname, str(thread))
                return thread_no, package, str_to_date(start, 9), str_to_date(end, 9), \
                       build_result, release_version

        return None, None, None, None, None, None
