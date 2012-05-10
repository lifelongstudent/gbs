#!/usr/bin/python -tt
# vim: ai ts=4 sts=4 et sw=4
#
# Copyright (c) 2011 Intel, Inc.
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

"""Implementation of subcmd: remotebuild
"""

import os
import time
import tempfile
import glob
import shutil
import urlparse

import msger
import runner
import utils
from conf import configmgr
import git
import obspkg
import errors

OSCRC_TEMPLATE = """[general]
apiurl = %(apiurl)s
plaintext_passwd=0
use_keyring=0
http_debug = %(http_debug)s
debug = %(debug)s
gnome_keyring=0
[%(apiurl)s]
user=%(user)s
passx=%(passwdx)s
"""

APISERVER   = configmgr.get('build_server', 'remotebuild')
USER        = configmgr.get('user', 'remotebuild')
PASSWDX     = configmgr.get('passwdx', 'remotebuild')
TMPDIR      = configmgr.get('tmpdir')

def do(opts, args):

    workdir = os.getcwd()
    if len(args) > 1:
        msger.error('only one work directory can be specified in args.')
    if len(args) == 1:
        workdir = args[0]

    tmpdir = '%s/%s' % (TMPDIR, USER)
    if not os.path.exists(tmpdir):
        os.makedirs(tmpdir)

    oscrc = OSCRC_TEMPLATE % {
                "http_debug": 1 if msger.get_loglevel() == 'debug' else 0,
                "debug": 1 if msger.get_loglevel() == 'verbose' else 0,
                "apiurl": APISERVER,
                "user": USER,
                "passwdx": PASSWDX,
            }
    (fd, oscrcpath) = tempfile.mkstemp(dir=tmpdir,prefix='.oscrc')
    os.close(fd)
    f = file(oscrcpath, 'w+')
    f.write(oscrc)
    f.close()
    
    # TODO: check ./packaging dir at first
    specs = glob.glob('%s/packaging/*.spec' % workdir)
    if not specs:
        msger.error('no spec file found under /packaging sub-directory')

    specfile = specs[0] #TODO:
    if len(specs) > 1:
        msger.warning('multiple specfiles found.')

    # get 'name' and 'version' from spec file
    name = utils.parse_spec(specfile, 'name')
    version = utils.parse_spec(specfile, 'version')
    if not name or not version:
        msger.error('can\'t get correct name or version from spec file.')

    if opts.base_obsprj is None:
        # TODO, get current branch of git to determine it
        base_prj = 'Trunk'
    else:
        base_prj = opts.base_obsprj

    if opts.target_obsprj is None:
        target_prj = "home:%s:gbs:%s" % (USER, base_prj)
    else:
        target_prj = opts.target_obsprj

    prj = obspkg.ObsProject(target_prj, apiurl = APISERVER, oscrc = oscrcpath)
    msger.info('checking status of obs project: %s ...' % target_prj)
    if prj.is_new():
        msger.info('creating %s for package build ...' % target_prj)
        try:
            prj.branch_from(base_prj)
        except errors.ObsError, e:
            msger.error('%s' % e)

    msger.info('checking out %s/%s to %s ...' % (target_prj, name, tmpdir))
    localpkg = obspkg.ObsPackage(tmpdir, target_prj, name, APISERVER, oscrcpath)
    oscworkdir = localpkg.get_workdir()
    localpkg.remove_all()

    source = utils.parse_spec(specfile, 'SOURCE0')
    urlres = urlparse.urlparse(source)

    tarball = '%s/%s' % (oscworkdir, os.path.basename(urlres.path))
    msger.info('archive git tree to tarball: %s' % os.path.basename(tarball))
    mygit = git.Git(workdir)
    mygit.archive("%s-%s/" % (name, version), tarball)

    for f in glob.glob('%s/packaging/*' % workdir):
        shutil.copy(f, oscworkdir)

    localpkg.update_local()

    msger.info('commit packaging files to build server ...')
    localpkg.commit ('submit packaging files to obs for OBS building')

    os.unlink(oscrcpath)
    msger.info('local changes submitted to build server successfully')
    msger.info('follow the link to monitor the build progress:\n'
               '  %s/package/show?package=%s&project=%s' \
               % (APISERVER.replace('api', 'build'), name, target_prj))
