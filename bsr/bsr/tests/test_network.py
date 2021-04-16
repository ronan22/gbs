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

"""Test cases for dep_graph.py"""

import unittest
import os
import sys
import shutil
import json
from pprint import pprint

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.network.dep_graph import create_build_dep_graph


class TestNetwork(unittest.TestCase):
    """Testing dep_graph.py"""

    test_xml_content = ''
    depends_root = None
    package_names = []

    def setUp(self):
        """Default fixture"""

        TestNetwork.test_xml_content = '<builddepinfo>\n'
        TestNetwork.test_xml_content += '  <package name="a">\n'
        TestNetwork.test_xml_content += '    <source>a</source>\n'
        TestNetwork.test_xml_content += '    <pkgdep>z</pkgdep>\n'
        TestNetwork.test_xml_content += '    <subpkg>a</subpkg>\n'
        TestNetwork.test_xml_content += '  </package>\n'
        TestNetwork.test_xml_content += '  <package name="c">\n'
        TestNetwork.test_xml_content += '    <source>c</source>\n'
        TestNetwork.test_xml_content += '    <pkgdep>a</pkgdep>\n'
        TestNetwork.test_xml_content += '    <subpkg>c</subpkg>\n'
        TestNetwork.test_xml_content += '  </package>\n'
        TestNetwork.test_xml_content += '  <package name="b">\n'
        TestNetwork.test_xml_content += '    <source>b</source>\n'
        TestNetwork.test_xml_content += '    <pkgdep>a</pkgdep>\n'
        TestNetwork.test_xml_content += '    <pkgdep>q</pkgdep>\n'
        TestNetwork.test_xml_content += '    <subpkg>b</subpkg>\n'
        TestNetwork.test_xml_content += '  </package>\n'
        TestNetwork.test_xml_content += '</builddepinfo>'

        TestNetwork.package_names = ['a', 'b', 'c']

        TestNetwork.depends_root = os.path.join(os.getcwd(), 'test_depends_out')

        TestNetwork.network_root = os.path.join(TestNetwork.depends_root, \
                                                'default', 'arch', 'networks')

    def tearDown(self):
        """Destroy fixture"""

        shutil.rmtree(TestNetwork.depends_root, ignore_errors=True)

        TestNetwork.test_xml_content = ''
        TestNetwork.depends_root = None
        TestNetwork.package_names = []

    def test_network(self):
        """Check network output file created"""

        create_build_dep_graph(TestNetwork.test_xml_content, TestNetwork.depends_root, TestNetwork.package_names)

        if not os.path.isdir(TestNetwork.depends_root):
            self.assertTrue(False)

    def test_package_names(self):
        """Check input parameter - package_names"""

        create_build_dep_graph(TestNetwork.test_xml_content, TestNetwork.depends_root, TestNetwork.package_names)

        check_filename = os.path.join(TestNetwork.network_root, 'package_names.json')

        self.assertTrue(os.path.isfile(check_filename))

        network_json = None
        with open(check_filename) as network_rf:
            network_json = json.load(network_rf)

        self.assertTrue(network_json)
        self.assertEqual(network_json, TestNetwork.package_names)

        for package_id, package_name in enumerate(TestNetwork.package_names):
            self.assertTrue(os.path.isfile(os.path.join(TestNetwork.network_root, \
                                                        '{}.json'.format(package_id))))

        self.assertTrue(os.path.isfile(os.path.join(TestNetwork.network_root, '9999.json')))

    def test_partial_full_keys(self):
        """Check all the keys are included for partial/full"""

        create_build_dep_graph(TestNetwork.test_xml_content, TestNetwork.depends_root, TestNetwork.package_names)

        for package_id, package_name in enumerate(TestNetwork.package_names):
            network_json = None
            with open(os.path.join(TestNetwork.network_root, '{}.json'.format(package_id)), 'r') as network_rf:
                network_json = json.load(network_rf)
            for type_key in ["pn", "pe", "pl", "fn", "fe", "fl", \
                             "prn", "pre", "prl", "frn", "fre", "frl"]:
                self.assertIn(type_key, network_json)

    def test_json_data(self):
        """Check json data"""

        create_build_dep_graph(TestNetwork.test_xml_content, TestNetwork.depends_root, TestNetwork.package_names)

        sample_answer_json = \
            {'0': {'fe': {'0': [1, 2]},
                'fl': [[1, 0, 0], [1, 0, 1], [0, 0, 0]],
                'fn': [1, 2, 0],
                'fre': {},
                'frl': [[0, 0, 0]],
                'frn': [0],
                'pe': {'0': [1, 2]},
                'pl': [[1, 0, 0], [1, 0, 1], [0, 0, 0]],
                'pn': [1, 2, 0],
                'pre': {},
                'prl': [[0, 0, 0]],
                'prn': [0]},
            '1': {'fe': {},
                'fl': [[0, 0, 0]],
                'fn': [1],
                'fre': {'1': [0]},
                'frl': [[0, 0, 0], [1, 0, 0]],
                'frn': [1, 0],
                'pe': {},
                'pl': [[0, 0, 0]],
                'pn': [1],
                'pre': {'1': [0]},
                'prl': [[0, 0, 0], [1, 0, 0]],
                'prn': [1, 0]},
            '2': {'fe': {},
                'fl': [[0, 0, 0]],
                'fn': [2],
                'fre': {'2': [0]},
                'frl': [[0, 0, 0], [1, 0, 0]],
                'frn': [2, 0],
                'pe': {},
                'pl': [[0, 0, 0]],
                'pn': [2],
                'pre': {'2': [0]},
                'prl': [[0, 0, 0], [1, 0, 0]],
                'prn': [2, 0]},
            '9999': {'fe': {'0': [1, 2]},
                    'fl': [[0, 0, 0], [1, 0, 0], [1, 0, 1]],
                    'fn': [0, 2, 1],
                    'fre': {'1': [0], '2': [0]},
                    'frl': [[1, 0, 0], [0, 0, 0], [0, 0, 1]],
                    'frn': [0, 2, 1],
                    'pe': {'0': [1, 2]},
                    'pl': [[0, 0, 0], [1, 0, 0], [1, 0, 1]],
                    'pn': [0, 2, 1],
                    'pre': {'1': [0], '2': [0]},
                    'prl': [[1, 0, 0], [0, 0, 0], [0, 0, 1]],
                    'prn': [0, 2, 1]},
            'package_names': ['a', 'b', 'c']}

        for package_id, package_name in enumerate(TestNetwork.package_names):
            network_json = None
            with open(os.path.join(TestNetwork.network_root, '{}.json'.format(package_id)), 'r') as network_rf:
                network_json = json.load(network_rf)
            self.assertEqual(sorted(network_json.keys()), sorted(sample_answer_json['{}'.format(package_id)].keys()))


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
