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

import os
from subprocess import *

import msger

def runtool(cmdln_or_args, catch=1):
    """ wrapper for most of the subprocess calls
    input:
        cmdln_or_args: can be both args and cmdln str (shell=True)
        catch: 0, quitely run
               1, only STDOUT
               2, only STDERR
               3, both STDOUT and STDERR
    return:
        (rc, output)
        if catch==0: the output will always None
    """

    if catch not in (0, 1, 2, 3):
        # invalid catch selection, will cause exception, that's good
        return None

    if isinstance(cmdln_or_args, list):
        cmd = cmdln_or_args[0]
        shell = False
    else:
        import shlex
        cmd = shlex.split(cmdln_or_args)[0]
        shell = True

    if catch != 3:
        dev_null = os.open("/dev/null", os.O_WRONLY)

    if catch == 0:
        sout = dev_null
        serr = dev_null
    elif catch == 1:
        sout = PIPE
        serr = dev_null
    elif catch == 2:
        sout = dev_null
        serr = PIPE
    elif catch == 3:
        sout = PIPE
        serr = STDOUT

    try:
        p = Popen(cmdln_or_args, stdout=sout, stderr=serr, shell=shell)
        out = p.communicate()[0]
        if out is None:
            out = ''
    except OSError, e:
        if e.errno == 2:
            # [Errno 2] No such file or directory
            msger.error('Cannot run command: %s, lost dependency?' % cmd)
        else:
            raise # relay
    finally:
        if catch != 3:
            os.close(dev_null)

    return (p.returncode, out)

def show(cmdln_or_args):
    # show all the message using msger.verbose

    rc, out = runtool(cmdln_or_args, catch=3)

    if isinstance(cmdln_or_args, list):
        cmd = ' '.join(cmdln_or_args)
    else:
        cmd = cmdln_or_args

    msg =  'running command: "%s"' % cmd
    if out: out = out.strip()
    if out:
        msg += ', with output::'
        msg += '\n  +----------------'
        for line in out.splitlines():
            msg += '\n  | %s' % line
        msg += '\n  +----------------'

    msger.verbose(msg)
    return rc

def outs(cmdln_or_args, catch=1):
    # get the outputs of tools
    return runtool(cmdln_or_args, catch)[1].strip()

def quiet(cmdln_or_args):
    return runtool(cmdln_or_args, catch=0)[0]

def embed(cmdln_or_args):
    # embed shell script into python frame code

    if isinstance(cmdln_or_args, list):
        args = cmdln_or_args
    else:
        import shlex
        args = shlex.split(cmdln_or_args)

    try:
        sts = call(args)
    except OSError, e:
        if e.errno == 2:
            # [Errno 2] No such file or directory
            msger.error('Cannot run command: %s, lost dependency?' % args[0])
        else:
            raise # relay

    return sts