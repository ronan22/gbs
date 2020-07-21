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

"""Implementation of subcmd: localbuild
"""

import os
import shutil
import pwd
import re
import urlparse
import glob
import gzip
import requests
from lxml import etree
import xml.etree.cElementTree as ET
import xml.etree.ElementTree as ETP
import subprocess
import re

from gitbuildsys.utils import Temp, Workdir, RepoParser, read_localconf, \
                              guess_spec, show_file_from_rev, \
                              GitRefMappingParser, GitDirFinder, GerritNameMapper
from gitbuildsys.errors import GbsError, Usage
from gitbuildsys.conf import configmgr, MappingConfigParser, encode_passwd
from gitbuildsys.safe_url import SafeURL
from gitbuildsys.cmd_export import get_packaging_dir, config_is_true
from gitbuildsys.log import LOGGER as log
from gitbuildsys.oscapi import OSC, OSCError
from gitbuildsys.log import DEBUG

from gbp.rpm.git import GitRepositoryError, RpmGitRepository
from gbp import rpm
from gbp.rpm import SpecFile
from gbp.errors import GbpError


CHANGE_PERSONALITY = {
    'ia32':  'linux32',
    'i686':  'linux32',
    'i586':  'linux32',
    'i386':  'linux32',
    'ppc':   'powerpc32',
    's390':  's390',
    'sparc': 'linux32',
    'sparcv8': 'linux32',
    }

SUPPORTEDARCHS = [
    'x86_64',
    'i586',
    'armv6l',
    'armv7hl',
    'armv7l',
    'aarch64',
    'mips',
    'mipsel',
    ]

USERID = pwd.getpwuid(os.getuid())[0]
TMPDIR = None

def formalize_build_conf(profile):
    ''' formalize build conf file name from profile'''

    # build conf file name should not start with digital, see:
    # obs-build/Build.pm:read_config_dist()
    start_digital_re = re.compile(r'^[0-9]')
    if start_digital_re.match(profile):
        profile = 'tizen%s' % profile

    # '-' is not allowed, so replace with '_'
    return profile.replace('-', '_')

def get_binary_name_from_git(args, package_dirs):
    ''' get binary rpm name from specified git package'''

    binary_list = []
    packaging_dir = get_packaging_dir(args)
    if args.commit:
        commit = args.commit
    elif args.include_all:
        commit = 'WC.UNTRACKED'
    else:
        commit = 'HEAD'

    for package_dir in package_dirs:
        main_spec, rest_specs = guess_spec(package_dir, packaging_dir,
                                           None, commit)
        rest_specs.append(main_spec)
        for spec in rest_specs:
            if args.include_all:
                spec_to_parse = os.path.join(package_dir, spec)
            else:
                content = show_file_from_rev(package_dir, spec, commit)
                if content is None:
                    raise GbsError('failed to checkout %s from commit: %s' %
                                   (spec, commit))
                tmp_spec = Temp(content=content)
                spec_to_parse = tmp_spec.path

            try:
                spec = rpm.SpecFile(spec_to_parse)
            except GbpError as err:
                raise GbsError('%s' % err)
            binary_list.append(spec.name)

    return binary_list

def prepare_repos_and_build_conf(args, arch, profile):
    '''generate repos and build conf options for depanneur'''

    cmd_opts = []
    cache = Temp(prefix=os.path.join(TMPDIR, 'gbscache'),
                 directory=True)
    cachedir = cache.path
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    log.info('generate repositories ...')

    if args.skip_conf_repos:
        repos = []
    else:
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

#refine code with SAM check.

