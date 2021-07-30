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
from datetime import datetime 

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.analyzer.data_analyzer import DataAnalyzer
from bsr.utility.utils import str_to_date


class TestDataAnalyzer(unittest.TestCase):
    """Testing data_analyzer.py"""

    xml_inst = None

    def setUp(self):
        """Default fixture"""

        class SampleXml:
            """Sample XML"""

            package_names = None
            build_time = None

            def __init__(self):
               """Default init function"""

               self.package_names = []
               self.build_time = {}

               self.package_names = ['a', 'chromium-efl', 'k']
               self.nodes = [0, 1, 2]
               self.edges = {0: [1, 2], 1: [], 2: []}
               self.in_degree = [0, 1, 1]
               self.topology_sorted = [[0], [1, 2]]
               self.chromium = ['a', 'chromium-efl']
               self.top_without_zero = ['a']
               self.zero_links = ['chromium-efl', 'k']
               self.links = {'edges_full': {0: [1, 2], 1: [], 2: []},
                             'links': [{'level': 0, 'links': 2, 'y': 0},
                                       {'level': 1, 'links': 0, 'y': 0},
                                       {'level': 1, 'links': 0, 'y': 1}],
                             'nodes': [0, 1, 2],
                             'package_names': ['a', 'chromium-efl', 'k']}
               self.max_depth = ['a', 'k']

               self.build_time = {
                   'a': {
                         'package': 'a',
                         'status': 'pass', 
                         'start': datetime.strptime('2021-02-15 03:35:50', '%Y-%m-%d %H:%M:%S'),
                         'end': datetime.strptime('2021-02-15 03:36:19', '%Y-%m-%d %H:%M:%S'),
                         'thread': 'thread:01',
                         'version': '1.1.0-0',
                         'duration': 29.0
                        },
                   'chromium-efl': {
                         'package': 'chromium-efl',
                         'status': 'pass', 
                         'start': datetime.strptime('2021-02-15 03:35:51', '%Y-%m-%d %H:%M:%S'),
                         'end': datetime.strptime('2021-02-15 03:37:21', '%Y-%m-%d %H:%M:%S'),
                         'thread': 'thread:02',
                         'version': '1.1.0-0',
                         'duration': 90.0
                        },
                   'k': {
                         'package': 'k',
                         'status': 'pass', 
                         'start': datetime.strptime('2021-02-15 03:36:23', '%Y-%m-%d %H:%M:%S'),
                         'end': datetime.strptime('2021-02-15 03:38:23', '%Y-%m-%d %H:%M:%S'),
                         'thread': 'thread:01',
                         'version': '1.1.0-0',
                         'duration': 120.0
                        }
               }


        TestDataAnalyzer.xml_inst = SampleXml()


    def tearDown(self):
        """Destroy fixture"""

        del TestDataAnalyzer.xml_inst

    def test_analyzer(self):
        """Check input parameters"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst)
        self.assertEqual(d.package_names, TestDataAnalyzer.xml_inst.package_names)
        self.assertEqual(d.nodes, TestDataAnalyzer.xml_inst.nodes)
        self.assertEqual(d.edges, TestDataAnalyzer.xml_inst.edges)
        self.assertEqual(d.in_degree, TestDataAnalyzer.xml_inst.in_degree)

    def test_analyzer_with_buildtime(self):
        """Check with build time"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst, \
                         build_time=TestDataAnalyzer.xml_inst.build_time)
        self.assertEqual(d.package_names, TestDataAnalyzer.xml_inst.package_names)
        self.assertEqual(d.nodes, TestDataAnalyzer.xml_inst.nodes)
        self.assertEqual(d.edges, TestDataAnalyzer.xml_inst.edges)
        self.assertEqual(d.in_degree, TestDataAnalyzer.xml_inst.in_degree)

    def test_analyzer_without_xml(self):
        """Check withhout xml"""

        d = DataAnalyzer(build_time=TestDataAnalyzer.xml_inst.build_time)
        self.assertEqual(sorted(d.package_names), \
                         sorted(TestDataAnalyzer.xml_inst.package_names))
        self.assertEqual(d.nodes, TestDataAnalyzer.xml_inst.nodes)

    def test_analyzer_topology_sort_negative(self):
        """Check topology sort"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst)
        d.topology_sorting()
        self.assertEqual(d.topology_sorted, TestDataAnalyzer.xml_inst.topology_sorted)

    def test_analyzer_before_chromium_negative(self):
        """Check before chromium_efl"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst)
        d.topology_sorting()
        c = d.get_all_packages_before_chromium_efl()
        self.assertEqual(c, TestDataAnalyzer.xml_inst.chromium)

    def test_analyzer_link_info_negative(self):
        """Check link info"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst)
        d.topology_sorting()
        d.get_all_packages_before_chromium_efl()
        d.get_link_ordered_packages(buildtime_order=True, highdeps_order=True)
        self.assertEqual(d.top_orders_without_zero, \
                         TestDataAnalyzer.xml_inst.top_without_zero)
        self.assertEqual(sorted(d.zero_links), \
                         sorted(TestDataAnalyzer.xml_inst.zero_links))
        self.assertEqual(d.link_info, TestDataAnalyzer.xml_inst.links)

    def test_analyzer_with_buildtime_links_negative(self):
        """Check with build time with link info"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst, \
                         build_time=TestDataAnalyzer.xml_inst.build_time)
        d.topology_sorting()
        d.get_link_ordered_packages(buildtime_order=True, highdeps_order=True)
        self.assertEqual(sorted(d.zero_links), \
                         sorted(TestDataAnalyzer.xml_inst.zero_links))


    def test_analyzer_find_max_depth_negative(self):
        """Check find max depth"""

        d = DataAnalyzer(inst_xml=TestDataAnalyzer.xml_inst, \
                         build_time=TestDataAnalyzer.xml_inst.build_time)
        d.topology_sorting()
        d.get_link_ordered_packages(buildtime_order=True, highdeps_order=True)
        d.find_max_depth()
        self.assertEqual(list(d.max_depth.keys()), TestDataAnalyzer.xml_inst.max_depth)


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
