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

"""Dependency Information"""

import sys
import os
import xml.etree.ElementTree as ElementTree
import shutil
import json


class GlobalStorage:
    """Store global variables"""

    package_names = []
    sub_pkg_edges = {}
    pkg_id = {}
    main_sub_pkg = {}
    pkg_print_index = {}
    sub_main_pkg = {}
    dep_edges = set()
    sorted_packages = []
    main_pkg_level = {}
    reduced_edges = {}
    reduced_edges_reverse = {}
    warn_message = []
    depends_data = {}

    def __init__(self):
        """Init routine"""

    def empty_share_vars(self, proceed=True):
        """Empty variables"""

        if proceed:
            self.package_names = []

    def warning_message(self, message):
        """Garbage function"""

        self.warn_message.append('{}'.format(message))

    def attach_package_data(self, package_name, data_key, data_value):
        """Write package depends information"""

        package_id = 9999
        if package_name != 'index':
            package_id = self.package_names.index(package_name)
        if package_id not in self.depends_data:
            self.depends_data[package_id] = {}
        self.depends_data[package_id][data_key] = data_value

    def flush_output_to_file(self, output_dir):
        """Write output to file"""

        target_dir = os.path.join(output_dir, 'networks')
        os.makedirs(target_dir)
        self.depends_data['package_names'] = self.package_names[:]
        for key in self.depends_data:
            with open(os.path.join(target_dir, '{}.json'.format(key)), 'w') as network_f:
                json.dump(self.depends_data[key], network_f)


def make_edges(nodes, sorted_info, dep_packages, cycle_edges, reduced_info):
    """Edge information"""

    edges=set()

    level=0
    while level < len(sorted_info)-1:
        for src_pkg in sorted_info[level]:
            next_level = level+1
            for dst_pkg in sorted_info[next_level]:
                if src_pkg in dep_packages and dst_pkg in dep_packages[src_pkg]:
                    edges.add((src_pkg, dst_pkg, 'false'))
            if src_pkg in reduced_info:
                for short_item in reduced_info[src_pkg]:
                    if short_item[0] == src_pkg and short_item not in edges:
                        edges.add(short_item)
        level=level+1

    for src_pkg,dst_pkgs in cycle_edges.items():
        for dst_pkg in dst_pkgs:
            if src_pkg in nodes and dst_pkg in nodes:
                edges.add((src_pkg, dst_pkg, 'true'))

    return edges


def make_full_edges(nodes, dep_packages, cycle_edges):
    """Full Edge information"""

    edges=set()

    for pkg in nodes:
        if pkg in dep_packages:
            for dst_pkg in dep_packages[pkg]:
                if dst_pkg in nodes:
                    edges.add((pkg, dst_pkg, 'false'))

    for src_pkg,dst_pkgs in cycle_edges.items():
        for dst_pkg in dst_pkgs:
            if src_pkg in nodes and dst_pkg in nodes:
                edges.add((src_pkg, dst_pkg, 'true'))

    return edges

# pylint: disable=R0914
def topology_sort_package(nodes, dep_packages, in_edge_count, cycle_edges, reduced_info):
    """Process topology sorting"""

    level=0
    pkg_count=0
    total_pkg_count=len(nodes)
    sorted_info=[]
    pkg_level={}

    # loop until all packages are inserted to sorted_packages
    while pkg_count < total_pkg_count:
        sorted_info.append([])
        # find packages that have zero in_edge_count
        for pkg in nodes:
            if pkg not in in_edge_count or in_edge_count[pkg] == 0:
                sorted_info[level].append(pkg)
                in_edge_count[pkg]=-1
                pkg_level[pkg]=level
                pkg_count=pkg_count+1

        # if no packages in this level, but pkg_count < total_pkg_count,
        # It is the case there is a cycle. Currently, we cannot solve this case.
        if( len(sorted_info[level]) == 0 and pkg_count < total_pkg_count ):
            print('Cycles should be removed before calling TopologySortPackages!')
            sys.exit(0)

        #decrease in_edge_count for target packages
        for pkg in sorted_info[level]:
            if pkg in dep_packages:
                for dep_pkg in dep_packages[pkg]:
                    in_edge_count[dep_pkg] = in_edge_count[dep_pkg] - 1
        level = level+1

    # compensate nodes.
    # if a node is in cycle_edges, insert it into the nodes.
    for src,dst_pkgs in cycle_edges.items():
        if src not in nodes:
            continue
        for dst_pkg in dst_pkgs:
            if dst_pkg not in nodes:
                nodes.add(dst_pkg)
                pkg_level[dst_pkg]=pkg_level[src]+1

    edges = make_edges(nodes, sorted_info, dep_packages, cycle_edges, reduced_info)
    full_edges = make_full_edges(nodes, dep_packages, cycle_edges)
    return nodes, edges, pkg_level, full_edges


