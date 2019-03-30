#!/usr/bin/env python

import os
import sys

import InstrumentDriver

__version__  = '0.9'


import ZI_MFLI_lib

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class wraps the ziPython API"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        self.log("A: " + self.comCfg.address, level=30)

        self.ziDevice = ZI_MFLI_lib.Zi_Device(self.comCfg.address)

        self.ziDevice.init_mfli_aux_output()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.ziDevice.disconnect()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        if quant.name in ['Voltage',]:
            self.ziDevice.set_voltage(value)
            return self.ziDevice.get_voltage()

    def performGetValue(self, quant, options={}):
        if quant.name in ['Voltage',]:
            return self.ziDevice.get_voltage()