def prepare_depanneur_simple_opts(args):
    '''generate extra simple options for depanneur'''
    cmd_opts = []
    if args.exclude:
        cmd_opts += ['--exclude=%s' % i for i in args.exclude.split(',')]
    if args.exclude_from_file:
        cmd_opts += ['--exclude-from-file=%s' % args.exclude_from_file]
    if args.overwrite:
        cmd_opts += ['--overwrite']
    if args.clean_once:
        cmd_opts += ['--clean-once']
    if args.clean_repos:
        cmd_opts += ['--clean-repos']
    if args.debug:
        cmd_opts += ['--debug']
    if args.incremental:
        cmd_opts += ['--incremental']
    if args.no_configure:
        cmd_opts += ['--no-configure']
    if args.keep_packs:
        cmd_opts += ['--keep-packs']
    if args.use_higher_deps:
        cmd_opts += ['--use-higher-deps']
    if args.not_export_source:
        cmd_opts += ['--not-export-source']
    if args.baselibs:
        cmd_opts += ['--baselibs']
    if args.skip_srcrpm:
        cmd_opts += ['--skip-srcrpm']
    if args.fail_fast:
        cmd_opts += ['--fail-fast']
    if args.keepgoing:
        cmd_opts += ['--keepgoing=%s' % args.keepgoing]
    if args.disable_debuginfo:
        cmd_opts += ['--disable-debuginfo']
    if args.style:
        cmd_opts += ['--style=%s' % args.style]
    if args.export_only:
        cmd_opts += ['--export-only']

    return cmd_opts

def prepare_depanneur_opts(args):
    '''generate extra options for depanneur'''

    cmd_opts = prepare_depanneur_simple_opts(args)
    #
    if args.package_list:
        package_list = args.package_list.split(',')
        binary_list = get_binary_name_from_git(args, package_list)
        args.binary_list += ','+ ','.join(binary_list)
    if args.package_from_file:
        if not os.path.exists(args.package_from_file):
            raise GbsError('specified package list file %s not exists' % \
                           args.package_from_file)
        with open(args.package_from_file) as fobj:
            pkglist = [pkg.strip() for pkg in fobj.readlines() if pkg.strip()]
            binary_list = get_binary_name_from_git(args, pkglist)
        args.binary_list += ',' + ','.join(binary_list)
    if args.binary_list:
        blist = [i.strip() for i in args.binary_list.split(',')]
        cmd_opts += ['--binary-list=%s' % ','.join(blist)]
    if args.binary_from_file:
        if not os.path.exists(args.binary_from_file):
            raise GbsError('specified binary list file %s not exists' % \
                        args.binary_from_file)
        cmd_opts += ['--binary-from-file=%s' % args.binary_from_file]
    if args.deps:
        cmd_opts += ['--deps']
    if args.rdeps:
        cmd_opts += ['--rdeps']

    if args.kvm:
        cmd_opts += ['--clean']
        cmd_opts += ['--vm-type=kvm']
        cmd_opts += ['--vm-memory=%s' % args.vm_memory]
        cmd_opts += ['--vm-disk=%s' % args.vm_disk]
        cmd_opts += ['--vm-swap=%s' % args.vm_swap]
        cmd_opts += ['--vm-diskfilesystem=%s' % args.vm_diskfilesystem]
        if not os.path.exists(args.vm_initrd):
            raise GbsError("Check file to exists vm-initrd")
        cmd_opts += ['--vm-initrd=%s' % args.vm_initrd]
        if not os.path.exists(args.vm_kernel):
            raise GbsError("Check file to exists vm-kernel")
        cmd_opts += ['--vm-kernel=%s' % args.vm_kernel]

    if args.icecream > 0:
        cmd_opts += ['--icecream=%s' % args.icecream]

    cmd_opts += ['--threads=%s' % args.threads]
    if args.kvm:
        loopdev = len([name for name in os.listdir('/dev') if bool(re.search("loop[0-9]",name))])
        if not args.threads < loopdev:
            raise GbsError('When using the kvm, loop device should be larger than the threads option.')
    cmd_opts += ['--packaging-dir=%s' % get_packaging_dir(args)]

    return cmd_opts

def get_profile(args):
    """
    Get the build profile to be used
    """
    if args.profile:
        profile_name = args.profile if args.profile.startswith("profile.") \
                                    else "profile." + args.profile
        profile = configmgr.build_profile_by_name(profile_name)
    else:
        profile = configmgr.get_current_profile()
    return profile

