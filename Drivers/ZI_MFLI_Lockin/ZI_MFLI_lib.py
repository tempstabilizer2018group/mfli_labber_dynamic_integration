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


libs_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python_libs', sys.platform))
# list_directory: .../Drivers/python_libs/linux2
assert os.path.exists(libs_directory), 'Directory does not exist: {}'.format(libs_directory)
sys.path.append(libs_directory)

import time
import logging
import pprint
pp = pprint.PrettyPrinter(indent=4)
logger = logging.getLogger(os.path.basename(sys.argv[0]))
# logger = logging.getLogger(__name__)

# create console handler and set level to debug
ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)

# create formatter
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.INFO)

import zhinst
import zhinst.ziPython
# import zhinst.ziPython
# import zhinst.ziPython as zi
# import zhinst
# import zhinst.utils
import criterion

def statistics_time_add(*args):
    pass

try:
    import InstrumentDriver
    CommunicationError = InstrumentDriver.CommunicationError
except ImportError:
    CommunicationError = Exception

class Zi_Device:
    """ This class wraps the ziPython API"""

    def __init__(self, dev):
        """Perform the operation of opening the instrument connection"""
        assert dev != ''
        self.voltage = 0.0
        self.dev = dev
        self.set_criterion(criterion.CriterionSimple.__name__)
        try:
            # self.log("Descover Zurich Instruments device \"" + self.dev + "\"..")
            discovery = zhinst.ziPython.ziDiscovery()
            self.device_id = discovery.find(self.dev)
            device_props = discovery.get(self.device_id)
            self.daq = zhinst.ziPython.ziDAQServer(device_props['serveraddress'], device_props['serverport'], device_props['apilevel'])
        except Exception as e:
            raise CommunicationError("Device " + self.dev + " not found: " + str(e))
        
        try:
            _devtype = self.getByte('/features/devtype')
        except Exception as e:
            raise CommunicationError("Device " + self.dev + " not found: " + str(e))

    def disconnect(self):
        self.daq.disconnect()

    def set_criterion(self, criterion_name):
        if criterion_name == '':
            criterion_name = criterion.CriterionSimple.__name__
        self.criterion_name = criterion_name
        self.criterion_class = getattr(criterion, self.criterion_name, None)
        if self.criterion_class is None:
            raise Exception('Unknown class for criterion "{}"! "{}" is a valid class name'.format(self.criterion_name, criterion.CriterionSimple.__name__))

    def get_criterion(self):
        return self.criterion_name

    def __get(self, f, path):
        try:
            fullpath = '/%s%s' % (self.dev, path)
            return f(fullpath)
        except Exception as e:
            raise CommunicationError("Failed to " + f.__name__ + ": " + str(e))

    def getByte(self, path):
        return self.__get(self.daq.getByte, path)

    def __set(self, f, fullpath, v):
        try:
            f(fullpath, v)
        except Exception as e:
            raise CommunicationError("Failed to " + f.__name__ + "(" + fullpath + "): " + str(e))

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
        raise CommunicationError("Failed to setValue" + fullpath + "): Unknown type " + type(str).__name__)


    #
    # AUX OUTPUT
    #

    def init_mfli_aux_output(self):
        for channel in (0, 1, 2):
            self.setValue('/auxouts/{}/outputselect'.format(channel), -1)
            self.setValue('/auxouts/{}/offset'.format(channel), 0.0)
            self.setValue('/auxouts/{}/limitlower'.format(channel), -10.0)
            self.setValue('/auxouts/{}/limitupper'.format(channel), 10.0)

    def get_voltage(self):
        return self.voltage

    def set_voltage(self, v):
        self.voltage = v
        outputs = {
            0: (10, 10, 10),
            1: (10, 10,  0),
            2: (10,  0,  0),
            3: ( 0, 10, 10),
            4: ( 0,  0, 10),
        }
        voltage_abs_int = int(abs(self.voltage)+0.5)
        for channel, output in enumerate(outputs.get(voltage_abs_int, (0, 0, 0))):
            self.setValue('/auxouts/{}/offset'.format(channel), float(output))


    #
    # LOCK-IN
    #

    def init_mfli_lock_in(self):
        # Reset
        self._loopback_flag = False
        self._loopback_value_false_V = 0.0
        self._loopback_value_true_V = 10.0
        self._loopback_value_avg_V = (self._loopback_value_true_V-self._loopback_value_false_V)/2.0

        self.daq.unsubscribe('/{}/*'.format(self.dev))
        self.setValue('/demods/*/enable', 0)
        self.setValue('/oscs/*/freq', 1000.0)
        self.setValue('/sigouts/*/on', 0)
        self.setValue('/sigouts/*/amplitudes/*', 0.0)
        self.setValue('/sigins/*/on', 0)

        # Set
        self.setValue('/sigins/0/scaling', 1.0)
        self.setValue('/sigins/0/diff', 0)
        self.setValue('/sigins/0/float', 0)
        self.setValue('/sigins/0/imp50', 0)
        self.setValue('/sigins/0/ac', 0)
        self.setValue('/sigins/0/on', 1)
        self.setValue('/sigins/0/range', 0.001)

        self.setValue('/sigouts/0/amplitudes/0', 1.414031982421875)
        self.setValue('/sigouts/0/on', 1)
        self.setValue('/sigouts/0/autorange', 0)
        self.setValue('/sigouts/0/imp50', 0)
        self.setValue('/sigouts/0/offset', 0)
        self.setValue('/sigouts/0/diff', 0)
        self.setValue('/sigouts/0/add', 0)
        self.setValue('/sigouts/0/range', 10.0)

        self.setValue('/oscs/0/freq', 33.0)

        self.setValue('/demods/0/adcselect', 0)
        self.setValue('/demods/0/bypass', 0)
        self.setValue('/demods/0/oscselect', 0)
        self.setValue('/demods/0/sinc', 1)
        self.setValue('/demods/0/order', 3)
        self.setValue('/demods/0/trigger', 0)
        self.setValue('/demods/0/phaseshift', 0.0)
        self.setValue('/demods/0/harmonic', 1.0)
        self.setValue('/demods/0/rate', 104.6)
        self.setValue('/demods/0/timeconstant', 0.081133224070072174)

        self.setValue('/demods/0/enable', 1)

        self.setValue('/auxouts/3/outputselect', -1)
        self.setValue('/auxouts/3/offset', 0.0)
        self.setValue('/auxouts/3/limitlower', -10.0)
        self.setValue('/auxouts/3/limitupper', 10.0)

        # Start
        self.toggle_loopback_output()
        time.sleep(1.0)
        self._subscribe_path_lockin = '/{}/demods/0/sample'.format(self.dev)
        self._subscribe_path_auxin0_0 = '/{}/auxins/0/values/0'.format(self.dev)
        subscribe_list = [self._subscribe_path_lockin, self._subscribe_path_auxin0_0]
        # subscribe_list = [self._subscribe_path_auxin0_0]
        self.daq.subscribe(subscribe_list)

    def poll(self, duration_s=0.5):
        timeout_ms = 5 
        flags = 0
        return_flat_dict = True
        data = self.daq.poll(duration_s, timeout_ms, flags, return_flat_dict)
        if not data:
            # No data anymore
            return None
        if False:
            print('**** DATA')
            pp.pprint(data)
        return data

        '''
        {   '/dev3116/auxins/0/values/1': {   'timestamp': array([1351595804502], dtype=uint64),
                                            'value': array([5.84246397])},
            '/dev3116/demods/0/sample': {   'auxin0': array([9.98732167, 9.98996556, 9.98732167, 9.98831313, 9.98930459,
            9.98996556, 9.98864361, 9.98831313]),
                                            'auxin1': array([5.84811979, 5.02769293, 5.84080049, 5.84346206, 5.84446014,
            5.84512553, 5.84545823, 5.84712171]),
                                            'dio': array([0, 0, 0, 0, 0, 0, 0, 0], dtype=uint32),
                                            'frequency': array([32.99999996, 32.99999996, 32.99999996, 32.99999996, 32.99999996,
            32.99999996, 32.99999996, 32.99999996]),
                                            'phase': array([3.39930143, 5.38101286, 1.07944311, 3.06115454, 5.04277009,
            0.74129622, 2.72291177, 4.7046232 ]),
                                            'time': {   'blockloss': False,
                                                        'dataloss': False,
                                                        'invalidtimestamp': False,
                                                        'mindelta': 0,
                                                        'ratechange': False,
                                                        'trigger': 0},
                                            'timestamp': array([1351593544855, 1351594118295, 1351594691735, 1351595265175,
            1351595838615, 1351596412055, 1351596985495, 1351597558935],
            dtype=uint64),
                                            'trigger': array([ 10, 512, 256, 778, 512, 256, 778,   0], dtype=uint32),
                                            'x': array([-2.60897676e-05, -2.60897676e-05, -2.60897676e-05, -2.60897676e-05,
            -2.99412824e-05, -2.99412824e-05, -2.99412824e-05, -3.12901257e-05]),
                                            'y': array([-2.32184302e-06, -2.32184302e-06, -2.32184302e-06, -2.32184302e-06,
                4.05271902e-06,  4.05271902e-06,  4.05271902e-06,  9.37900449e-06])}}
        '''

        sample_list = data.get(subscribe_path, None)
        if sample_list:
            return sample_list
        if False:
            logger.debug('**** SAMPLE')
            pp.pprint(sample_list)

        '''
        {   'dev3116': {   'demods': {   '0': {   'sample': {   'auxin0': array([9.98996556, 9.98996556, 9.98996556, 9.99029605]),
                                                                'auxin1': array([4.52432478, 4.5233267 , 9.99716416, 9.99550068]),
                                                                'dio': array([0, 0, 0, 0], dtype=uint32),
                                                                'frequency': array([32.99999996, 32.99999996, 32.99999996, 32.99999996]),
                                                                'phase': array([4.14970565, 6.13132121, 1.82984733, 3.81146289]),
                                                                'time': {   'blockloss': False,
                                                                            'dataloss': False,
                                                                            'invalidtimestamp': False,
                                                                            'mindelta': 0,
                                                                            'ratechange': False,
                                                                            'trigger': 0},
                                                                'timestamp': array([523183197335, 523183770775, 523184344215, 523184917655], dtype=uint64),
                                                                'trigger': array([  0, 522, 256, 512], dtype=uint32),
                                                                'x': array([0.00081382, 0.00081382, 0.00081382, 0.00079068]),
                                                                'y': array([7.68430508e-06, 7.68430508e-06, 7.68430508e-06, 6.27083050e-06])}}}}}
        '''

        '''
        {   '/dev3116/demods/0/sample': {   'auxin0': array([9.98864361, 9.99095702, 9.99029605, 9.98963508]),
                                            'auxin1': array([4.55260389, 4.55160581, 9.99317182, 9.99350451]),
                                            'dio': array([0, 0, 0, 0], dtype=uint32),
                                            'frequency': array([32.99999996, 32.99999996, 32.99999996, 32.99999996]),
                                            'phase': array([4.01174326, 5.99335881, 1.69188494, 3.67350049]),
                                            'time': {   'blockloss': False,
                                                        'dataloss': False,
                                                        'invalidtimestamp': False,
                                                        'mindelta': 0,
                                                        'ratechange': False,
                                                        'trigger': 0},
                                            'timestamp': array([529840262295, 529840835735, 529841409175, 529841982615], dtype=uint64),
                                            'trigger': array([  0, 512, 266, 512], dtype=uint32),
                                            'x': array([0.00081626, 0.00081626, 0.00081626, 0.00079526]),
                                            'y': array([ 6.30869067e-07,  6.30869067e-07,  6.30869067e-07, -8.03117684e-07])}}
        '''

        '''
        {   'auxin0': array([9.99360092, 9.99690579, 9.99624482, 9.99360092, 9.99260946,
            9.99393141]),
            'auxin1': array([3.49363443, 3.4663534 , 9.99782955, 3.47101114, 3.44971863,
            3.43907238]),
            'dio': array([0, 0, 0, 0, 0, 0], dtype=uint32),
            'frequency': array([32.99999996, 32.99999996, 32.99999996, 32.99999996, 32.99999996,
            32.99999996]),
            'phase': array([5.5868539 , 1.28528415, 3.26699558, 5.24861114, 0.94713726,
            2.92875282]),
            'time': {   'blockloss': False,
                        'dataloss': False,
                        'invalidtimestamp': False,
                        'mindelta': 0,
                        'ratechange': False,
                        'trigger': 0},
            'timestamp': array([459849616535, 459850189975, 459850763415, 459851336855,
            459851910295, 459852483735], dtype=uint64),
            'trigger': array([  0, 266, 512,   0, 778, 256], dtype=uint32),
            'x': array([-2.77537180e-05, -2.77537180e-05, -3.38719419e-05, -3.38719419e-05,
            -3.38719419e-05, -3.38719419e-05]),
            'y': array([-4.51401086e-06, -4.51401086e-06, -8.98523653e-06, -8.98523653e-06,
            -8.98523653e-06, -8.98523653e-06])}
        '''
        list_timestamp = sample_list['timestamp']
        list_x = sample_list['x']
        list_y = sample_list['x']


        return sample_list

    def toggle_loopback_output(self):
        self._loopback_flag = not self._loopback_flag
        self._loopback_value = self._loopback_value_true_V if self._loopback_flag else self._loopback_value_false_V
        self.setValue('/auxouts/3/offset', float(self._loopback_value))

    def iter_poll_loopback(self):
        while True:
            data1 = self.poll(duration_s=0.1)
            if not data1:
                # No data anymore
                logger.debug('iter_poll_loopback: no data')
                continue
            data2 = data1.get(self._subscribe_path_auxin0_0, None)
            if not data2:
                # lock-in data: Trash
                logger.debug('iter_poll_loopback: trash lock-in')
                continue
            list_timestamp = data2['timestamp']
            list_value = data2['value']
            logger.debug('iter_poll_loopback: list_value: ' + str(list_value))
            assert len(list_timestamp) == len(list_value)
            value = list_value[-1]
            logger.debug('iter_poll_loopback: value: ' + str(value))
            yield value

    def iter_poll_lockin(self):
        timestamp_last = 0
        while True:
            data1 = self.poll(duration_s=0.01)
            if not data1:
                # No data anymore
                logger.debug('iter_poll_lockin: no data')
                continue
            data2 = data1.get(self._subscribe_path_lockin, None)
            if not data2:
                # lock-in data: Trash
                logger.debug('iter_poll_lockin: trash loopback')
                continue

            list_timestamp = data2['timestamp']
            list_x = data2['x']
            list_y = data2['x']
            assert len(list_timestamp) == len(list_x)
            assert len(list_timestamp) == len(list_y)
            logger.debug('iter_poll_lockin: list_timeout: ' + str(list_timestamp))
            for timestamp, x, y in zip(list_timestamp, list_x, list_y):
                if timestamp_last != timestamp:
                    timestamp_last = timestamp
                    logger.debug('iter_poll_lockin: timestamp, x, y: {} {} {}'.format(timestamp, x, y))
                    yield timestamp, x, y


    def get_lockin(self):
        '''
          TODO: Wait for the correct 'frame'
          TODO: Measure the time:
            Between get_lockin()
            a) Clear buffer
            b) Between start get_lockin() und Loopback
            c) Between Loopback and the first lock-in
            d) Between last lock-in and poll
        '''
        # Trash all incoming data
        timeA = time.time()

        while True:
            sample = self.poll(duration_s=0.001)
            if sample is None:
                break

        timeB = time.time()
        statistics_time_add(timeB-timeA, 'a) Clear buffer')

        # Set for Loopback-Reply
        self.toggle_loopback_output()

        # Wait for Loopback-Reply
        for loopback_measured_V in self.iter_poll_loopback():
            loopback_measured_flag = loopback_measured_V > self._loopback_value_avg_V
            if loopback_measured_flag == self._loopback_flag:
                # We got the reply from the loopback-loop
                break
            logger.debug('waiting for loopback-reply')

        timeC = time.time()
        statistics_time_add(timeC-timeB, 'b) Between start get_lockin() und Loopback')

        timeD = time.time()
        statistics_time_add(timeD-timeC, 'c) Between Loopback and the first lock-in')

        obj_criterion = self.criterion_class()

        # Wait for First Lock-In sample
        # Wait for criterion to be satisfied
        for timestamp, x, y in self.iter_poll_lockin():
            obj_criterion.append_values(timestamp, x, y)
            if obj_criterion.satisfied():
                return obj_criterion


if __name__ == '__main__':
    dev_name = 'dev3116'
    dev_name = 'dev4078'

    if False:
        dev = Zi_Device(dev_name)
        dev.init_mfli_aux_output()
        dev.set_voltage(4)
        dev.set_voltage(0)
        dev.disconnect()
        logger.debug('done')

    if True:
        dev = Zi_Device(dev_name)
        dev.init_mfli_lock_in()
        while True:
            # x, y, r, theta = dev.get_lockin()
            obj_criterion = dev.get_lockin()
            logger.info('get_lockin() returned {c.x_V} {c.y_V} {c.r_V} {c.theta_rad}'.format(c=obj_criterion))
            break
        dev.disconnect()
