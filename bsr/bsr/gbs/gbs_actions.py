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

"""GBS related job"""

import os
import subprocess
import shutil

try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser

from bsr.utility.utils import pushd, console, list_all_directories


# pylint: disable=R0902
class GbsAction:
    """GBS related actions"""

    verbose = False
    preview = False

    configs = {}
    reference_url = None
    profile_name = 'default'

    depends_dir = None
    log_dir = None

    depends_xml_file_content = None

    # pylint: disable=R0913
    def __init__(self, roots=None, user_xml_file=None, verbose=False, \
                 reference_url=None, preview=False):
        """Initialize"""

        default_gbs_root = os.path.join(os.getcwd(), '.GBS-ROOT.bsr') + '/'

        self.verbose = verbose
        self.preview = preview
        self.reference_url = reference_url
        self.set_configs(roots)

        if self.get_build_root() is None:
            self.configs['gbs_root'] = default_gbs_root
        if self.get_build_root() and not self.get_build_root().endswith('/'):
            self.configs['gbs_root'] = '{}/'.format(self.get_build_root())

        if os.path.exists(os.path.join(os.getcwd(), '.gbs.conf.bsr')):
            os.remove(os.path.join(os.getcwd(), '.gbs.conf.bsr'))

        self.read_gbs_conf()

        self.depends_dir = os.path.join(self.get_build_root(), 'local', 'depends',
                                        self.profile_name, self.get_arch())
        self.log_dir = os.path.join(self.get_build_root(), 'local', 'repos',
                                    self.profile_name, self.get_arch(), 'logs')
        if 'user_log_dir' in roots and roots['user_log_dir']:
            self.log_dir = roots['user_log_dir']

        if user_xml_file is not None:
            self.configs['arch'] = 'arch'
            with open(user_xml_file, 'r') as user_f:
                self.depends_xml_file_content = user_f.read()

    def set_configs(self, roots):
        """Set config values"""

        self.configs = {
            'gbs_root': roots.get('build_root'),
            'src_root': roots.get('src_root'),
            'arch': roots.get('arch', 'arch'),
            'conf_file': roots.get('conf_file')
        }
        if self.configs.get('arch') is None:
            self.configs['arch'] = 'arch'

    def get_build_root(self):
        """GBS build root"""

        return self.configs.get('gbs_root')

    def get_source_root(self):
        """GBS source root"""

        return self.configs.get('src_root')

    def get_arch(self):
        """GBS architecture"""

        return self.configs.get('arch')

    def get_config_file(self):
        """GBS configuration file"""

        return self.configs.get('conf_file')

    def get_depends_dir(self):
        """GBS depends directory"""

        return self.depends_dir

    def read_gbs_conf(self):
        """Read gbs conf file content"""

        if self.get_config_file() is None or not os.path.isfile(self.get_config_file()):
            if self.get_source_root() is None:
                return
            for file_n in sorted(os.listdir(self.get_source_root())):
                if os.path.isfile(os.path.join(self.get_source_root(), file_n)) and \
                        'gbs.conf' in file_n:
                    self.configs['conf_file'] = os.path.join(self.get_source_root(), file_n)
                    break
        if self.get_config_file() is None:
            return

        console('Use gbs configuration file from {}'.format(self.get_config_file()), \
                self.verbose)

        parser = SafeConfigParser()
        parser.read(self.get_config_file())

        conf_profile = parser.get('general', 'profile')
        self.profile_name = conf_profile.replace('profile.', '').replace('-', '_')

        if self.preview is True and self.reference_url is not None:
            conf_repos = ''.join(parser.get(conf_profile, 'repos').split()).split(',')
            reference_found = False
            for conf_repo in conf_repos:
                url = parser.get(conf_repo, 'url')
                if self.reference_url in url:
                    reference_found = True
                    break

            def _list_candidate_path(url):
                """Candidate repo url"""

                matches = []
                for path_name in list_all_directories(url, 'repomd.xml'):
                    if '/source/' not in path_name and \
                            path_name.endswith('/repodata/repomd.xml'):
                        matches.append(path_name.replace('repodata/repomd.xml', ''))

                return matches

            # pylint: disable=W0511
            if reference_found is not True:
                for index, url_path in enumerate(_list_candidate_path( \
                        self.reference_url)):
                    new_repo_name = 'repo.reference_bsr_action_{}'.format(index)
                    parser.add_section(new_repo_name)
                    parser.set(new_repo_name, 'url', url_path)
                    conf_repos.append(new_repo_name)
                    console('Adding new repo: {}'.format(url_path, verbose=self.verbose))
                parser.set(conf_profile, 'repos', ','.join(conf_repos))
                with open(os.path.join(os.getcwd(), '.gbs.conf.bsr'), 'w') as conf_file:
                    parser.write(conf_file)
                self.configs['conf_file'] = os.path.join(os.getcwd(), '.gbs.conf.bsr')
                console('Renew gbs conf for preview: {}'.format(self.get_config_file()), \
                        verbose=self.verbose)

    def find_depends_xml_file(self, gbs_root=None):
        """Find generated depends xml file"""

        depends_xml_file = None
        depends_dir = self.depends_dir
        if gbs_root is not None:
            depends_dir = self.depends_dir.replace(self.get_build_root(), gbs_root)

        if not os.path.isdir(depends_dir):
            return

        for dep_file in sorted(os.listdir(depends_dir)):
            fname = os.path.join(depends_dir, dep_file)
            if os.path.isfile(fname) and fname.endswith('.xml'):
                if depends_xml_file is None:
                    depends_xml_file = fname
                elif '_rev' in depends_xml_file and '_rev' not in dep_file:
                    depends_xml_file = fname

        console('We are using the xml file {}'.format(depends_xml_file), \
                verbose=self.verbose)

        if os.path.isfile(depends_xml_file):
            with open(depends_xml_file, 'r') as dep_xml_f:
                self.depends_xml_file_content = dep_xml_f.read()

        # if self.preview is True:
        #    shutil.rmtree(gbs_root)

    def call_depends(self, style='git', local_only=False):
        """Call gbs depends command"""

        if not self.get_source_root():
            return

        with pushd(self.get_source_root()):
            cmd = ['gbs']
            gbs_root = self.get_build_root()

            # if self.preview is True:
            #    console('Depends with preview mode...', verbose=self.verbose)
            #    preview_gbs_conf = '.gbs.conf.preview'
            #    if os.path.isfile(preview_gbs_conf):
            #        cmd.extend(['-c', preview_gbs_conf])
            #    gbs_root = self.get_build_root().replace('/GBS-ROOT/', '/GBS-ROOT.preview/')

            if self.get_config_file() and os.path.isfile(self.get_config_file()):
                cmd.extend(['-c', self.get_config_file()])

            # Remove old depends directory
            shutil.rmtree(os.path.join(gbs_root, 'local', 'depends'), ignore_errors=True)

            cmd.extend(['depends', '-A', '{}'.format(self.get_arch()), '-B', gbs_root, \
                        '--style={}'.format(style)])
            if local_only is True:
                cmd.extend(['--local-only'])
            console(cmd, verbose=self.verbose)

            ret = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (_stdout, _stderr) = ret.communicate()
            console(_stdout, verbose=self.verbose)
            console(_stderr, verbose=self.verbose)

        self.find_depends_xml_file(gbs_root)