def get_local_archs(repos):
    """
    Get the supported arch from prebuilt toolchains
      > get primary file
      > get archs

    Each toolchain should contain about 128 packages,
    it is insufficient if less than that.
    """
    def get_primary_file_from_local(repos):
        def find_primary(repo):
            pattern = os.path.join(repo, 'repodata', '*primary.*.gz')
            files = glob.glob(pattern)
            if files:
                return files[0]

        for repo in repos:
            if not repo.startswith('http'):
                pri = find_primary(repo)
                if pri:
                    yield pri

    def extract_arch(primary):
        with gzip.open(primary) as fobj:
            root = ET.fromstring(fobj.read())

        xmlns = re.sub(r'metadata$', '', root.tag)
        for elm in root.getiterator('%spackage' % xmlns):
            arch = elm.find('%sarch' % xmlns).text
            if re.match(r'i[3-6]86', arch):
                yield 'i586'
            elif arch not in ('noarch', 'src'):
                yield arch

    archs = set()
    for pri in get_primary_file_from_local(repos):
        for arch in extract_arch(pri):
            archs.add(arch)

    return archs

def get_profile_url(snapshot):
    """
    get profile url according to snapshot.
    """
    profile_url = ''
    if snapshot:
        if snapshot.startswith('tizen-3.0-mobile'):
            profile_url = 'http://download.tizen.org/snapshots/tizen/3.0-mobile/' + snapshot
        elif snapshot.startswith('tizen-3.0-tv'):
            profile_url = 'http://download.tizen.org/snapshots/tizen/3.0-tv/' + snapshot
        elif snapshot.startswith('tizen-3.0-wearable'):
            profile_url = 'http://download.tizen.org/snapshots/tizen/3.0-wearable/' + snapshot
        elif snapshot.startswith('tizen-3.0-ivi'):
            profile_url = 'http://download.tizen.org/snapshots/tizen/3.0-ivi/' + snapshot
        elif snapshot.startswith('tizen-unified'):
            profile_url = 'http://download.tizen.org/snapshots/tizen/unified/' + snapshot
        else:
            raise GbsError('unkown snapshot: %s, please check' %snapshot)

        res = requests.get(profile_url)
        if res.status_code == 404:
            raise GbsError('specified snapshot: %s does not exist, please check' %profile_url)


    return profile_url

def create_autoconf(arch, snapshot, full_build):
    """
    Create ~/.gbs.conf.auto for user
    """
    url = ''

    profile_url = get_profile_url(snapshot)

    log.info("sync git-ref-mapping from review.tizen.org to get reference binary id")
    refparser = GitRefMappingParser()
    ref_meta = refparser.parse()

    mapparser = MappingConfigParser('/usr/share/gbs/mapping.conf')
    obs_meta = mapparser.GetObsMapping()
    prefix_meta = mapparser.GetPrefixMapping()
    repo_meta = mapparser.GetRepoMapping()
    profile_meta = mapparser.GetProfileMapping()
    source_meta = mapparser.GetSourceMapping()
    osc_meta = mapparser.GetOscMapping()

    content = ''
    default = ''
    if arch in ['armv7l', 'aarch64']:
        default = 'profile.unified_standard'
    elif arch in ['i586', 'x86_64']:
        default = 'profile.unified_emulator'
    else:
        default = 'profile.error'

    content += '[general]\nfallback_to_native = true\nprofile = ' + default + '\n'
    repos_map = {}
    for k, v in obs_meta.iteritems():
        ref_id = ref_meta.get(v)
        if ref_id == None:
            ref_id = 'latest'

        prefix = prefix_meta.get(k)
        if prefix == None:
            continue

        if ref_id == 'latest':
           prefix = os.path.dirname(prefix) + '/'

        url = prefix + ref_id
        if snapshot:
            if os.path.dirname(url) == os.path.dirname(profile_url):
                url = profile_url

        repos = repo_meta.get(k)
        if repos == None:
            continue


        repotypes = repos.split(',')
        bid = os.path.basename(url)
        for repo in repotypes:
            repos_map[k + '_' + repo.replace('-', '_')] = url + '/repos/' + repo + '/packages/'
            content += '[repo.' + k + '_' + repo + ']\n'
            content += 'url = ' + url + '/repos/' + repo + '/packages/\n'
            content += '[repo.' + k + '_' + repo + '_source]\n'
            content += 'url = ' + url + '/builddata/manifest/' + bid + '_' + repo + '.xml\n'
            content += '[repo.' + k + '_' + repo + '_debug]\n'
            content += 'url = ' + url + '/repos/' + repo + '/debug/\n'
            content += '[repo.' + k + '_' + repo + '_depends]\n'
            content += 'url = ' + url + '/builddata/depends/dep_graph/' + repo + '/' + arch + '/\n'
            content += '[repo.' + k + '_' + repo + '_pkgs]\n'
            content += 'url = ' + url + '/builddata/depends/' + v + '_' + repo + '_' + arch + '_revpkgdepends.xml\n'

    for k, v in profile_meta.iteritems():
        content += '[profile.' + k + ']\n'
        if full_build:
            v = v[:v.index('repo.' + k) - 1]

        content += 'repos = ' + v + '\n'
        source = source_meta.get(k)
        if source != None:
            attrs = source.split(',')
            content += 'source = ' + attrs[0] + '\n'
            content += 'depends = ' + attrs[1] + '\n'
            content += 'pkgs = ' + attrs[2] + '\n'

        content += 'obs = obs.tizen\n'
        v = osc_meta.get(k)
        if v != None:
            attrs = v.split(',')
            content += 'obs_prj = ' + attrs[0] + '\n'
            content += 'obs_repo = ' + attrs[1] + '\n'

    content += '[obs.tizen]\nurl = https://build.tizen.org\nuser = obs_viewer\npasswd = obs_viewer\n'

    fpath = os.path.expanduser('~/.gbs.conf.auto')
    with open(fpath, 'w') as wfile:
        wfile.write(content)

    configmgr.add_conf(fpath)

    return repos_map

