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

"""Test cases for gbs_actions.py"""

import unittest
import os
import sys
import shutil
import json
from pprint import pprint
import datetime
import signal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.utility.utils import *


class TestUtils(unittest.TestCase):
    """Testing utils.py"""

    test_gbs_param = {}

    def setUp(self):
        """Default fixture"""

    def tearDown(self):
        """Destroy fixture"""

    def test_utils_console(self):
        """Check console"""

        console('Logging this message', level='INFO', verbose=True)
        test_string = 'Forever'
        self.assertEqual(test_string, 'Forever')

    def test_utils_pushd(self):
        """Check pushd"""

        sample_text = 'Hello World'
        sample_filename = 'test.log'
        test_dir = os.path.join(os.getcwd(), 'pushd_test_dir')
        shutil.rmtree(test_dir, ignore_errors=True)
        os.makedirs(test_dir)

        with pushd(test_dir):
            with open(sample_filename, 'w') as test_f:
                test_f.write(sample_text)

        with open(os.path.join(test_dir, sample_filename), 'r') as read_f:
            full_text = read_f.read()
            self.assertEqual(sample_text, full_text)

        shutil.rmtree(test_dir, ignore_errors=True)

    def test_utils_temp_dir_negative(self):
        """Check temporary_directory"""

        sample_text = 'Hello World'
        sample_filename = 'test.log'

        with temporary_directory():
            with open(sample_filename, 'w') as test_f:
                test_f.write(sample_text)
            self.assertEqual(sample_text, 'Hello World')

    def test_utils_serve_web_negative(self):
        """Check web servings"""

        def handler(signum, frame):
            raise Exception("end of time")

        def serve_forever():
            serve_web(8007, os.getcwd())

        test_string = 'Forever'
        self.assertEqual(test_string, 'Forever')
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(2)

        try:
            serve_forever()
        except Exception:
            pass


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
