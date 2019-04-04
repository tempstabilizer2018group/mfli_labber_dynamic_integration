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
        self.obj_criterion = None

        self.log("%s: before init" % __file__, level=30)

        self.ziDevice = ZI_MFLI_lib.Zi_Device(self.comCfg.address)

        self.ziDevice.init_mfli_lock_in()

        self.log("%s: after init" % __file__, level=30)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.ziDevice.stop_logging()
        self.log("%s: performClose: before disconnect" % __file__, level=30)
        self.ziDevice.disconnect()
        self.log("%s: performClose: after disconnect" % __file__, level=30)

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        if quant.name in ['criterion',]:
            self.ziDevice.set_criterion(value)
            return self.ziDevice.get_criterion()

        if quant.name in ['measure_loopback',]:
            self.ziDevice.measure_loopback = value
            return self.ziDevice.measure_loopback

        if quant.name in ['logging_save_file',]:
            self.ziDevice.stop_logging()
            self.ziDevice.stop_logging()

    def _performGetValue(self, quant, options):
        assert self.obj_criterion is not None

        if quant.name in ['quality',]:
            return self.obj_criterion.quality
        if quant.name in ['X',]:
            return self.obj_criterion.x_V
        if quant.name in ['Y',]:
            return self.obj_criterion.y_V
        if quant.name in ['R',]:
            return self.obj_criterion.r_V
        if quant.name in ['theta',]:
            return self.obj_criterion.theta_rad

        assert False, 'quant.name={} unknown!'.format(quant.name)
    
    def performGetValue(self, quant, options={}):
        '''
            In Measurement Setup:
              Log Channels
                 run
                 X
                 Y
                15:24:35,044:  %s: performGetValue: quant.name run quant.isFirstCall True quant.isFinalCall False
                15:24:35,194:  %s: performGetValue: quant.name X quant.isFirstCall False quant.isFinalCall False
                15:24:35,202:  %s: performGetValue: quant.name Y quant.isFirstCall False quant.isFinalCall True
                15:24:35,278:  %s: performGetValue: quant.name run quant.isFirstCall True quant.isFinalCall False
                15:24:35,443:  %s: performGetValue: quant.name X quant.isFirstCall False quant.isFinalCall False
                15:24:35,450:  %s: performGetValue: quant.name Y quant.isFirstCall False quant.isFinalCall True

            Checked: Log in parallel
                15:26:37,079:  %s: performGetValue: quant.name run quant.isFirstCall True quant.isFinalCall False
                15:26:37,258:  %s: performGetValue: quant.name X quant.isFirstCall False quant.isFinalCall False
                15:26:37,259:  %s: performGetValue: quant.name Y quant.isFirstCall False quant.isFinalCall True
                15:26:37,310:  %s: performGetValue: quant.name run quant.isFirstCall True quant.isFinalCall False
                15:26:37,499:  %s: performGetValue: quant.name X quant.isFirstCall False quant.isFinalCall False
                15:26:37,501:  %s: performGetValue: quant.name Y quant.isFirstCall False quant.isFinalCall True
        '''
        # self.log("%s: performGetValue: quant.name {} quant.isFirstCall {} quant.isFinalCall {}".format(quant.name, self.isFirstCall(options), self.isFinalCall(options)), level=30)

        if quant.name in ['criterion',]:
            return self.ziDevice.get_criterion()

        if quant.name in ['measure_loopback',]:
            return self.ziDevice.measure_loopback

        if self.isFirstCall(options):
            assert self.obj_criterion is None
            self.obj_criterion = self.ziDevice.get_lockin()

        value = self._performGetValue(quant, options)

        if self.isFinalCall(options):
            self.obj_criterion = None

        return value
