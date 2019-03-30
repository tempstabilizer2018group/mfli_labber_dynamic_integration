#!/usr/bin/env python

import os
import sys

import InstrumentDriver

__version__  = '0.9'


import ZI_MFLI_lib

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class wraps the ziPython API"""
    def performOpen(self, options={}):
        self.x, self.y, self.r, self.theta = 0.0, 0.0, 0.0, 0.0


        self.log("A: " + self.comCfg.address, level=30)

        self.ziDevice = ZI_MFLI_lib.Zi_Device(self.comCfg.address)

        self.ziDevice.init_mfli_lock_in()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.ziDevice.disconnect()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        return 0.0

    def performGetValue(self, quant, options={}):
        if quant.name in ['X',]:
            self.x, self.y, self.r, self.theta = self.ziDevice.get_lockin()
            return self.x
        if quant.name in ['Y',]:
            return self.y
        if quant.name in ['R',]:
            return self.r
        if quant.name in ['theta',]:
            return self.theta
