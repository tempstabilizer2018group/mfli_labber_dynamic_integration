#!/usr/bin/env python

import os
import sys

# sys.path.insert(0, r'C:\Program Files (x86)\Labber\python-labber\multiproc-include\py37')
#Some stuff to import ziPython from a relative path independent from system wide installations
# cmd_folder = os.path.abspath(os.path.dirname(__file__))
# if cmd_folder not in sys.path:
#     sys.path.insert(0, cmd_folder)

import InstrumentDriver


__version__  = '1.1'

#Some stuff to import ziPython from a relative path independent from system wide installations
# cmd_folder = os.path.abspath(os.path.dirname(__file__))
# if cmd_folder not in sys.path:
#     sys.path.insert(0, cmd_folder)


import ZI_MFLI_lib

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class wraps the ziPython API"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        self.log("AAA", level=30)
        self.log("A: " + self.comCfg.address)

        self.ziDevice = ZI_MFLI_lib.Zi_Device(self.comCfg.address)

        self.ziDevice.init_mfli_aux_output()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.ziDevice.disconnect()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.name in ['Voltage',]:
            value = quant.getValue()
            self.ziDevice.set_voltage(value)

