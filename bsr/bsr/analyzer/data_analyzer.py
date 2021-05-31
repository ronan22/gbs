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

"""Analyzing the report data"""

from operator import or_
from itertools import starmap

from bsr.utility.utils import to_timestamp, console


# pylint: disable=R0902
class DataAnalyzer:
    """DataAnalyzer"""

    package_names = []
    nodes = []
    edges = {}
    in_degree = []

    topology_sorted = []
    build_time = None
    sorted_buildtime = None

    count_link_map = None
    zero_links = []
    top_orders_without_zero = []
    max_depth = None
    link_info = None

    verbose = False

    def __init__(self, inst_xml=None, build_time=None, verbose=False):
        """Initialize"""

        self.verbose = verbose
        if inst_xml:
            self.package_names = inst_xml.package_names
            self.nodes = inst_xml.nodes
            self.edges = inst_xml.edges
            self.in_degree = inst_xml.in_degree
        self.build_time = build_time
        if self.build_time:
            # Sort by largest build time
            sorted_b = {}
            for pkg in self.build_time:
                sorted_b[self.build_time[pkg].get('package')] = \
                    self.build_time[pkg].get('duration')
            self.sorted_buildtime = sorted(sorted_b, key=sorted_b.get, reverse=True)

            # Fake xml info from buildtime
            if not inst_xml and not self.package_names and not self.nodes:
                for pkg_name in self.sorted_buildtime:
                    self.package_names.append(pkg_name)
                    self.nodes.append(self.sorted_buildtime.index(pkg_name))
                    self.in_degree.append(0)
                    self.edges[self.sorted_buildtime.index(pkg_name)] = []

    def topology_sorting(self):
        """Do topological sorting"""

        keys = sorted(self.edges.keys())
        queue = []
        answer = []
        for i in range(len(self.in_degree)):
            if self.in_degree[i] == 0:
                queue.append(keys[i])
        while queue:
            answer.append(sorted(queue))
            new_arr = []
            for i in queue:
                for j in range(len(self.edges[i])):
                    idx = keys.index(self.edges[i][j])
                    self.in_degree[idx] -= 1
                    if self.in_degree[idx] == 0:
                        new_arr.append(keys[idx])
            queue = new_arr

        self.topology_sorted = answer

    def get_all_packages_before_chromium_efl(self):
        """Get all packages before chromium-efl"""

        pkg_list = []
        chromium_idx = None
        for level in range(len(self.topology_sorted) - 1, -1, -1):
            pkgs = self.topology_sorted[level]
            if chromium_idx is None:
                for pkg in pkgs:
                    if self.package_names[pkg] == 'chromium-efl':
                        pkg_list.append(pkg)
                        chromium_idx = pkg
                        break
            for src in pkgs:
                for dst in self.edges[src]:
                    if dst not in pkg_list:
                        continue
                    if src not in pkg_list:
                        pkg_list.append(src)

        console('We have #{} packages which links to chromium-efl.'.format( \
            len(pkg_list)), verbose=self.verbose)
        return [self.package_names[item] for item in reversed(pkg_list)]

    def get_link_counts_map(self):
        """Calculate number of links depends on each package"""

        if self.count_link_map is not None:
            return

        count_link = {x: [0] * len(self.nodes) for x in self.nodes}
        for level in range(len(self.topology_sorted) - 1, -1, -1):
            for package in self.topology_sorted[level]:
                for dep in self.edges[package]:
                    count_link[package][dep] = 1
                    zipped = zip(count_link[package], count_link[dep])
                    count_link[package] = list(starmap(or_, zipped))

        self.count_link_map = count_link

    def _work_with_buildtime(self, buildtime_order):
        """Count into buildtime for zero ordering"""

        if buildtime_order is True and self.sorted_buildtime:
            zero_links_time = []
            for sn_pkg in self.sorted_buildtime:
                if sn_pkg in self.zero_links:
                    zero_links_time.append(sn_pkg)
            for zn_pkg in self.zero_links:
                if zn_pkg not in self.sorted_buildtime:
                    zero_links_time.append(zn_pkg)
            return zero_links_time

        return self.zero_links

    def generate_link_data(self):
        """Calculate link data"""

        link_data = {}
        for level in range(len(self.topology_sorted)):
            for package in self.topology_sorted[level]:
                if level not in link_data:
                    link_data[level] = []
                link_data[level].append({
                    'package': package,
                    'links': sum(self.count_link_map[package])
                })

        for level in link_data:
            link_data[level] = sorted(link_data[level], key=lambda a: a['links'], reverse=True)

        link_list = [{}] * len(self.package_names)
        for level in link_data:
            for y_depth, item in enumerate(link_data[level]):
                link_list[item.get('package')] = {
                    'level': level, \
                    'links': item.get('links'), 'y': y_depth
                }

        return link_list

    def get_link_ordered_packages(self, buildtime_order=False, highdeps_order=True):
        """Calculate link number based sorted list"""

        self.get_link_counts_map()

        self.top_orders_without_zero = []
        self.zero_links = []

        top_links_order = {}
        for level in range(len(self.topology_sorted)):
            for package in self.topology_sorted[level]:
                try:
                    cnt_links = 0
                    if highdeps_order is True:
                        cnt_links = sum(self.count_link_map[package])
                    top_links_order[package] = cnt_links
                except KeyError:
                    console('{} does not exists in the top order'.format(package), verbose=True)

        # [[pkg1, 39], [pkg2, 21], [pkg2, 7], ...]
        top_links_order = sorted(top_links_order.items(), key=lambda x: x[1], reverse=True)

        console('Total #{} items...'.format(len(top_links_order)), verbose=self.verbose)

        for item in top_links_order:
            package, link_no = item
            if link_no > 0:
                self.top_orders_without_zero.append(self.package_names[package])
            elif link_no == 0:
                self.zero_links.append(self.package_names[package])

        self.zero_links = sorted(self.zero_links)
        self.zero_links = self._work_with_buildtime(buildtime_order)

        link_info = {
            'nodes': self.nodes, 'edges_full': self.edges, 'links': {}, \
            'package_names': self.package_names
        }

        link_info['links'] = self.generate_link_data()
        self.link_info = link_info

        console('  Top Order: #{} items...'.format(len(self.top_orders_without_zero)), \
                verbose=self.verbose)
        console('  Zero Order: #{} items...'.format(len(self.zero_links)), \
                verbose=self.verbose)

    def _get_all_paths_until(self, start_pkg, path, all_path, edges):
        """Get all paths start from the given point"""

        path.append(start_pkg)
        if start_pkg not in edges or len(edges[start_pkg]) <= 0:
            all_path.append(path[:])
        else:
            for i in edges[start_pkg]:
                self._get_all_paths_until(i, path, all_path, edges)
        path.pop()

    # pylint: disable=R0201
    def _split_two_parts(self, pkg_name, topo_sorted):
        """Work with binary parts with chromium-efl cenered"""

        # Split two parts around chromium-efl.
        search_part_1 = [0, len(topo_sorted)]
        search_part_2 = [-1, len(topo_sorted)]
        # What level chromium-efl resides?
        for level, items in enumerate(topo_sorted):
            for item in items:
                if pkg_name[item] == 'chromium-efl':
                    search_part_1[1] = level + 1
                    search_part_2[0] = level
                    break

        return search_part_1, search_part_2

    # pylint: disable=R0914,R0912,R0915
    def find_max_depth(self):
        """Finding maximum build time path"""

        # Remove dangled nodes
        def trim_deps(level, storage, adj_list, build_t):
            next_level_packages = storage[level + 1]
            curr_packages = storage[level]
            answer = []
            max_duration = 0
            max_duration_pkg = None
            for pkg in curr_packages:
                found = False
                for dep_pkg in adj_list[pkg]:
                    if dep_pkg in next_level_packages:
                        found = True
                        break
                if found is True:
                    answer.append(pkg)
                if pkg in build_t and build_t[pkg]['duration'] > max_duration:
                    max_duration = build_t[pkg]['duration']
                    max_duration_pkg = pkg
            if max_duration_pkg is not None and max_duration_pkg not in answer:
                answer.append(max_duration_pkg)
            return answer

        def trim_levels(topology_sorted_orig, search_from, search_to, edges, buildtime):
            topology_sorted = topology_sorted_orig[search_from:search_to]
            # Trim non-important nodes
            if search_from == 0:
                for level in range(len(topology_sorted) - 2, -1, -1):
                    topology_sorted[level] = trim_deps(level, topology_sorted, edges, buildtime)
            return topology_sorted

        def gen_trimmed_edges(topo_sorted, edges):
            new_edges = {}
            # Make new edges
            # Preserve linked with level + 1
            for level in range(len(topo_sorted) - 1):
                next_level_packages = topo_sorted[level + 1]
                for pkg in topo_sorted[level]:
                    new_edges[pkg] = []
                    for dep_pkg in edges[pkg]:
                        if dep_pkg in next_level_packages:
                            new_edges[pkg].append(dep_pkg)
            for pkg in topo_sorted[-1]:
                new_edges[pkg] = []

            return new_edges

        # Fill blank build time
        build_t = {pkg_id: {'duration': 0} for pkg_id in range(len(self.package_names))}
        for item in self.build_time:
            pkg_name = self.build_time[item]['package']
            if pkg_name not in self.package_names:
                continue
            build_t[self.package_names.index(pkg_name)] = \
                {
                    'duration': self.build_time[item]['duration'], \
                    'start': to_timestamp(self.build_time[item]['start']), \
                    'end': to_timestamp(self.build_time[item]['end']) \
                    }

        topology_orig = self.topology_sorted
        part_1, part_2 = self._split_two_parts(self.package_names, topology_orig)

        maximum_buildtime_path = []
        for search_from, search_to in [part_1, part_2]:
            if search_from == -1:
                break
            topology_sorted = trim_levels(topology_orig, search_from, \
                                          search_to, self.edges, build_t)
            new_edges = gen_trimmed_edges(topology_sorted, self.edges)

            all_path = []
            for point in topology_sorted[0]:
                path = []
                self._get_all_paths_until(point, path, all_path, new_edges)
            max_duration = 0
            max_duration_idx = None
            for idx, item in enumerate(all_path):
                dur = 0
                for pkg_n in item:
                    dur += build_t[pkg_n]['duration']
                if max_duration < dur:
                    max_duration = dur
                    max_duration_idx = idx
            if max_duration_idx is not None:
                console('Max duration LEVEL({}->{}) is {}, path: {}'.format( \
                    search_from, search_to, max_duration, len(all_path[max_duration_idx])), \
                    verbose=self.verbose)
                for k in all_path[max_duration_idx]:
                    if k not in maximum_buildtime_path:
                        maximum_buildtime_path.append(k)

        package_levels = {}
        for level, item in enumerate(topology_orig):
            for pkg in item:
                package_levels[pkg] = level + 1
        total_buildtime = 0
        total_waittime = 0

        build_log = {}
        for idx, package_idx in enumerate(maximum_buildtime_path):
            package_buildtime = build_t[package_idx]['duration']
            package_waittime = 0
            if idx > 1:
                prev_package_idx = maximum_buildtime_path[idx - 1]
                if package_idx in build_t and \
                        'start' in build_t[package_idx] and \
                        'end' in build_t[prev_package_idx]:
                    package_waittime = build_t[package_idx]['start'] \
                                       - build_t[prev_package_idx]['end']
            total_buildtime += package_buildtime
            total_waittime += package_waittime
            console('[{}/{}] {} (build: {}, wait: {})'.format( \
                idx + 1, \
                package_levels[package_idx], \
                self.package_names[package_idx], \
                package_buildtime, package_waittime), \
                verbose=self.verbose \
                )
            build_log[self.package_names[package_idx]] = \
                {
                    'level': package_levels[package_idx], \
                    'buildtime': package_buildtime, \
                    'waittime': package_waittime \
                    }

        self.max_depth = build_log
        return build_log