def insert_package(pkg_name, share_var):
    """Add package information"""

    if not pkg_name in share_var.pkg_id:
        if pkg_name in share_var.package_names:
            share_var.pkg_id[pkg_name] = share_var.package_names.index(pkg_name)
        else:
            share_var.pkg_id[pkg_name] = 100000 + len(share_var.pkg_id)
        share_var.pkg_print_index[pkg_name] = 0


def find_main_package_name(sub_pkg_name, share_var):
    """Find main package name"""

    # If it is a main package, we cannot find it in sub_main_pkg.
    # In this case, just return the package name
    if sub_pkg_name in share_var.main_sub_pkg.keys():
        return sub_pkg_name

    if not sub_pkg_name in share_var.sub_main_pkg:
        return None

    return share_var.sub_main_pkg[sub_pkg_name]


def insert_sub_package(pkg_name, sub_pkg_name, share_var):
    """Insert sub package"""

    if not pkg_name in share_var.main_sub_pkg:
        share_var.main_sub_pkg[pkg_name]=[]
    share_var.main_sub_pkg[pkg_name].append(sub_pkg_name)

    if sub_pkg_name in share_var.sub_main_pkg:
        print('Subpackage ' + sub_pkg_name + ' is related to one or more main ' + 'packages(' \
            + share_var.sub_main_pkg[sub_pkg_name] + ','+ pkg_name + ')!\n')
    share_var.sub_main_pkg[sub_pkg_name] = pkg_name

    share_var.pkg_print_index[sub_pkg_name] = 0


def insert_edge(pkg_name, dep_pkg_name, share_var):
    """Edge information"""

    if not dep_pkg_name in share_var.sub_pkg_edges:
        share_var.sub_pkg_edges[dep_pkg_name]=[]
    insert_package(dep_pkg_name, share_var)
    insert_package(pkg_name, share_var)
    share_var.sub_pkg_edges[dep_pkg_name].append(pkg_name)
    #pprint.PrettyPrinter(indent=4).pprint(sub_pkg_edges)


def remove_cycle(main_pkg_edges, full_in_edge_count):
    """Remove redundant cycle information"""

    cycle_edges={}
    visited=set()
    path=set()

    def visit(level, node):
        if node in visited:
            return
        if node not in main_pkg_edges:
            return

        #for i in range(1,level):
        #print " ",
        #print "("+str(level)+")visiting "+node
        visited.add(node)
        path.add(node)
        dst_pkgs=main_pkg_edges[node].copy()
        for dst in dst_pkgs:
            if dst in path:
                #cycle!
                print("removing cycle (" + node + "->"+dst+")")
                if node not in cycle_edges:
                    cycle_edges[node]=set()
                cycle_edges[node].add(dst)
                main_pkg_edges[node].remove(dst)
                full_in_edge_count[dst]=full_in_edge_count[dst]-1
            else:
                visit(level+1, dst)
        path.remove(node)

    for pkg in main_pkg_edges.keys():
        visit(0, pkg)

    return main_pkg_edges, cycle_edges, full_in_edge_count