def sync_source(exclude_pkgs, pkgs, manifest_url, path):
    if pkgs != None:
        if len(pkgs) == 0:
            return

    cmd = 'repo init -u https://git.tizen.org/cgit/scm/manifest -b tizen -m unified_standard.xml'
    with Workdir(path):
        ret = os.system(cmd)
        if ret != 0:
            raise GbsError("failed to run %s in %s" % (' '.join(cmd), path))

    out_file = path + '/.repo/manifests/unified_standard.xml.new'
    in_file = path + '/.repo/manifests/unified_standard.xml'
    with open(out_file, 'w') as f:
        with open(in_file, 'r') as i:
            for line in i.readlines():
                if 'metadata.xml' not in line and 'prebuilt.xml' not in line:
                    f.write(line)

    shutil.move(out_file, in_file)
    r = requests.get(manifest_url)
    if r.status_code == 404:
        log.error("manifest %s not found" %manifest_url)
        return

    old = path + '/.repo/manifests/unified/standard/projects.xml'
    new = path + '/.repo/manifests/unified/standard/projects.xml.new'
    with open(new, "w") as f:
        f.write(r.content)

    log.info('use %s as projects.xml' %manifest_url)
    with open(new, 'r') as f:
        with open(old, 'w') as i:
            for line in f.readlines():
                if exclude_pkgs != None:
                    if 'revision' in line:
                        k = line.index('"', line.index('path'))
                        abs_path = line[k + 1:line.index('"', k + 1)]
                        if abs_path in exclude_pkgs:
                            continue

                    i.write(line)

                if pkgs != None:
                    if 'revision' in line:
                        k = line.index('"', line.index('path'))
                        abs_path = line[k + 1:line.index('"', k + 1)]
                        if abs_path not in pkgs:
                            continue

                    i.write(line)

    cmd = 'repo sync'
    with Workdir(path):
        ret = os.system(cmd)
        if ret != 0:
            raise GbsError("failed to run %s in %s" % (' '.join(cmd), path))

def prepare_fullbuild_source(profile, pkgs, url, download_path):
    """
    prepare full build source
    """
    sync_source(pkgs, None, url, download_path)

