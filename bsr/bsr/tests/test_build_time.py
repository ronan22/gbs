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

"""Test cases for build_time.py"""

import unittest
import os
import sys
import shutil
import json
from pprint import pprint
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.report.build_time import BuildTime


class TestBuildTime(unittest.TestCase):
    """Testing build_time.py"""

    local_log_dir = None
    test_packages = {
        'package-a': {'start_time': 'Mon Mar 2 23:31:45 UTC 2021', 'end_time': 'Mon Mar 2 23:50:21 UTC 2021', 'thread_no': 0},
        'package-b': {'start_time': 'Mon Mar 2 23:50:23 UTC 2021', 'end_time': 'Tue Mar 3 00:34:11 UTC 2021', 'thread_no': 0},
        'package-c': {'start_time': 'Mon Mar 2 23:50:23 UTC 2021', 'end_time': 'Mon Mar 2 23:58:32 UTC 2021', 'thread_no': 1},
        'package-d': {'start_time': 'Tue Mar 3 00:34:14 UTC 2021', 'end_time': 'Tue Mar 3 01:12:33 UTC 2021', 'thread_no': 0},
    }
    logfile_template = '''[    0s] Memory limit set to 17263388KB
[    0s] Using BUILD_ROOT=/home/test/GBS-test/local/BUILD-ROOTS/scratch.armv7l.{}
[    0s] test-server started "build {}.spec" at {}.
[    0s] processing recipe /home/test/GBS-test/local/sources/test_target/{}-1.16.0-0/{}.spec ...
[    2s] expanding package dependencies...
[  123s] make[1]: Leaving directory /home/abuild/rpmbuild/BUILD/{}-1.16.0-0
[  124s] + exit 0
[  125s] test-server finished "build {}.spec" at {}.
[  126s]'''


    def setUp(self):
        """Default fixture"""

        TestBuildTime.local_log_dir = os.path.join(os.getcwd(), 'test_build_logs')
        gbs_log_dir = os.path.join(TestBuildTime.local_log_dir, 'local', 'repos', 'tizen', 'armv7l', 'logs')
        os.makedirs(gbs_log_dir)

        for package_name in TestBuildTime.test_packages:
            with open(os.path.join(gbs_log_dir, '{}.txt'.format(package_name)), 'w') as log_file:
                log_file.write(TestBuildTime.logfile_template.format( \
                        TestBuildTime.test_packages[package_name]['thread_no'], \
                        package_name, \
                        TestBuildTime.test_packages[package_name]['start_time'], \
                        package_name, \
                        package_name, \
                        package_name, \
                        package_name, \
                        TestBuildTime.test_packages[package_name]['end_time'] \
                        ))

    def tearDown(self):
        """Destroy fixture"""

        shutil.rmtree(TestBuildTime.local_log_dir, ignore_errors=True)

        TestBuildTime.local_log_dir = None

    def test_search_logfile(self):
        """Check finding log files"""

        b = BuildTime(local_log_dir=TestBuildTime.local_log_dir, verbose=True)
        self.assertNotEqual(len(b.build_time), 0)
        self.assertTrue(len(b.build_time) == len(TestBuildTime.test_packages))

    def test_all_packages_processed(self):
        """Check parsed packages"""

        b = BuildTime(local_log_dir=TestBuildTime.local_log_dir, verbose=True)
        for package_name in TestBuildTime.test_packages:
            self.assertIn(package_name, b.build_time)
            self.assertEqual(sorted(['package', 'start', 'end', 'duration', 'status', 'thread', 'version']), \
                             sorted(b.build_time['package-c'].keys()))

    def test_detail_build_time_info(self):
        """Check detailed information"""

        b = BuildTime(local_log_dir=TestBuildTime.local_log_dir, verbose=True)
        self.assertEqual(datetime.datetime(2021, 3, 3, 8, 50, 23), b.build_time['package-b']['start'])
        self.assertEqual(datetime.datetime(2021, 3, 3, 9, 34, 11), b.build_time['package-b']['end'])
        self.assertEqual('package-b', b.build_time['package-b']['package'])
        self.assertEqual('test-server:0', b.build_time['package-b']['thread'])
        self.assertEqual('1.16.0-0', b.build_time['package-b']['version'])
        self.assertEqual('pass', b.build_time['package-b']['status'])
        self.assertEqual(2628, int(b.build_time['package-b']['duration']))


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