def make_sub_graph(pkg_to_start, main_pkg_edges, cycle_edges, share_var):
    """Sub graph"""

    pkg_status = {}
    nodes = set()
    dep_packages = {}
    in_edge_count = {}

    pkg_name = find_main_package_name(pkg_to_start, share_var)
    more_packages=1
    while more_packages:
        more_packages=0
        #print 'adding pkg '+pkg_name
        nodes.add(pkg_name)
        if pkg_name in main_pkg_edges:
            for dst_pkg_name in main_pkg_edges[pkg_name]:
                if pkg_name not in dep_packages:
                    dep_packages[pkg_name]=[]
                dep_packages[pkg_name].append(dst_pkg_name)
                if dst_pkg_name not in in_edge_count:
                    in_edge_count[dst_pkg_name] = 0
                in_edge_count[dst_pkg_name] = in_edge_count[dst_pkg_name] + 1
                if dst_pkg_name not in pkg_status:
                    #print 'pkg_status['+dst_pkg_name+']=visited'
                    pkg_status[dst_pkg_name]='visited'
        if pkg_name in cycle_edges:
            for dst_pkg_name in cycle_edges[pkg_name]:
                if pkg_name not in dep_packages:
                    dep_packages[pkg_name]=[]
                dep_packages[pkg_name].append(dst_pkg_name)
                if dst_pkg_name not in pkg_status:
                    #print 'pkg_status['+dst_pkg_name+']=visited'
                    pkg_status[dst_pkg_name]='visited'

        pkg_status[pkg_name] = 'printed'

        for pkg_st in pkg_status:
            if pkg_status[pkg_st] == 'visited':
                pkg_name = pkg_st
                more_packages=1
                break

    return nodes, dep_packages, in_edge_count


def print_vis_format(nodes, edges, pkg_level, share_var):
    """Write package data"""

    data_nodes = []
    link_list = [{}] * len(nodes)
    y_offset = {}
    for pkg_name in nodes:
        pkg_id = share_var.package_names.index(pkg_name)
        data_nodes.append(pkg_id)

        my_pkg_level = pkg_level[pkg_name]
        if my_pkg_level not in y_offset:
            y_offset[my_pkg_level] = -1
        y_offset[my_pkg_level] = y_offset[my_pkg_level] + 1
        link_list[data_nodes.index(pkg_id)] = [my_pkg_level, 0, y_offset[my_pkg_level]]

    data_edges = {}
    for item in edges:
        src_pkg_id = share_var.pkg_id[item[0]]
        if src_pkg_id not in data_edges:
            data_edges[src_pkg_id] = []
        data_edges[src_pkg_id].append(share_var.pkg_id[item[1]])
    #data_out = {"nodes": data_nodes, "edges": data_edges}

    #with open(filename, 'w') as out_f:
    #    json.dump(data_out, out_f)

    return data_nodes, data_edges, link_list


# pylint: disable=R0913
def generate_output(pkg_name, nodes, edges, pkg_level, full_edges, reverse, share_var):
    """Output information"""

    # Partial
    js_postfix = "p"
    if reverse:
        js_postfix = "{}r".format(js_postfix)

    data_nodes, data_edges, link_list = print_vis_format( \
        nodes, edges, pkg_level, share_var)
    share_var.attach_package_data(pkg_name, '{}n'.format(js_postfix), data_nodes)
    share_var.attach_package_data(pkg_name, '{}e'.format(js_postfix), data_edges)
    share_var.attach_package_data(pkg_name, '{}l'.format(js_postfix), link_list)

    # Full
    js_postfix = "f"
    if reverse:
        js_postfix = "{}r".format(js_postfix)

    data_nodes, data_edges, link_list = print_vis_format( \
        nodes, full_edges, pkg_level, share_var)
    share_var.attach_package_data(pkg_name, '{}n'.format(js_postfix), data_nodes)
    share_var.attach_package_data(pkg_name, '{}e'.format(js_postfix), data_edges)
    share_var.attach_package_data(pkg_name, '{}l'.format(js_postfix), link_list)


