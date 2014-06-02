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
import struct
import socket
import h5py
import numpy
import config
from lecroy import LeCroyScope

def fetch(filename, nevents):
    '''
    Fetch and save waveform traces from the oscilloscope.
    '''
    scope = LeCroyScope(config.ip, timeout=config.timeout)
    scope.clear()
    channels = scope.get_channels()
    settings = scope.get_settings()

    if 'ON' in settings['SEQUENCE']:
        sequence_count = int(settings['SEQUENCE'].split(',')[1])
        if sequence_count != 1:
            raise Exception('sequence count must be 1 (for now).')
    
    f = h5py.File(filename, 'w')
    for command, setting in settings.items():
        f.attrs[command] = setting
    current_dim = {}
    for channel in channels:
        wave_desc = scope.get_wavedesc(channel)
        current_dim[channel] = wave_desc['wave_array_count']
        f.create_dataset("c%i_samples"%channel, (nevents,current_dim[channel]), dtype=wave_desc['dtype'], compression='gzip', maxshape=(nevents,None))
        for key, value in wave_desc.items():
            try:
                f["c%i_samples"%channel].attrs[key] = value
            except ValueError:
                pass
        f.create_dataset("c%i_vert_offset"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_vert_scale"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_horiz_offset"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_horiz_scale"%channel, (nevents,), dtype='f8')
        f.create_dataset("c%i_num_samples"%channel, (nevents,), dtype='f8')
        
    start = time.time()
    try:
        i = 0
        while i < nevents:
            print '\rfetching event: %i' % i,
            sys.stdout.flush()
            try:
                scope.trigger()
                for channel in channels:
                    wave_desc,wave_array = scope.get_waveform(channel)
                    num_samples = wave_desc['wave_array_count']
                    if current_dim[channel] < num_samples:
                        current_dim[channel] = num_samples
                        f['c%i_samples'%channel].resize(current_dim[channel],1)
                    f['c%i_samples'%channel][i] =numpy.append(wave_array,numpy.zeros((current_dim[channel]-num_samples,),dtype=wave_array.dtype))
                    f['c%i_num_samples'%channel][i] = num_samples
                    f['c%i_vert_offset'%channel][i] = wave_desc['vertical_offset']
                    f['c%i_vert_scale'%channel][i] = wave_desc['vertical_gain']
                    f['c%i_horiz_offset'%channel][i] = -wave_desc['horiz_offset']
                    f['c%i_horiz_scale'%channel][i] = wave_desc['horiz_interval']
                    
            except (socket.error, struct.error) as e:
                print '\n' + str(e)
                scope.clear()
                continue
            i += 1
    finally:
        print '\r'
        f.close()
        scope.clear()

        elapsed = time.time() - start

        if i > 0:
            print 'Completed %i events in %.3f seconds.' % (i, elapsed)
            print 'Averaged %.5f seconds per acquisition.' % (elapsed/i)
            print "Wrote to file '%s'." % filename

if __name__ == '__main__':
    import optparse

    usage = "usage: %prog <filename/prefix> [-n] [-r]"
    parser = optparse.OptionParser(usage, version="%prog 0.1.0")
    parser.add_option("-n", type="int", dest="nevents",
                      help="number of events to store per run", default=1000)
    parser.add_option("-r", type="int", dest="nruns",
                      help="number of runs", default=1)
    parser.add_option("--time", action="store_true", dest="time",
                      help="append time string to filename", default=False)
    (options, args) = parser.parse_args()

    if len(args) < 1:
        sys.exit(parser.format_help())
    
    if options.nevents < 1 or options.nruns < 1:
        sys.exit("Please specify a number >= 1 for number of events/runs")

    if options.nruns == 1 and not options.time:
        try:
            fetch(args[0], options.nevents)
        except KeyboardInterrupt:
            pass
    else:
        import time
        import string

        for i in range(options.nruns):
            timestr = string.replace(time.asctime(time.localtime()), ' ', '-')
            filename = args[0] + '_' + timestr + '.h5'
            print '-' * 65
            print 'Saving to file %s' % filename
            print '-' * 65

            try:
                fetch(filename, options.nevents)
            except KeyboardInterrupt:
                break
