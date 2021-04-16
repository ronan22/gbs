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

"""Generate package build time json file"""

import os
import sys
import shutil

from bsr.network.dep_parse import make_dep_graph


def create_build_dep_graph(depends_xml_contents, depends_root, package_names):
    """Main depends graph routine"""

    network_workspace = os.path.join(depends_root, 'default', 'arch')
    shutil.rmtree(network_workspace, ignore_errors=True)
    os.makedirs(network_workspace)

    make_dep_graph(depends_xml_contents, network_workspace, package_names)


def main():
    """Script entry point.
    """

    print('Do nothing here...')


if __name__ == '__main__':
    sys.exit(main())
