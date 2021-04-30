#!/usr/bin/env python
#-*- coding: utf-8 -*-
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

"""Hold dependency xml data"""

import xml.etree.ElementTree as ET

from bsr.utility.utils import console


class DependsXml:
    """Dependency xml data"""

    verbose = False
    package_names = []
    nodes = []
    edges = {}
    in_degree = []

    def __init__(self, xml_file_content, verbose=False):
        """Initialize"""

        self.verbose = verbose

        if xml_file_content is not None:
            self.read_dep_xml(xml_file_content)

    def read_dep_xml(self, content):
        """Read file contents into node-edge format"""

        bucket = {}
        sub_to_main_map = {}

        for child in ET.fromstring(content):
            src_name = child.attrib.get('name')
            bucket[src_name] = {'pkgdep': [], 'subpkg': []}
            for pkgdep in child.findall('pkgdep'):
                bucket[src_name]['pkgdep'].append(pkgdep.text)
            for subpkg in child.findall('subpkg'):
                bucket[src_name]['subpkg'].append(subpkg.text)
                sub_to_main_map[subpkg.text] = src_name
            if src_name not in bucket[src_name]['subpkg']:
                bucket[src_name]['subpkg'].append(src_name)
            if src_name not in sub_to_main_map:
                sub_to_main_map[src_name] = src_name
        console('Loaded... # of total packages: {}'.format(len(bucket.keys())), \
                verbose=self.verbose)

        self.init_items(bucket)
        self.construct_mapping(bucket, sub_to_main_map)

    def init_items(self, bucket):
        """Initialize items"""

        self.package_names = list(bucket.keys())
        self.nodes = list(range(len(self.package_names)))
        self.edges = { k: [] for k in self.nodes }
        self.in_degree = [0] * len(self.package_names)

    def construct_mapping(self, bucket, sub_to_main_map):
        """Replace sub packages to main package and remove duplicate"""

        for pkg_id in self.nodes:
            for dep in bucket[self.package_names[pkg_id]].get('pkgdep'):
                if dep not in sub_to_main_map:
                    continue
                dep_id = self.package_names.index(sub_to_main_map[dep])
                if pkg_id not in self.edges[dep_id]:
                    self.edges[dep_id].append(pkg_id)
                    self.in_degree[pkg_id] += 1
