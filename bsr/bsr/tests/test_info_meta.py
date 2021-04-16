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

"""Test cases for info_meta.py"""

import unittest
import os
import sys
import shutil
import json
from pprint import pprint
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.report.info_meta import gather_meta_information


class TestInfoMeta(unittest.TestCase):
    """Testing info_meta.py"""

    test_build_time = {}


    def setUp(self):
        """Default fixture"""

        TestInfoMeta.test_build_time = {
            'package-a': {'duration': 1116.0,
                        'end': datetime.datetime(2021, 3, 3, 8, 50, 21),
                        'package': 'package-a',
                        'start': datetime.datetime(2021, 3, 3, 8, 31, 45),
                        'status': 'pass',
                        'thread': 'test-server:0',
                        'version': '1.16.0-0'},
            'package-b': {'duration': 2628.0,
                        'end': datetime.datetime(2021, 3, 3, 9, 34, 11),
                        'package': 'package-b',
                        'start': datetime.datetime(2021, 3, 3, 8, 50, 23),
                        'status': 'pass',
                        'thread': 'test-server:0',
                        'version': '1.16.0-0'},
            'package-c': {'duration': 489.0,
                        'end': datetime.datetime(2021, 3, 3, 8, 58, 32),
                        'package': 'package-c',
                        'start': datetime.datetime(2021, 3, 3, 8, 50, 23),
                        'status': 'pass',
                        'thread': 'test-server:1',
                        'version': '1.16.0-0'},
            'package-d': {'duration': 2299.0,
                        'end': datetime.datetime(2021, 3, 3, 10, 12, 33),
                        'package': 'package-d',
                        'start': datetime.datetime(2021, 3, 3, 9, 34, 14),
                        'status': 'pass',
                        'thread': 'test-server:0',
                        'version': '1.16.0-0'}
        }

    def tearDown(self):
        """Destroy fixture"""

        TestInfoMeta.test_build_time = {}

    def test_info_meta(self):
        """Check processing meta information"""

        test_meta = gather_meta_information(TestInfoMeta.test_build_time, {})
        self.assertIn('BuildDetail', test_meta)
        self.assertIn('ReferenceDetail', test_meta)

    def test_meta_keys(self):
        """Check detailed keys exist"""

        test_meta = gather_meta_information(TestInfoMeta.test_build_time, {})
        self.assertEqual(sorted(['Total', 'StartTime', 'EndTime', 'RunTime', 'Pass', 'Fail']), sorted(test_meta['BuildDetail'].keys()))


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
