#!/usr/bin/env python

import os
import sys

# C:\Program Files (x86)\Labber\python-labber\Lib\site-packages

# p = os.environ["USERPROFILE"]
# sys.path.insert(0, p)
# import Labber

#Some stuff to import ziPython from a relative path independent from system wide installations
# cmd_folder = os.path.abspath(os.path.dirname(__file__))
# if cmd_folder not in sys.path:
#     sys.path.insert(0, cmd_folder)


cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(cmd_folder)

import zhinst
import zhinst.ziPython
# import zhinst.ziPython
# import zhinst.ziPython as zi
# import zhinst
# import zhinst.utils


try:
    import InstrumentDriver
except ImportError:
    pass

class Zi_Device:
    """ This class wraps the ziPython API"""

    def __init__(self, dev):
        """Perform the operation of opening the instrument connection"""
        assert dev != ''
        self.dev = dev
        try:
            # self.log("Descover Zurich Instruments device \"" + self.dev + "\"..")
            discovery = zhinst.ziPython.ziDiscovery()
            self.device_id = discovery.find(self.dev)
            device_props = discovery.get(self.device_id)
            self.daq = zhinst.ziPython.ziDAQServer(device_props['serveraddress'], device_props['serverport'], device_props['apilevel'])
        except Exception as e:
            raise InstrumentDriver.CommunicationError("Device " + self.dev + " not found: " + str(e))
        
        try:
            _devtype = self.getByte('/features/devtype')
        except Exception as e:
            raise InstrumentDriver.CommunicationError("Device " + self.dev + " not found: " + str(e))

    def disconnect(self):
        self.daq.disconnect()

    def __get(self, f, path):
        try:
            fullpath = '/%s%s' % (self.dev, path)
            return f(fullpath)
        except Exception as e:
            raise InstrumentDriver.CommunicationError("Failed to " + f.__name__ + ": " + str(e))

    def getByte(self, path):
        return self.__get(self.daq.getByte, path)

    def __set(self, f, fullpath, v):
        try:
            f(fullpath, v)
        except Exception as e:
            raise InstrumentDriver.CommunicationError("Failed to " + f.__name__ + "(" + fullpath + "): " + str(e))

    # def setInt(self, path, v):
    #     self.__set(self.daq.setInt, path, v)

    # def setDouble(self, path, v):
    #     self.__set(self.daq.setDouble, path, v)
    
    def setValue(self, path, v):
        fullpath = '/%s%s' % (self.dev, path)
        if isinstance(v, int):
            self.__set(self.daq.setInt, fullpath, v)
            return
        if isinstance(v, float):
            self.__set(self.daq.setDouble, fullpath, v)
            return
        if isinstance(v, str):
            self.__set(self.daq.setString, fullpath, v)
            return
        raise InstrumentDriver.CommunicationError("Failed to setValue" + fullpath + "): Unknown type " + type(str).__name__)


    def init_mfli_aux_output(self):
        for channel in (0, 1, 2):
            self.setValue('/auxouts/{}/outputselect'.format(channel), -1)
            self.setValue('/auxouts/{}/offset'.format(channel), 0.0)
            self.setValue('/auxouts/{}/limitlower'.format(channel), -10.0)
            self.setValue('/auxouts/{}/limitupper'.format(channel), 10.0)

    def set_voltage(self, v):
            v = int(v)
            outputs = {
                0: (10, 10, 10),
                1: (10, 10,  0),
                2: (10,  0,  0),
                3: ( 0, 10, 10),
                4: ( 0,  0, 10),
            }
            for channel, output in enumerate(outputs.get(v, (0, 0, 0))):
                self.setValue('/auxouts/{}/offset'.format(channel), float(output))



if __name__ == '__main__':
    dev = Zi_Device('dev4078')
    dev.init_mfli_aux_output()
    dev.set_voltage(4)
    dev.set_voltage(0)
    dev.disconnect()