def prepare_depsbuild_source(gnmapper, profile, arch, pkgs, url, download_path):
    """
    prepare deps build source
    """
    deps = set([])
    deps_path = []
    try:
        for pkg in pkgs:
            depurl = profile.depends.url + pkg + '.full_edges.vis_input.js'
            r = requests.get(depurl)
            if r.status_code == 404:
                log.error('get depends from %s failed' %depurl)
                continue

            match = re.findall("label: '.*'", r.content)
            if not match:
                continue

            for m in match:
                dep = m[m.index("'") + 1:m.rindex("'")]
                if dep == pkg:
                    continue

                if dep not in deps:
                    deps.add(dep)

        log.info("what depends on number:%d --> %s" %(len(deps), deps))
        for pkg in deps:
            gerrit_name = gnmapper.get_gerritname_by_obsname(pkg)
            if gerrit_name == None:
                log.warning('can not get gerrit name for pkg:%s' %pkg)
                continue

            deps_path.append(gnmapper.get_gerritname_by_obsname(pkg))
    except OSCError as err:
        raise GbsError(str(err))

    sync_source(None, deps_path, url, download_path)

def prepare_depanneur_cmd(args, buildarch, profile, workdir):
    '''Prepare depanneur commond'''
    # get virtual env from system env first
    if 'VIRTUAL_ENV' in os.environ:
        cmd = ['%s/usr/bin/depanneur' % os.environ['VIRTUAL_ENV']]
    else:
        cmd = ['depanneur']

    cmd += ['--arch=%s' % buildarch]

    if args.clean:
        cmd += ['--clean']

    # check & prepare repos and build conf
    if not args.noinit:
        cmd += prepare_repos_and_build_conf(args, buildarch, profile)
    else:
        cmd += ['--noinit']

    cmd += ['--path=%s' % "'"+str(workdir)+"'"]

    if args.ccache:
        cmd += ['--ccache']

    if args.extra_packs:
        cmd += ['--extra-packs=%s' % args.extra_packs]

    hostarch = os.uname()[4]
    if hostarch != buildarch and buildarch in CHANGE_PERSONALITY:
        cmd = [CHANGE_PERSONALITY[buildarch]] + cmd

    # Extra depanneur special command options
    cmd += prepare_depanneur_opts(args)

    # Extra options for gbs export
    if args.include_all:
        cmd += ['--include-all']
    if args.commit:
        cmd += ['--commit=%s' % args.commit]

    if args.upstream_branch:
        cmd += ['--upstream-branch=%s' % args.upstream_branch]
    if args.upstream_tag:
        cmd += ['--upstream-tag=%s' % args.upstream_tag]

    if args.conf and args.conf != '.gbs.conf':
        fallback = configmgr.get('fallback_to_native')
    elif args.full_build or args.deps_build:
        fallback = configmgr.get('fallback_to_native')
    else:
        fallback = ''
    if args.fallback_to_native or config_is_true(fallback):
        cmd += ['--fallback-to-native']

    if args.squash_patches_until:
        cmd += ['--squash-patches-until=%s' % args.squash_patches_until]
    if args.no_patch_export:
        cmd += ['--no-patch-export']

    if args.define:
        cmd += [('--define="%s"' % i) for i in args.define]
    if args.spec:
        cmd += ['--spec=%s' % args.spec]

    # Determine if we're on devel branch
    orphan_packaging = configmgr.get('packaging_branch', 'orphan-devel')
    if orphan_packaging:
        cmd += ['--spec-commit=%s' % orphan_packaging]

    return cmd

def init_buildroot(args, profile):
    '''init build root'''
    if args.buildroot:
        build_root = args.buildroot
    elif 'TIZEN_BUILD_ROOT' in os.environ:
        build_root = os.environ['TIZEN_BUILD_ROOT']
    elif profile.buildroot:
        build_root = profile.buildroot
    else:
        build_root = configmgr.get('buildroot', 'general')
    build_root = os.path.expanduser(build_root)

    return build_root