# pylint: disable=R0912,R0914,R0915
def make_dep_graph(input_file_contents, dest_dir_name, package_name_ids):
    """Main routine"""

    share_var = GlobalStorage()
    share_var.empty_share_vars()

    share_var.package_names = package_name_ids[:]

    root = ElementTree.fromstring(input_file_contents)
    for package in root:
        if package.tag != 'package':
            continue
        pkg_name = package.attrib['name']
        insert_package(pkg_name, share_var)
        dep_pkg_list = []

        for child in package:
            if child.tag == 'pkgdep':
                dep_pkg_name = child.text
                dep_pkg_list.append(dep_pkg_name)
            if child.tag == 'subpkg':
                sub_pkg_name = child.text
                insert_sub_package(pkg_name, sub_pkg_name, share_var)

        # if there are no sub packages, insert itself.
        if not pkg_name in share_var.main_sub_pkg:
            share_var.main_sub_pkg[pkg_name]=[]
            share_var.main_sub_pkg[pkg_name].append(pkg_name)

        # make dependence (dep_pkg_list -> sub_pkg_name)
        for dep_pkg_name in dep_pkg_list:
            for sub_pkg_name in share_var.main_sub_pkg[pkg_name]:
                insert_edge(sub_pkg_name, dep_pkg_name, share_var)

    main_pkg_edges={}
    full_in_edge_count={}
    main_pkg_reverse_edges={}
    full_in_reverse_edge_count={}
    #generate main_pkg_edges using sub_pkg_edges
    for src,dst_pkgs in share_var.sub_pkg_edges.items():
        src_main = find_main_package_name(src, share_var)
        if src_main is None:
            continue
        for dst in dst_pkgs:
            dst_main = find_main_package_name(dst, share_var)
            if dst_main is None:
                continue

            #for main_pkg_edges
            if not src_main in main_pkg_edges:
                main_pkg_edges[src_main]=set()
            if dst_main not in main_pkg_edges[src_main]:
                main_pkg_edges[src_main].add(dst_main)
                if dst_main not in full_in_edge_count:
                    full_in_edge_count[dst_main]=0
                full_in_edge_count[dst_main]=full_in_edge_count[dst_main]+1

            # for main_pkg_reverse_edges
            if not dst_main in main_pkg_reverse_edges:
                main_pkg_reverse_edges[dst_main]=set()
            if src_main not in main_pkg_reverse_edges[dst_main]:
                main_pkg_reverse_edges[dst_main].add(src_main)
                if src_main not in full_in_reverse_edge_count:
                    full_in_reverse_edge_count[src_main]=0
                full_in_reverse_edge_count[src_main]=full_in_reverse_edge_count[src_main]+1


    #print 'Removing cycles...'
    main_pkg_edges, cycle_edges, full_in_edge_count = \
        remove_cycle(main_pkg_edges, full_in_edge_count)
    main_pkg_reverse_edges, cycle_reverse_edges, full_in_reverse_edge_count = \
        remove_cycle(main_pkg_reverse_edges, full_in_reverse_edge_count)

    ## for dependency graph
    #make build_dep
    shutil.rmtree(dest_dir_name, ignore_errors=True)
    os.makedirs(dest_dir_name)

    #make a dependency graph for each package.
    for pkg in share_var.main_sub_pkg:
        #print 'processing package for dependence graph: ' + pkg
        nodes, dep_packages, in_edge_count = \
            make_sub_graph(pkg, main_pkg_edges, cycle_edges, share_var)
        nodes, edges, pkg_level, full_edges = \
            topology_sort_package(nodes, dep_packages, in_edge_count, \
            cycle_edges, share_var.reduced_edges)
        share_var.reduced_edges[pkg]=edges.copy()
        generate_output(pkg, nodes, edges, pkg_level, full_edges, False, share_var)

    #make a full dependency graph
    #print 'printing full package dependency graph...'
    nodes, edges, pkg_level, full_edges = \
        topology_sort_package(share_var.main_sub_pkg.keys(), main_pkg_edges, \
        full_in_edge_count, cycle_edges, share_var.reduced_edges)
    generate_output('index', nodes, edges, pkg_level, full_edges, False, share_var)

    #--------------------------------------------------------------------------------
    ## for reverse dependency graph

    #make a reverse dependency graph for each package.
    for pkg in share_var.main_sub_pkg:
        #print 'processing package for reverse dependence graph: ' + pkg
        nodes, dep_packages, in_edge_count = \
            make_sub_graph(pkg, main_pkg_reverse_edges, cycle_reverse_edges, share_var)
        nodes, edges, pkg_level, full_edges = \
            topology_sort_package(nodes, dep_packages, in_edge_count, cycle_reverse_edges, \
            share_var.reduced_edges_reverse)
        share_var.reduced_edges_reverse[pkg]=edges.copy()
        generate_output(pkg, nodes, edges, pkg_level, full_edges, True, share_var)

    #make a full dependency graph
    #print 'printing full package reverse dependency graph...'
    nodes, edges, pkg_level, full_edges = \
        topology_sort_package(share_var.main_sub_pkg.keys(), main_pkg_reverse_edges, \
        full_in_reverse_edge_count, cycle_reverse_edges, share_var.reduced_edges_reverse)
    generate_output('index', nodes, edges, pkg_level, full_edges, True, share_var)

    share_var.flush_output_to_file(dest_dir_name)
