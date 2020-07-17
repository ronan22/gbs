"""Functionality tests for gbs export."""

import unittest
import imp
import os
import shutil
import tempfile
from nose.tools import eq_

GBS = imp.load_source("gbs", "./tools/gbs").main

class TestExport(unittest.TestCase):
    """Test export output of gbs commands"""

    def setUp(self):
        self.cdir = os.getcwd()
        self.testdataDir = os.path.join(self.cdir, "./tests/testdata")
        os.chdir(self.testdataDir)
        os.system('./create_proj fake.spec')

    def tearDown(self):
        shutil.rmtree(os.path.join(self.testdataDir, "./fake"))
        os.chdir(self.cdir)

    def test_command_export_directory(self):
        """Test running gbs export commond."""
        try:
            GBS(argv=["gbs", "export", "fake", "-o", "tmp_output"])
            shutil.rmtree(os.path.join(self.testdataDir, "./tmp_output"))
        except SystemExit as err:
            eq_(err.code, 0)

    def test_command_export_source_rpm(self):
        """Test running gbs export source rpm commond."""
        try:
            GBS(argv=["gbs", "export", "fake", "--source-rpm", "-o", "tmp_output"])
            shutil.rmtree(os.path.join(self.testdataDir, "./tmp_output"))
        except SystemExit as err:
            eq_(err.code, 0)

    def test_command_export_include_all(self):
        """Test running gbs export with include-all commond."""
        try:
            GBS(argv=["gbs", "export", "fake", "--include-all", "-o", "tmp_output"])
            shutil.rmtree(os.path.join(self.testdataDir, "./tmp_output"))
        except SystemExit as err:
            eq_(err.code, 0)

    def test_command_export_outdir_directly(self):
        """Test running gbs export with include-all commond."""
        try:
            GBS(argv=["gbs", "export", "fake", "--outdir-directly", "-o", "tmp_output"])
            shutil.rmtree(os.path.join(self.testdataDir, "./tmp_output"))
        except SystemExit as err:
            eq_(err.code, 0)

    def test_command_export_special_spec(self):
        """Test running gbs export with --spec and --no-patch-export commond."""
        try:
            GBS(argv=["gbs", "export", "fake", "--spec=fake.spec", "--no-patch-export", "-o", "tmp_output"])
            shutil.rmtree(os.path.join(self.testdataDir, "./tmp_output"))
        except SystemExit as err:
            eq_(err.code, 0)

    def test_command_export_disable_fallback_to_native_packaging(self):
        """Test running gbs export failed case:disable fallback to native commond."""
        try:
            os.system('mkdir -p /tmp/gbs_export_tmp')
            shutil.copy('./sw-tools.spec', '/tmp/gbs_export_tmp')
            shutil.copy('./create_proj', '/tmp/gbs_export_tmp')
            os.chdir('/tmp/gbs_export_tmp')
            os.system('./create_proj --tizen sw-tools.spec')
            os.system('sed -i "s/^Version:.*$/Version:0.2/" packaging/sw-tools.spec')
            os.system('git commit -a -m "upgrade to gbs 0.2"')
            GBS(argv=["gbs", "export", "sw-tools"])
            shutil.rmtree('/tmp/gbs_export_tmp')
        except SystemExit as err:
            eq_(err.code, 2)

