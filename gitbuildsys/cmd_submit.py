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

"""Implementation of subcmd: submit"""

import os
import time

from gitbuildsys import msger, errors

from gbp.rpm.git import GitRepositoryError, RpmGitRepository


def main(args):
    """gbs submit entry point."""

    workdir = args.gitdir

    if not args.msg:
        msger.error("argument for -m option can't be empty")

    try:
        repo = RpmGitRepository(workdir)
        commit = repo.rev_parse(args.commit)
        current_branch = repo.get_branch()
    except GitRepositoryError, err:
        msger.error(str(err))

    try:
        upstream = repo.get_upstream_branch(current_branch)
    except GitRepositoryError:
        upstream = None
        pass
    if not args.remote:
        if upstream:
            args.remote = upstream.split('/')[0]
        else:
            msger.info("no upstream set for the current branch, using "
                       "'origin' as the remote server")
            args.remote = 'origin'
    if not args.target:
        if upstream and upstream.startswith(args.remote):
            args.target = os.path.basename(upstream)
        else:
            msger.warning("Can't find upstream branch for current branch "
                          "%s. Gbs uses the local branch name as the target. "
                          "Please consider to use git-branch --set-upstream "
                          "to set upstream remote branch." % current_branch)
            args.target = current_branch

    try:
        if args.target == 'master':
            args.target = 'trunk'
        tagname = 'submit/%s/%s' % (args.target, time.strftime( \
                                    '%Y%m%d.%H%M%S', time.gmtime()))
        msger.info('creating tag: %s' % tagname)
        repo.create_tag(tagname, msg=args.msg, commit=commit, sign=args.sign,
                                                 keyid=args.user_key)
    except GitRepositoryError, err:
        msger.error('failed to create tag %s: %s ' % (tagname, str(err)))

    try:
        msger.info("pushing tag to remote '%s'" % args.remote)
        repo.push_tag(args.remote, tagname)
    except GitRepositoryError, err:
        repo.delete_tag(tagname)
        msger.error('failed to push tag %s :%s' % (tagname, str(err)))

    msger.info('done.')
