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
import time
from pprint import pprint
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.report.info_meta import gather_meta_information, reconstruct_new_format
from bsr.utility.monitoring import Monitoring
from bsr.utility.utils import json_datetime_serializer


class TestInfoMeta(unittest.TestCase):
    """Testing info_meta.py"""

    test_build_time = {}
    local_repo_dir = None

    def setUp(self):
        """Default fixture"""

        TestInfoMeta.test_build_time = {
            'package-a': {
                'duration': 1116.0,
                'end': datetime.datetime(2021, 3, 3, 8, 50, 21),
                'package': 'package-a',
                'start': datetime.datetime(2021, 3, 3, 8, 31, 45),
                'status': 'pass',
                'thread': 'test-server:0',
                'version': '1.16.0-0'
            },
            'package-b': {
                'duration': 2628.0,
                'end': datetime.datetime(2021, 3, 3, 9, 34, 11),
                'package': 'package-b',
                'start': datetime.datetime(2021, 3, 3, 8, 50, 23),
                'status': 'pass',
                'thread': 'test-server:0',
                'version': '1.16.0-0'
            },
            'package-c': {
                'duration': 489.0,
                'end': datetime.datetime(2021, 3, 3, 8, 58, 32),
                'package': 'package-c',
                'start': datetime.datetime(2021, 3, 3, 8, 50, 23),
                'status': 'pass',
                'thread': 'test-server:1',
                'version': '1.16.0-0'
            },
            'package-d': {
                'duration': 2299.0,
                'end': datetime.datetime(2021, 3, 3, 10, 12, 33),
                'package': 'package-d',
                'start': datetime.datetime(2021, 3, 3, 9, 34, 14),
                'status': 'pass',
                'thread': 'test-server:0',
                'version': '1.16.0-0'
            }
        }

        TestInfoMeta.local_repo_dir = os.path.join(os.getcwd(), 'test_build_logs')
        gbs_repo_dir = os.path.join(TestInfoMeta.local_repo_dir, \
                                    'local', 'repos', 'tizen', 'armv7l')
        shutil.rmtree(gbs_repo_dir, ignore_errors=True)
        os.makedirs(gbs_repo_dir)
        report_d = {
                    "summary": {
                                "packages_total": 4,
                                "packages_export_error": 0,
                                "packages_expansion_error": 0,
                                "packages_build_error": 0,
                                "packages_succeeded": "4"
                               }
                    }

        TestInfoMeta.sample_dir = os.path.join(os.getcwd(), 'sample_data')
        shutil.rmtree(TestInfoMeta.sample_dir, ignore_errors=True)
        os.makedirs(os.path.join(TestInfoMeta.sample_dir, 'depends'))
        os.makedirs(os.path.join(TestInfoMeta.sample_dir, 'datasets'))

        with open(os.path.join(gbs_repo_dir, 'report.json'), 'w') as log_file:
            json.dump(report_d, log_file, default=json_datetime_serializer)

    def tearDown(self):
        """Destroy fixture"""

        TestInfoMeta.test_build_time = {}
        TestInfoMeta.local_repo_dir = None

    def test_info_meta(self):
        """Check processing meta information"""

        test_meta = gather_meta_information(None, TestInfoMeta.test_build_time, {})
        self.assertIn('BuildDetail', test_meta)
        self.assertIn('ReferenceDetail', test_meta)

    def test_info_meta_keys(self):
        """Check detailed keys exist"""

        test_meta = gather_meta_information(None, TestInfoMeta.test_build_time, {})
        self.assertEqual(sorted(['Total', 'StartTime', 'EndTime', 'RunTime', 'Pass', 'Fail']),
                         sorted(test_meta['BuildDetail'].keys()))


    def test_info_meta_keys_with_local_repo_negative(self):
        """Check from local repos"""

        test_meta = gather_meta_information(TestInfoMeta.local_repo_dir, \
                                            TestInfoMeta.test_build_time, \
                                            TestInfoMeta.test_build_time)
        self.assertEqual(sorted(['Total', 'StartTime', 'EndTime', 'RunTime', 'Pass', 'Fail']),
                         sorted(test_meta['BuildDetail'].keys()))


    def test_info_meta_reconstruct_negative(self):
        """Check reconstruct"""

        Monitoring().start_recording(os.path.join(os.getcwd(), 'cpu.records'))
        time.sleep(2)
        Monitoring().stop_recording_without_cleanup(os.path.join(os.getcwd(), 'cpu.records'))
        test_meta = gather_meta_information(None, TestInfoMeta.test_build_time, {})
        reconstruct_new_format(TestInfoMeta.sample_dir , os.path.join(os.getcwd(), 'cpu.records'))

        test_meta = gather_meta_information(None, TestInfoMeta.test_build_time, {})
        self.assertIn('BuildDetail', test_meta)


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
