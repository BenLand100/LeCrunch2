#!/usr/bin/env python
# LeCrunch2 
# Copyright (C) 2014 Benjamin Land
#
# based on
#
# LeCrunch
# Copyright (C) 2010 Anthony LaTorre 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import string
import struct
import socket
import h5py
import numpy
import config
from lecroy import LeCroyScope

def fetch(filename, nevents, nsequence):
    '''
    Fetch and save waveform traces from the oscilloscope.
    '''
    scope = LeCroyScope(config.ip, timeout=config.timeout)
    scope.clear()
    scope.set_sequence_mode(nsequence)
    channels = scope.get_channels()
    settings = scope.get_settings()

    if 'ON' in settings['SEQUENCE']:
        sequence_count = int(settings['SEQUENCE'].split(',')[1])
    else:
        sequence_count = 1
        
    if nsequence != sequence_count:
        print 'Could not configure sequence mode properly'
    if sequence_count != 1:
        print 'Using sequence mode with %i traces per aquisition' % sequence_count 
    
    f = {}
    for channel in channels:
        f[channel] = open('%s.ch%s.traces'%(filename,channel),'wb')
    params_pattern = '=IBdddd' # (num_samples, sample_bytes, v_off, v_scale, h_off, h_scale, [samples]) ...
    try:
        i = 0
        while i < nevents:
            print '\rfetching event: %i' % i,
            sys.stdout.flush()
            try:
                scope.trigger()
                for channel in channels:
                    wave_desc,wave_array = scope.get_waveform(channel)
                    num_samples = wave_desc['wave_array_count']//sequence_count
                    traces = wave_array.reshape(sequence_count, wave_array.size//sequence_count)
                    out = f[channel]
                    for n in xrange(0,sequence_count):
                        out.write(struct.pack(params_pattern,num_samples,wave_desc['dtype'].itemsize,wave_desc['vertical_offset'], wave_desc['vertical_gain'], -wave_desc['horiz_offset'], wave_desc['horiz_interval']))
                        traces[n].tofile(out)
                    
            except (socket.error) as e:
                print '\n' + str(e)
                scope.clear()
                continue
            i += sequence_count
    except KeyboardInterrupt:
        print '\rUser interrupted fetch early'
    except Exception as e:
        print "\rUnexpected error:", e
    finally:
        print '\r', 
        for channel in channels:
            f[channel].close()
        scope.clear()
        return i

if __name__ == '__main__':
    import optparse

    usage = "usage: %prog <filename/prefix> [-n] [-s]"
    parser = optparse.OptionParser(usage, version="%prog 0.1.0")
    parser.add_option("-n", type="int", dest="nevents",
                      help="number of events to capture in total", default=1000)
    parser.add_option("-s", type="int", dest="nsequence",
                      help="number of sequential events to capture at a time", default=1)
    parser.add_option("--time", action="store_true", dest="time",
                      help="append time string to filename", default=False)
    (options, args) = parser.parse_args()

    if len(args) < 1:
        sys.exit(parser.format_help())
    
    if options.nevents < 1 or options.nsequence < 1:
        sys.exit("Arguments to -s or -n must be positive")
    
    filename = args[0] + '_' + string.replace(time.asctime(time.localtime()), ' ', '-') if options.time else args[0]
    print 'Saving to file %s' % filename

    start = time.time()
    count = fetch(filename, options.nevents, options.nsequence)
    elapsed = time.time() - start
    if count > 0:
        print 'Completed %i events in %.3f seconds.' % (count, elapsed)
        print 'Averaged %.5f seconds per acquisition.' % (elapsed/count)
