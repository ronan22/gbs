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

"""Test cases for depends_xml.py"""

import unittest
import os
import sys
from pprint import pprint

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.report.depends_xml import DependsXml


class TestReadXmlFile(unittest.TestCase):
    """Testing depends_xml.py"""

    testcontent = ''

    def setUp(self):
        """Default fixture"""

        TestReadXmlFile.testcontent = '<builddepinfo>\n'
        TestReadXmlFile.testcontent += '  <package name="a">\n'
        TestReadXmlFile.testcontent += '    <source>a</source>\n'
        TestReadXmlFile.testcontent += '    <pkgdep>z</pkgdep>\n'
        TestReadXmlFile.testcontent += '    <subpkg>a</subpkg>\n'
        TestReadXmlFile.testcontent += '  </package>\n'
        TestReadXmlFile.testcontent += '  <package name="c">\n'
        TestReadXmlFile.testcontent += '    <source>c</source>\n'
        TestReadXmlFile.testcontent += '    <pkgdep>a</pkgdep>\n'
        TestReadXmlFile.testcontent += '    <subpkg>c</subpkg>\n'
        TestReadXmlFile.testcontent += '  </package>\n'
        TestReadXmlFile.testcontent += '  <package name="b">\n'
        TestReadXmlFile.testcontent += '    <source>b</source>\n'
        TestReadXmlFile.testcontent += '    <pkgdep>a</pkgdep>\n'
        TestReadXmlFile.testcontent += '    <pkgdep>q</pkgdep>\n'
        TestReadXmlFile.testcontent += '    <subpkg>b</subpkg>\n'
        TestReadXmlFile.testcontent += '  </package>\n'
        TestReadXmlFile.testcontent += '</builddepinfo>'

    def tearDown(self):
        """Destroy fixture"""

        try:
            os.remove(TestReadXmlFile.testcontent)
        except (IOError, OSError) as e:
            print('Error removing test file')

    def test_read_dep_xml(self):
        """Check package names"""

        # package_names = ['a', 'b', 'c']

        d = DependsXml(TestReadXmlFile.testcontent)
        self.assertTrue(len(d.package_names) == 3)
        self.assertEqual(sorted(d.package_names), ['a', 'b', 'c'])
        self.assertNotIn('q', d.package_names)
        self.assertNotIn('z', d.package_names)

    def test_check_nodes(self):
        """Check node list"""

        # nodes = [0, 1, 2]

        d = DependsXml(TestReadXmlFile.testcontent)
        self.assertTrue(len(d.nodes) == 3)
        self.assertEqual([0, 1, 2], sorted(d.nodes))
        self.assertIn(d.package_names.index('a'), d.nodes)
        self.assertIn(d.package_names.index('b'), d.nodes)
        self.assertIn(d.package_names.index('c'), d.nodes)
        self.assertNotIn(3, d.nodes)
        for package_id in d.nodes:
            self.assertIsInstance(package_id, int)

    def test_check_edges_negative(self):
        """Check edge list"""

        # edges = {0: [1, 2], 1: [], 2: []}

        d = DependsXml(TestReadXmlFile.testcontent)
        self.assertEqual(len(d.edges), 3)
        self.assertIn(0, d.edges)
        self.assertIn(1, d.edges)
        self.assertIn(2, d.edges)

    def test_check_indegree_negative(self):
        """Check in degree list for topology sorting"""

        # in_degree = [0, 1, 1]

        d = DependsXml(TestReadXmlFile.testcontent)
        self.assertEqual(len(d.in_degree), 3)
        self.assertTrue(d.in_degree[d.package_names.index('a')] == 0)
        self.assertTrue(d.in_degree[d.package_names.index('b')] == 1)
        self.assertTrue(d.in_degree[d.package_names.index('c')] == 1)

if __name__ == '__main__':
    """Entry point"""

    unittest.main()