def main(args):
    """gbs build entry point."""
    global TMPDIR
    TMPDIR = os.path.join(configmgr.get('tmpdir', 'general'), '%s-gbs' % USERID)

    if args.commit and args.include_all:
        raise Usage('--commit can\'t be specified together with '\
                    '--include-all')
    if args.noinit and (args.clean or args.clean_once):
        raise Usage('--noinit can\'t be specified together with '\
                    '--clean or --clean-once')
    workdir = args.gitdir

    try:
        repo = RpmGitRepository(workdir)
        workdir = repo.path
    except GitRepositoryError:
        if args.spec:
            raise GbsError("git project can't be found for --spec, "
                           "give it in argument or cd into it")

    repos_map = {}
    if not args.conf:
        if args.full_build or args.deps_build:
            repos_map = create_autoconf(args.arch, args.snapshot, args.full_build)
            log.info("Create ~/.gbs.conf.auto using reference binary id")

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
    if args.full_build or args.deps_build:
        if profile.source == None:
            raise GbsError('full build/deps build option must specify source repo in gbs.conf')

        download_path = Temp(prefix=os.path.expanduser('~/gbs-build'),
                     directory=True)
        local_pkgs = []
        gitf = GitDirFinder(workdir)

        profile_name = formalize_build_conf(profile.name.replace('profile.', '', 1))
        profile_repo = repos_map.get(profile_name)

        cache = Temp(prefix=os.path.join(TMPDIR, 'gbscache'),
                     directory=True)
        cachedir = cache.path
        repoparser = RepoParser([SafeURL(profile_repo)], cachedir)
        distconf = os.path.join(download_path.path, '%s.conf' % profile_name)

        if repoparser.buildconf is None:
            raise GbsError('failed to get build conf from repos, please '
                           'use snapshot repo or specify build config using '
                           '-D option')
        else:
            buildconf = repoparser.buildconf
        try:
            shutil.copy(buildconf, distconf)
            log.info('build conf has been downloaded at:\n      %s' \
                       % distconf)
        except IOError as err:
            raise GbsError("Failed to copy build conf: %s" % (str(err)))

        profile.buildconf = distconf

        r = requests.get(profile.pkgs.url)
        if r.status_code == 404:
            raise GbsError('get pkg xml from %s failed' %profile.pkgs.url)
        exclude_pkgs = []
        if args.exclude:
            exclude_pkgs = args.exclude.split(',')
        gnmapper = GerritNameMapper(r.content, repoparser.primaryxml)
        for spec_file in gitf.specs:
            try:
                spec = SpecFile(spec_file)
                if spec.name in exclude_pkgs:
                    continue

                if args.full_build:
                    pkg = gnmapper.get_gerritname_by_srcname(spec.name)
                else:
                    pkg = gnmapper.get_pkgname_by_srcname(spec.name)
                if pkg != None:
                    local_pkgs.append(pkg)
                else:
                    log.error('package %s parse failed' %spec.name)
            except GbpError as err:
                log.warning('gbp parse spec failed. %s' % err)


        gnmapper = GerritNameMapper(r.content, repoparser.primaryxml)
        if args.full_build:
            prepare_fullbuild_source(profile, local_pkgs, profile.source.url, download_path.path)
        else:
            if len(local_pkgs) == 0:
                raise GbsError('deps build option must has local packages')

            prepare_depsbuild_source(gnmapper, profile, args.arch, local_pkgs, profile.source.url, download_path.path)

        for path in gitf.paths:
            shutil.copytree(path, os.path.join(download_path.path, os.path.basename(path)))

        workdir = download_path.path
        curdir = os.getcwd()
        os.chdir(workdir)

    build_root = init_buildroot(args, profile)
    # transform variables from shell to python convention ${xxx} -> %(xxx)s
    build_root = re.sub(r'\$\{([^}]+)\}', r'%(\1)s', build_root)
    sanitized_profile_name = re.sub("[^a-zA-Z0-9:._-]", "_", profile.name)
    build_root = build_root % {'tmpdir': TMPDIR,
                               'profile': sanitized_profile_name}
    if profile.exclude_packages:
        log.info('the following packages have been excluded build from gbs '
                 'config:\n   %s' % '\n   '.join(profile.exclude_packages))
        if args.exclude:
            args.exclude += ',' + ','.join(profile.exclude_packages)
        else:
            args.exclude = ','.join(profile.exclude_packages)
    os.environ['TIZEN_BUILD_ROOT'] = os.path.abspath(build_root)

    #prepare depanneur commond
    cmd = prepare_depanneur_cmd(args, buildarch, profile, workdir)

    log.debug("running command: %s" % ' '.join(cmd))
    retcode = os.system(' '.join(cmd))
    if args.full_build or args.deps_build:
        os.chdir(curdir)
    if retcode != 0:
        raise GbsError('some packages failed to be built')
    else:
        log.info('Done')
