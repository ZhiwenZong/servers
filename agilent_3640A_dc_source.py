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

"""
### BEGIN NODE INFO
[info]
name = Agilent 3640A DC Source
version = 1.0
description = Controls the Agilent 3640A DC Power Supply.

[startup]
cmdline = %PYTHON% agilent_3640A_dc_source.py
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad import types as T, util
from labrad.server import setting
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
            
class AgilentDCSource(GPIBManagedServer):
    """Controls the Agilent 3640A DC Power Supply."""
    name = 'Agilent 3640A DC Source'
    deviceName = 'Agilent Technologies E3640A'
        
    @setting(10, state='b', returns='b')
    def output(self, c, state=None):
        """Get or set the output state."""
        dev = self.selectedDevice(c)
        if state is None:
            ans = yield dev.query('OUTP?')
            state = bool(ans)
        else:
            yield dev.write('OUTP %d' % state)
        returnValue(state)

    @setting(20, curr='v[A]', returns='v[A]')
    def current(self, c, curr=None):
        """Get or set the output current.

        Returns the measured output current, which
        may not be equal to the set level if the output
        is off or the device is voltage-limited, etc.
        """
        dev = self.selectedDevice(c)
        if curr is not None:
            yield dev.write('CURR %g' % float(curr))
        ans = yield dev.query('MEAS:CURR?')
        returnValue(float(ans))

    @setting(30, volt='v[V]', returns='v[V]')
    def voltage(self, c, volt=None):
        """Get or set the output voltage.

        Returns the measured output voltage, which
        may not be equal to the set level if the output
        is off or the device is current-limited, etc.
        """
        dev = self.selectedDevice(c)
        if volt is not None:
            yield dev.write('VOLT %g' % float(volt))
        ans = yield dev.query('MEAS:VOLT?')
        returnValue(float(ans))

__server__ = AgilentDCSource()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)