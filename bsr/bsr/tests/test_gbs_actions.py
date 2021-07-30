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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bsr'))

from bsr.gbs.gbs_actions import GbsAction


class TestGbsAction(unittest.TestCase):
    """Testing gbs_actions.py"""

    test_gbs_param = {}

    def setUp(self):
        """Default fixture"""

        gbs_root = os.path.join(os.getcwd(), 'test-gbs-root')
        gbs_src_root = os.path.join(os.getcwd(), 'test-src-root')
        gbs_conf_file = os.path.join(gbs_src_root, 'test-gbs-conf')
        TestGbsAction.test_gbs_param = {
            'gbs_root': gbs_root,
            'src_root': gbs_src_root,
            'arch': 'armv7l',
            'conf_file': gbs_conf_file,
        }
        os.makedirs(gbs_root)
        os.makedirs(gbs_src_root)
        with open(gbs_conf_file, 'w') as conf_f:
            conf_f.write('''[general]
profile = profile.tizen

[profile.tizen]
repos = repo.tizen_base

[repo.tizen_base]
url = http://download.tizen.org/snapshots/tizen/base/latest/repos/standard/packages/
''')

        TestGbsAction.reference_build_url = os.getenv('BuildProfiling_Test_Url')


    def tearDown(self):
        """Destroy fixture"""

        shutil.rmtree(TestGbsAction.test_gbs_param['gbs_root'], ignore_errors=True)
        shutil.rmtree(TestGbsAction.test_gbs_param['src_root'], ignore_errors=True)

        TestGbsAction.test_gbs_param = {}

    def test_gbs_action(self):
        """Check gbs parameters"""

        g = GbsAction(roots=TestGbsAction.test_gbs_param, verbose=True)
        self.assertEqual('armv7l', g.configs['arch'])

    def test_gbs_action_with_conf(self):
        """Check .gbs.conf.bsr"""

        shutil.copy(TestGbsAction.test_gbs_param['conf_file'],
                    os.path.join(os.getcwd(), '.gbs.conf.bsr'))
        g = GbsAction(roots=TestGbsAction.test_gbs_param, verbose=True)
        self.assertEqual('armv7l', g.configs['arch'])

    def test_gbs_action_preview_negative(self):
        """Check preview option"""

        g = GbsAction(roots=TestGbsAction.test_gbs_param, preview=True, verbose=True)
        self.assertEqual('armv7l', g.configs['arch'])

    def test_gbs_action_previe_with_ref_negative(self):
        """Check preview option with reference"""

        try:
            g = GbsAction(roots=TestGbsAction.test_gbs_param, preview=True, verbose=True, \
                          reference_url=TestGbsAction.reference_build_url)
            self.assertEqual('armv7l', g.configs['arch'])
        except Exception:
            pass

    def test_gbs_action_depends_negative(self):
        """Check gbs depends command"""

        g = GbsAction(roots=TestGbsAction.test_gbs_param, verbose=True)
        self.assertEqual('armv7l', g.configs['arch'])

        try:
            g.call_depends()
        except Exception:
            pass

        try:
            g.find_depends_xml_file()
        except Exception:
            pass


if __name__ == '__main__':
    """Entry point"""

    unittest.main()
