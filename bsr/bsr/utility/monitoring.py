#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

"""Query Monitoring System"""

import os
import subprocess
import signal


class Monitoring:
    """This class does blah blah."""

    pid = None

    def __init__(self):
        """Entry point"""

        self.pid = 9999999999

    # pylint: disable=R0201
    def query_cpu_usage(self, target_file):
        """Retrieve CPU usage"""

        values = []

        if os.path.isfile(target_file):
            with open(target_file, 'r') as hw_rec:
                for item in hw_rec.readlines()[1:]:
                    tstamp, cpu_usage, mem_usage = item.strip().split(',')
                    values.append([int(tstamp), \
                                   round(float(cpu_usage), 2), round(float(mem_usage), 2)])

        return values

    def start_recording(self, target_file):
        """Recording CPU usage"""

        self.cleanup_record(target_file)

        stringed_command = """import time, psutil
while True:
    with open('__DEST__', 'a') as wf:
        wf.write('{},{},{}\\n'.format(int(time.time()),
            round(psutil.cpu_percent(interval=5), 2),
            round(float(psutil.virtual_memory().used)/1024/1024/1024, 2)))
    if sum(1 for line in open('__DEST__')) > 17280:
         break
    try:
        if len([x.name() for x in psutil.process_iter() if 'depanneur' in x.name()]) <= 0:
            break
    except Exception as err:
        pass
""".replace('__DEST__', target_file)

        pid = subprocess.Popen(['python', '-c', stringed_command]).pid
        with open(target_file, 'w') as record_file:
            record_file.write('{}\n'.format(pid))

        self.pid = pid

        return pid

    def stop_recording(self, pid):
        """Stop recording by kill the process"""

        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

        self.pid = None

    def cleanup_record(self, target_file, preserve_file=False):
        """Remove log file"""

        if os.path.isfile(target_file):
            with open(target_file, 'r') as record_file:
                pid = int(record_file.readline().strip())
            self.stop_recording(pid)
            if preserve_file is False and os.path.isfile(target_file):
                os.remove(target_file)

    def stop_recording_without_cleanup(self, target_file):
        """Stop the process"""

        self.cleanup_record(target_file, preserve_file=True)
