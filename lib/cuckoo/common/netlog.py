# Copyright (C) 2010-2012 Cuckoo Sandbox Developers.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import struct

from lib.cuckoo.common.logtbl import table as LOGTBL
from lib.cuckoo.common.utils import get_filename_from_path, time_from_cuckoomon

class NetlogParser(object):
    def __init__(self, handler):
        self.handler = handler

        self.formatmap = {
            's': self.read_string,
            'S': self.read_string,
            'u': self.read_string,
            'U': self.read_string,
            'b': self.read_buffer,
            'B': self.read_buffer,
            'i': self.read_int32,
            'l': self.read_int32,
            'L': self.read_int32,
            'p': self.read_ptr,
            'P': self.read_ptr,
            'o': self.read_string,
            'O': self.read_string,
            'a': None,
            'A': None,
            'r': self.read_registry,
            'R': self.read_registry,
        }

    def read_next_message(self):
        apiindex, status = struct.unpack('BB', self.handler.read(2))
        returnval, tid, timediff = struct.unpack('III', self.handler.read(12))
        context = (apiindex, status, returnval, tid, timediff)

        if apiindex == 0:
            # new process message
            timestring = time_from_cuckoomon(self.read_string())
            pid = self.read_int32()
            ppid = self.read_int32()
            modulepath = self.read_string()
            procname = get_filename_from_path(modulepath)
            self.handler.log_process(context, timestring, pid, ppid, modulepath, procname)

        elif apiindex == 1:
            # new thread message
            pid = self.read_int32()
            self.handler.log_thread(context, pid)

        else:
            # actual API call
            apiname, modulename, parseinfo = LOGTBL[apiindex]
            formatspecifiers, argnames = parseinfo[0], parseinfo[1:]
            arguments = []
            for pos in range(len(formatspecifiers)):
                fs = formatspecifiers[pos]
                argname = argnames[pos]
                fn = self.formatmap.get(fs, None)
                if fn:
                    r = fn()
                    arguments.append((argname, r))
                else:
                    log.warning('No handler for format specifier {0} on apitype {1}'.format(fs,apiname))

            self.handler.log_call(context, apiname, modulename, arguments)

        return True

    def read_int32(self):
        """Reads a 32bit integer from the socket."""
        return struct.unpack('I', self.handler.read(4))[0]

    def read_ptr(self):
        """Read a pointer from the socket."""
        value = self.read_int32()
        return '0x%08x' % value

    def read_string(self):
        """Reads an utf8 string from the socket."""
        length, maxlength = struct.unpack('II', self.handler.read(8))
        s = self.handler.read(length)
        if maxlength > length: s += '... (truncated)'
        return s

    def read_buffer(self):
        """Reads a memory socket from the socket."""
        length, maxlength = struct.unpack('II', self.handler.read(8))
        # only return the maxlength, as we don't log the actual buffer right now
        return maxlength

    def read_registry(self):
        """Read logged registry data from the socket."""
        typ = struct.unpack('H', self.handler.read(2))[0]
        # do something depending on type
        return typ

    def read_list(self, fn):
        """Reads a list of _fn_ from the socket."""
        count = struct.unpack('H', self.handler.read(2))[0]
        ret, length = [], 0
        for x in xrange(count):
            item = fn()
            ret.append(item)
        return ret
