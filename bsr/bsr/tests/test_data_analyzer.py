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

"""Test cases for data_analyzer.py"""

import unittest
import os
import sys
from pprint import pprint

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.analyzer.data_analyzer import DataAnalyzer


class TestDataAnalyzer(unittest.TestCase):
    """Testing data_analyzer.py"""

    xml_inst = None

    def setUp(self):
        """Default fixture"""

        class SampleXml:
            package_names = ['a', 'b', 'c']
            nodes = [0, 1, 2]
            edges = {0: [1, 2], 1: [], 2: []}
            in_degree = [0, 1, 1]

        TestDataAnalyzer.xml_inst = SampleXml()

    def tearDown(self):
        """Destroy fixture"""

        del TestDataAnalyzer.xml_inst

    def test_analyzer(self):
        """Check input parameters"""

        d = DataAnalyzer(TestDataAnalyzer.xml_inst)
        self.assertEqual(d.package_names, TestDataAnalyzer.xml_inst.package_names)
        self.assertEqual(d.nodes, TestDataAnalyzer.xml_inst.nodes)
        self.assertEqual(d.edges, TestDataAnalyzer.xml_inst.edges)
        self.assertEqual(d.in_degree, TestDataAnalyzer.xml_inst.in_degree)

if __name__ == '__main__':
    """Entry point"""

    unittest.main()
