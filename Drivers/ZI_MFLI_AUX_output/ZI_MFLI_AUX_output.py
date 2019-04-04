#!/usr/bin/env python

import os
import sys

import InstrumentDriver

__version__  = '0.9'

libs_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ZI_MFLI_Lockin'))
assert os.path.exists(libs_directory), 'Directory does not exist: {}'.format(libs_directory)
sys.path.append(libs_directory)

import ZI_MFLI_lib

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class wraps the ziPython API"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        self.log("%s: before init" % __file__, level=30)

        self.ziDevice = ZI_MFLI_lib.Zi_Device(self.comCfg.address)

        self.ziDevice.init_mfli_aux_output()

        self.log("%s: after init" % __file__, level=30)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.log("%s: performClose: before disconnect" % __file__, level=30)
        self.ziDevice.disconnect()
        self.log("%s: performClose: after disconnect" % __file__, level=30)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        if quant.name in ['outputform',]:
            self.ziDevice.output_form = value
            return self.ziDevice.output_form

        if quant.name in ['Voltage',]:
            self.ziDevice.set_voltage(value)
            return self.ziDevice.get_voltage()

    def performGetValue(self, quant, options={}):
        if quant.name in ['outputform',]:
            return self.ziDevice.output_form

        if quant.name in ['Voltage',]:
            return self.ziDevice.get_voltage()
