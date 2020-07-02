
#!/usr/bin/python -tt
# vim: ai ts=4 sts=4 et sw=4
#
# Copyright (c) 2012 Intel, Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2 of the License
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 59
# Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Implementation of subcmd: depends
"""
import os
import shutil
import pwd
import re
import urlparse
import glob
import requests
import subprocess
import re

from gitbuildsys.utils import Temp, RepoParser, read_localconf
from gitbuildsys.errors import GbsError, Usage
from gitbuildsys.conf import configmgr
from gitbuildsys.safe_url import SafeURL
from gitbuildsys.cmd_export import get_packaging_dir
from gitbuildsys.log import LOGGER as log
from gitbuildsys.oscapi import OSC, OSCError
from gitbuildsys.log import DEBUG

from gbp.rpm.git import GitRepositoryError, RpmGitRepository
from gbp import rpm
from gbp.rpm import SpecFile
from gbp.errors import GbpError

from gitbuildsys.cmd_build import CHANGE_PERSONALITY, SUPPORTEDARCHS, formalize_build_conf, get_profile, get_local_archs


USERID = pwd.getpwuid(os.getuid())[0]
TMPDIR = None

def prepare_depanneur_opts(args):
    '''generate extra options for depanneur'''

    cmd_opts = []
    if args.debug:
        cmd_opts += ['--debug']

    cmd_opts += ['--packaging-dir=%s' % get_packaging_dir(args)]
    cmd_opts += ['--depends']

    return cmd_opts

def prepare_repos_and_build_conf(args, arch, profile):
    '''generate repos and build conf options for depanneur'''

    cmd_opts = []
    cache = Temp(prefix=os.path.join(TMPDIR, 'gbscache'),
                 directory=True)
    cachedir = cache.path
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    log.info('generate repositories ...')

    repos = [i.url for i in profile.repos]

    if args.repositories:
        for repo in args.repositories:
            try:
                if not urlparse.urlsplit(repo).scheme:
                    if os.path.exists(repo):
                        repo = os.path.abspath(os.path.expanduser(repo))
                    else:
                        log.warning('local repo: %s does not exist' % repo)
                        continue
                opt_repo = SafeURL(repo)
            except ValueError as err:
                log.warning('Invalid repo %s: %s' % (repo, str(err)))
            else:
                repos.append(opt_repo)

    if not repos:
        raise GbsError('No package repository specified.')

    archs = get_local_archs(repos)
    if arch not in archs:
        log.warning('No local package repository for arch %s' % arch)

    repoparser = RepoParser(repos, cachedir)
    repourls = repoparser.get_repos_by_arch(arch)
    if not repourls:
        raise GbsError('no available repositories found for arch %s under the '
                       'following repos:\n%s' % (arch, '\n'.join(repos)))
    cmd_opts += [('--repository=%s' % url.full) for url in repourls]

    profile_name = formalize_build_conf(profile.name.replace('profile.', '', 1))
    distconf = os.path.join(TMPDIR, '%s.conf' % profile_name)

    if args.dist:
        buildconf = args.dist
    elif profile.buildconf:
        buildconf = profile.buildconf
    else:
        if repoparser.buildconf is None:
            raise GbsError('failed to get build conf from repos, please '
                           'use snapshot repo or specify build config using '
                           '-D option')
        else:
            buildconf = repoparser.buildconf
            log.info('build conf has been downloaded at:\n      %s' \
                       % distconf)
    try:
        shutil.copy(buildconf, distconf)
    except IOError as err:
        raise GbsError("Failed to copy build conf: %s" % (str(err)))

    if not os.path.exists(distconf):
        raise GbsError('No build config file specified, please specify in '\
                       '~/.gbs.conf or command line using -D')

    # must use abspath here, because build command will also use this path
    distconf = os.path.abspath(distconf)

    if not distconf.endswith('.conf') or '-' in os.path.basename(distconf):
        raise GbsError("build config file must end with .conf, and can't "
                       "contain '-'")
    dist = "'"+os.path.basename(distconf)[:-len('.conf')]+"'"
    cmd_opts += ['--dist=%s' % dist]
    path = "'"+os.path.dirname(distconf)+"'"
    cmd_opts += ['--configdir=%s' % path]

    return cmd_opts

def main(args):
    """gbs depends entry point."""

    global TMPDIR
    TMPDIR = os.path.join(configmgr.get('tmpdir', 'general'), '%s-gbs' % USERID)

    if args.commit and args.include_all:
        raise Usage('--commit can\'t be specified together with '\
                    '--include-all')
    workdir = args.gitdir

    try:
        repo = RpmGitRepository(workdir)
        workdir = repo.path
    except GitRepositoryError:
        pass

    read_localconf(workdir)

    hostarch = os.uname()[4]
    if args.arch:
        buildarch = args.arch
    else:
        buildarch = hostarch
        log.info('No arch specified, using system arch: %s' % hostarch)

    if not buildarch in SUPPORTEDARCHS:
        raise GbsError('arch %s not supported, supported archs are: %s ' % \
                       (buildarch, ','.join(SUPPORTEDARCHS)))

    profile = get_profile(args)

    if args.buildroot:
        build_root = args.buildroot
    elif 'TIZEN_BUILD_ROOT' in os.environ:
        build_root = os.environ['TIZEN_BUILD_ROOT']
    elif profile.buildroot:
        build_root = profile.buildroot
    else:
        build_root = configmgr.get('buildroot', 'general')
    build_root = os.path.expanduser(build_root)
    # transform variables from shell to python convention ${xxx} -> %(xxx)s
    build_root = re.sub(r'\$\{([^}]+)\}', r'%(\1)s', build_root)
    sanitized_profile_name = re.sub("[^a-zA-Z0-9:._-]", "_", profile.name)
    build_root = build_root % {'tmpdir': TMPDIR,
                               'profile': sanitized_profile_name}
    os.environ['TIZEN_BUILD_ROOT'] = os.path.abspath(build_root)

    # get virtual env from system env first
    if 'VIRTUAL_ENV' in os.environ:
        cmd = ['%s/usr/bin/depanneur' % os.environ['VIRTUAL_ENV']]
    else:
        cmd = ['depanneur']

    cmd += ['--arch=%s' % buildarch]

    # check & prepare repos and build conf
    cmd += prepare_repos_and_build_conf(args, buildarch, profile)
    cmd += ['--path=%s' % workdir]

    if hostarch != buildarch and buildarch in CHANGE_PERSONALITY:
        cmd = [CHANGE_PERSONALITY[buildarch]] + cmd

    # Extra depanneur special command options
    cmd += prepare_depanneur_opts(args)

    # Extra options for gbs export
    if args.include_all:
        cmd += ['--include-all']
    if args.commit:
        cmd += ['--commit=%s' % args.commit]

    log.debug("running command: %s" % ' '.join(cmd))
    retcode = os.system(' '.join(cmd))
    if retcode != 0:
        raise GbsError('some packages failed to be generate depends files')
    else:
        log.info('Done')
