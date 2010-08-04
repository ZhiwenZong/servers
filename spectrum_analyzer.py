# Copyright (C) 2007  Matthew Neeley
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# UPDATED
# 4 Aug, 2010 - Nathan Earnest - 2.1

"""
### BEGIN NODE INFO
[info]
name = Spectrum Analyzer Server
version = 2.1
description = 

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad import types as T, errors
from labrad.server import setting
from labrad.gpib import GPIBManagedServer
from struct import unpack
from twisted.internet.defer import inlineCallbacks, returnValue

__QUERY__ = """\
:FORM INT,32
:FORM:BORD NORM
:TRAC? TRACE%s"""

class SpectrumAnalyzer(GPIBManagedServer):
    name = 'Spectrum Analyzer Server'
    deviceName = 'Hewlett-Packard E4407B'

    @setting(10, 'Get Trace',
                 data=['{Query TRACE1}',
                          'w {Specify trace to query: 1, 2, or 3}'],
                 returns=['v[MHz] {start} v[MHz] {step} *v {y-values}'])
    def get_trace(self, c, data=1):
        """Returns the y-values of the current trace from the spectrum analyzer"""
        dev = self.selectedDevice(c)
        if data < 1 or data > 3:
            raise Exception('data out of range')
        trace = data
        start = float((yield dev.query(':FREQ:STAR?')))
        span = float((yield dev.query(':FREQ:SPAN?')))
        resp = yield dev.query(__QUERY__ % trace)
        vals = _parseBinaryData(resp)
        n = len(vals)
        returnValue((start/1.0e6, span/1.0e6/(n-1), vals))


    @setting(20, 'Peak Frequency',
                 data=['{Get Reading}'],
                 returns=['v[GHz] {Peak Frequency}'])
    def peak_frequency(self, c, data):
        """Gets the current frequency from the peak detector"""
        dev = self.selectedDevice(c)
        pos = float((yield dev.query(':CALC:MARK:X?')))
        returnValue(T.Value(pos/1e9, 'GHz'))

        
    @setting(21, 'Peak Amplitude',
                 data=['{Get Reading}'],
                 returns=['v[dBm] {Peak Amplitude}'])
    def peak_amplitude(self, c, data):
        """Gets the current amplitude from the peak detector"""
        dev = self.selectedDevice(c)
        height = float((yield dev.query(':CALC:MARK:Y?')))
        returnValue(T.Value(height, 'dBm'))

        
    @setting(22, 'Average Amplitude',
                 trace=['{Get average of Trace 1}',
                          'w {Get average of this trace}'],
                 returns=['v[dBm] {Average Amplitude}'])
    def average_amplitude(self, c, trace=1):
        """Gets the average amplitude of the entire trace"""
        dev = self.selectedDevice(c)
        height = float((yield dev.query(':TRAC:MATH:MEAN? TRACE%d\n' % trace)))
        returnValue(T.Value(height, 'dBm'))

        
    @setting(51, 'Number Of Points', n=['w'], returns=[''])
    def num_points(self, c, n):
        """Sets the current number of points in the sweep"""
        dev = self.selectedDevice(c)
        dev.write(':SWE:POIN %d' % n)


    @setting(102, 'Do IDN query', returns=['s'])
    def do_IDN_query(self, c):
        """Gets the IDN string from the device"""
        dev = self.selectedDevice(c)
        idn = yield dev.query('*IDN?')
        returnValue(idn)

    @setting(500, 'Set center Frequency', f='v[MHz]', returns='')
    def set_centerfreq(self, c, f):
        """Sets the center frequency"""
        dev = self.selectedDevice(c)
        dev.write(':FREQ:CENT %gMHz\n' % float(f))

    @setting(522, 'Set Span', f='v[MHz]', returns='')
    def set_span(self, c, f):
        """Sets the Frequency Span"""
        dev = self.selectedDevice(c)
        dev.write(':FREQ:SPAN %gMHz' % float(f))
        
    @setting(523, 'Set Resolution Bandwidth MHz', f = 'v[MHz]', returns='')
    def set_resolutionbandwidth(self,c,f):
        """Set the Resolution Bandwidth units in MHz"""
        dev = self.selectedDevice(c)
        dev.write(':BAND %gMHz' % float(f))

    @setting(524, 'Set Video Bandwidth kHz', f = 'v[kHz]', returns='')
    def set_videobandwidth(self,c,f):
        """Set the video Bandwidth units in kHz"""
        dev = self.selectedDevice(c)
        dev.write(':BAND:VID %gkHz' % float(f))

    @setting(600, 'Y Scale',setting='s', returns='')
    def set_yscale(self,c,setting):
        """This sets the Y scale to either LINear or LOGarithmic"""
        allowed = ['LIN','LOG']
        if setting not in allowed:
            raise Exception('allowed settings are: %s' % allowed)
        dev = self.selectedDevice(c)
        dev.write('DISP:WIND:TRAC:Y:SPAC %s' % setting)

    @setting(602, 'Reference Level dBm',f='v[dBm]', returns=[''])
    def set_referencelevel(self,c,f):
        """This sets the Reference Level in dBm"""
        dev = self.selectedDevice(c)
        dev.write('DISP:WIND:TRAC:Y:RLEV %gdBm' % float(f))

    @setting(603, 'Sweep time msec', f='v[ms]', returns='')
    def set_sweeprate(self, c, f):
        """This sets the sweep rate of the spectrum analyzer in mSeconds"""
        dev = self.selectedDevice(c)
        dev.write(':SWE:TIME %gms' % float(f))

    @setting(604, 'Detector type', setting='s', returns='')
    def set_detector(self, c, setting='POS'):
        """This sets the detector type to either Peak,Negative Peak or Sample"""
        allowed = ['SAMP', 'POS','NEG']
        if setting not in allowed:
            raise Exception('allowed settings are: %s' % allowed)
        dev = self.selectedDevice(c)
        dev.write(':DET %s' % setting)

    @setting(700, 'Trigger Source', setting='s', returns='')
    def set_trigsource(self, c, setting='IMM'):
        """This sets the triger source to Free Run, Video, Power Line, or External"""
        allowed = ['IMM', 'VID', 'LINE', 'EXT']
        if setting not in allowed:
            raise Exception('allowed settings are: %s' % allowed)
        dev = self.selectedDevice(c)
        dev.write(':TRIG:SOUR %s' % setting)


    @setting(701, 'Average ON/OFF', setting='s', returns='')
    def switch_average(self, c, setting='OFF'):
        """This turns the averaging on or off"""
        allowed = ['OFF', 'ON', 0, 1]
        if setting not in allowed:
            raise Exception('allowed settings are: %s' % allowed)
        dev = self.selectedDevice(c)
        dev.write(':AVER %s' % setting)

    @setting(702, 'Start Frequency MHz', f='v[MHz]',returns='')
    def start_frequency(self, c, f):
        """This will set the starting frequency"""
        dev = self.selectedDevice(c)
        dev.write(':FREQ:STAR %gMHz' % float(f) )


    @setting(703, 'Stop Frequency MHz', f='v[MHz]',returns='')
    def stop_frequency(self, c, f):
        """This will set the stopping frequency"""
        dev = self.selectedDevice(c)
        dev.write(':FREQ:STOP %gMHz' % float(f) )



##  Attempt to set average type.  SA does not accept value.
##  Gives error: "illegal paramter value"
##    @setting(702, 'Average Type', setting='s', returns='')
##    def average_type(self, c, setting='VID'):
##        """This switching the averaging type from either Video or to RMS Power"""
##        allowed = ['VID', 'POW']
##        if setting not in allowed:
##            raise Exception('allowed settings are: %s' % allowed)
##        dev = self.selectedDevice(c)
##        dev.write(':AVER:TYPE %s' % setting)


## dev.write('DISPlay:WINDow:TRACe:Y:SPACing  LINear|LOGarithmic)        
##    @setting(501, 'Resolution Bandwidth',
##                  accepts=['v[kHz]'],
##                  returns=['v[kHz]'])
##    @inlineCallbacks
##    def set_resolution_band(self, c, data):
##        """Sets the resolution bandwidth"""
##        dev = self.selectedDevice(c)
##        yield dev.write(':FREQ:CENT %gMHz\n' %data.value )
##        returnValue(data)


    
def _parseBinaryData(data):
    """Parse binary trace data."""
    h = int(data[1])
    d = int(data[2:2+h])
    s = data[2+h:]
    if len(s) != d:
        raise errors.HandlerError('Could not decode binary response.')
    n = d/4 # 4 bytes per data point

    data = unpack('>'+'l'*n, s)
    data = [d/1000.0 for d in data]

    return data

__server__ = SpectrumAnalyzer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
