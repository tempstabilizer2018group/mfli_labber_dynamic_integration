#!/usr/bin/env python

import os
import sys

import InstrumentDriver

__version__  = '0.9'


import ZI_MFLI_lib
import criterion

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
        if quant.name in ['criterion',]:
            self.ziDevice.set_criterion(value)
            return self.ziDevice.get_criterion()
        if quant.name in ['run',]:
            self.obj_criterion = self.ziDevice.get_lockin()
            return self.obj_criterion.quality
        return 0.0

    def performGetValue(self, quant, options={}):
        if quant.name in ['criterion',]:
            return self.ziDevice.get_criterion()
        if quant.name in ['run',]:
            self.obj_criterion = self.ziDevice.get_lockin()
            return self.obj_criterion.quality
        if quant.name in ['X',]:
            assert self.obj_criterion is not None
            return self.obj_criterion.x_V
        if quant.name in ['Y',]:
            assert self.obj_criterion is not None
            return self.obj_criterion.y_V
        if quant.name in ['R',]:
            assert self.obj_criterion is not None
            return self.obj_criterion.r_V
        if quant.name in ['theta',]:
            assert self.obj_criterion is not None
            return self.obj_criterion.theta_rad
