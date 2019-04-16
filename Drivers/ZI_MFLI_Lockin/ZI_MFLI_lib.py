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
import pickle
import logging
import importlib
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

# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

import zhinst
import zhinst.ziPython

import criterion

class Statistics:
    def __init__(self):
        self.time_start_s = None
        self.time_start_line_s = None
        self.line_num = 0
        self.first_line = True
        self.dict_values = {}
        self.dict_header = {}
        self.list_signal_name = []
        self.list_unit_name = []

        filename = __file__.replace('.py', '_log.csv')
        self.f = open(filename, 'w')

    def start_line(self, time_start_s):
        if self.time_start_s is None:
            self.time_start_s = time_start_s
        self.time_start_line_s = time_start_s
        self.add('line_begin', 's', self.time_start_line_s-self.time_start_s)

    def end_line(self):
        if self.first_line:
            # Dump Header
            self.first_line = False
            self.dump_line(self.list_signal_name)
            self.dump_line(self.list_unit_name)

        # Dump line
        l = []
        for signal_name in self.list_signal_name:
            l.append(self.dict_values.get(signal_name, '?'))
        self.dump_line(l)

        self.dict_values = {}

    def add(self, signal_name, unit_name, value):
        if self.first_line:
            self.list_signal_name.append(signal_name)
            self.list_unit_name.append('[{}]'.format(unit_name))

        if self.dict_values.get(signal_name, False) is not False:
            raise Exception('Signal {} used twice!'.format(signal_name))
        self.dict_values[signal_name] = str(value)
    
    def add_time(self, signal_name):
        time_s = time.time() - self.time_start_line_s
        self.add(signal_name, 'ms', int(time_s*1000.0))

    def add_counter(self, signal_name, counter):
        self.add(signal_name, '1', counter)

    def dump_line(self, list_line):
        self.f.write('\t'.join(list_line))
        self.f.write('\n')
        self.line_num += 1
        if self.line_num % 25 == 0:
            # 200ms * 25 = 5s
            self.f.flush()

    def flush(self):
        self.f.flush()

try:
    import InstrumentDriver
    CommunicationError = InstrumentDriver.CommunicationError
except ImportError:
    CommunicationError = Exception

OUTPUTFORM_PEAK = 'OUTPUTFORM_PEAK'
OUTPUTFORM_HORN = 'OUTPUTFORM_HORN'
OUTPUTFORM_STEP = 'OUTPUTFORM_STEP'
list_outputs = (OUTPUTFORM_HORN, OUTPUTFORM_PEAK, OUTPUTFORM_STEP)

class Zi_Device:
    """ This class wraps the ziPython API"""

    def __init__(self, dev):
        """Perform the operation of opening the instrument connection"""
        assert dev != ''
        self.trash_previous_samples = True
        self.measure_loopback = False
        self.skip_first_measurement = True
        self.start_using_last_measurement = True
        self.list_logging = None
        self.output_form = OUTPUTFORM_HORN
        self.time_last_import = time.time()
        self.statistics = Statistics()
        self.voltage = 0.0
        self._range = 0.1
        self.dev = dev
        self.set_criterion(criterion.CriterionSimple.__name__)
        try:
            # self.log("Descover Zurich Instruments device \"" + self.dev + "\"..")
            discovery = zhinst.ziPython.ziDiscovery()
            self.device_id = discovery.find(self.dev)
            device_props = discovery.get(self.device_id)
            logger.info('connecting to {} at {}:{}'.format(self.dev, device_props['serveraddress'], device_props['serverport']))
            self.daq = zhinst.ziPython.ziDAQServer(device_props['serveraddress'], device_props['serverport'], device_props['apilevel'])
        except Exception as e:
            raise CommunicationError("Device " + self.dev + " not found: " + str(e))
        
        try:
            _devtype = self.getByte('/features/devtype')
        except Exception as e:
            raise CommunicationError("Device " + self.dev + " not found: " + str(e))
        self.clockbase_s = self.getInt('/clockbase')
        self.clockbase_ms = self.clockbase_s//1000
        logger.debug('self.clockbase_s: %d' % self.clockbase_s)
        logger.debug('self.clockbase_ms: %d' % self.clockbase_ms)

    def disconnect(self):
        self.statistics.flush()
        self.daq.disconnect()

    def start_logging(self):
        self.list_logging = []

    def stop_logging(self):
        if self.list_logging is None:
            return

        filename_helper = '_{}_{}'.format(self.output_form, self.criterion_name)
        criterion.pickle_dump(self.list_logging, filename_helper)
        self.list_logging = None

    def is_logging(self):
        return self.list_logging is not None

    def get_time_diff_ms(self, timestamp_before, timestamp_after):
        assert timestamp_after >= timestamp_before
        diff = timestamp_after - timestamp_before
        return diff/self.clockbase_ms

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

    def getInt(self, path):
        return self.__get(self.daq.getInt, path)

    def getDouble(self, path):
        return self.__get(self.daq.getDouble, path)

    def __set(self, f, fullpath, v):
        try:
            f(fullpath, v)
        except Exception as e:
            raise CommunicationError("Failed to " + f.__name__ + "(" + fullpath + "): " + str(e))

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
        if self.output_form == OUTPUTFORM_HORN:
            outputs = {
                # channel
                #    1   2   3
                #  10M, 2M, 1M
                0: (10, 10, 10),
                1: ( 0, 10, 10),
                2: ( 0,  0, 10),
                3: (10, 10,  0),
                4: (10,  0,  0),
            }
            voltage_int = int(abs(self.voltage)+0.5)
            output_list = outputs.get(voltage_int, (0, 0, 0))
        if self.output_form == OUTPUTFORM_PEAK:
            outputs = {
                # channel
                #    1   2   3
                #  10M, 2M, 1M
                0: (10, 10, 10),
            }
            voltage_int = int(abs(self.voltage)+0.5)
            output_list = outputs.get(voltage_int, (0, 0, 0))
        if self.output_form == OUTPUTFORM_STEP:
            output_list = (0, 0, 0)
            if self.voltage >= 0.0:
                output_list = (10, 10, 10)
        if output_list is None:
            raise Exception('ouput is "{}" but must be one of {}'.format(self.output_form, ','.join(list_outputs)))
        for channel, output in enumerate(output_list):
            self.setValue('/auxouts/{}/offset'.format(channel), float(output))


    #
    # LOCK-IN
    #

    def init_mfli_lock_in(self):
        # my_directory = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        # filename = os.path.join(my_directory, 'log_mfli.txt')
        filename = __file__.replace('.py', '_log.txt')
        fh = logging.FileHandler(filename)
        # fh.setLevel(logging.DEBUG)
        fh.setLevel(logging.INFO)
        logger.addHandler(fh)

        # Reset
        self._skip_count = 0
        self._range = 0.1
        self._last_criterion = None
        self._loopback_flag = False
        self._loopback_value_false_V = 0.0
        self._loopback_value_true_V = 10.0
        self._loopback_value_avg_V = (self._loopback_value_true_V-self._loopback_value_false_V)/2.0

        self.daq.unsubscribe('/{}/*'.format(self.dev))

        self.setValue('/demods/*/enable', 0)
        self.setValue('/demods/*/adcselect', 0)
        self.setValue('/demods/*/bypass', 0)
        self.setValue('/demods/*/oscselect', 0)
        self.setValue('/demods/*/order', 0)
        self.setValue('/demods/*/sinc', 0)
        self.setValue('/demods/*/timeconstant', 1.0/10000.0)
        self.setValue('/demods/*/rate', 837.1)  # 104.6

        self.setValue('/oscs/*/freq', 1000.0)
        self.setValue('/sigouts/*/on', 0)
        self.setValue('/sigouts/*/amplitudes/*', 0.0)
        self.setValue('/sigins/*/on', 0)
        self.setValue('/sigouts/*/enables/0', 0)

        self.daq.sync()
        # Set
        self.setValue('/sigins/0/diff', 0)
        self.setValue('/sigins/0/float', 1)
        self.setValue('/sigins/0/imp50', 0)
        self.setValue('/sigins/0/ac', 0)
        self.setValue('/sigins/0/on', 1)
        self.setValue('/sigins/0/scaling', 1.0)
        self.setValue('/sigins/0/autorange', 1.0)
        self._update_range()

        self.setValue('/sigouts/0/amplitudes/0', 1.414031982421875)
        self.setValue('/sigouts/0/autorange', 0)
        self.setValue('/sigouts/0/imp50', 0)
        self.setValue('/sigouts/0/offset', 0)
        self.setValue('/sigouts/0/diff', 0)
        self.setValue('/sigouts/0/add', 0)
        self.setValue('/sigouts/0/range', 10.0)
        self.setValue('/sigouts/0/on', 1)
        self.setValue('/sigouts/0/enables/0', 1)

        self.setValue('/oscs/0/freq', 33.0)

        self.setValue('/demods/0/adcselect', 0)
        self.setValue('/demods/0/bypass', 0)
        self.setValue('/demods/0/oscselect', 0)
        self.setValue('/demods/0/sinc', 1)
        self.setValue('/demods/0/order', 3)
        self.setValue('/demods/0/trigger', 0)
        self.setValue('/demods/0/phaseshift', 0.0)
        self.setValue('/demods/0/harmonic', 1.0)
        self.setValue('/demods/0/rate', 104.6) # 837.1
        self.setValue('/demods/0/timeconstant', 8.11410938e-07)

        self.setValue('/demods/0/enable', 1)

        self.setValue('/auxouts/3/outputselect', -1)
        self.setValue('/auxouts/3/offset', 0.0)
        self.setValue('/auxouts/3/limitlower', -10.0)
        self.setValue('/auxouts/3/limitupper', 10.0)

        # Start
        self._toggle_loopback_output()
        self._subscribe_path = '/{}/demods/0/sample'.format(self.dev)
        self.daq.subscribe(self._subscribe_path)
        # Wait till toggle value sattles
        time.sleep(0.1)

        self.init_mfli_aux_output()

    def get_range(self):
        return self._range

    def set_range(self, range):
        self._range = range
        self._update_range()
        # We have to wait for the instrument to send back the value which was eventually used.
        time.sleep(2.0)
        self._range = self.getDouble('/sigins/0/range')

    def _update_range(self):
        self.setValue('/sigins/0/range', self._range)

    def _poll(self, duration_s=0.5):
        timeout_ms = 1
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
{   '/dev4078/demods/0/sample': {   'auxin0': array([-0.00229972, -0.00065706, -0.00032853, -0.00197119,  0.00032853,  0.00032853]),
                                    'auxin1': array([ 0.00032922, -0.00098766, -0.00098766,  0.00098766,  0.        ,  0.00032922]),
                                    'dio': array([0, 0, 0, 0, 0, 0], dtype=uint32),
                                    'frequency': array([32.99999996, 32.99999996, 32.99999996, 32.99999996, 32.99999996,  32.99999996]),
                                    'phase': array([4.95130649, 0.64973674, 2.63144817, 4.61306372, 0.31158985,  2.2932054 ]),
                                    'time': {   'blockloss': False,
                                                'dataloss': False,
                                                'invalidtimestamp': False,
                                                'mindelta': 0,
                                                'ratechange': False,
                                                'trigger': 0},
                                    'timestamp': array([1913412209688, 1913412783128, 1913413356568, 1913413930008, 1913414503448, 1913415076888], dtype=uint64),
                                    'trigger': array([  0, 768, 768,   0, 768, 768], dtype=uint32),
                                    'x': array([2.47236311e-09, 2.47236311e-09, 2.47236311e-09, 2.47236311e-09, 7.21072315e-09, 7.21072315e-09]),
                                    'y': array([3.87694619e-07, 3.87694619e-07, 3.87694619e-07, 3.87694619e-07, 3.83416479e-07, 3.83416479e-07])}}
        '''

    def _toggle_loopback_output(self):
        self._loopback_flag = not self._loopback_flag
        self._loopback_value = self._loopback_value_true_V if self._loopback_flag else self._loopback_value_false_V
        self.setValue('/auxouts/3/offset', float(self._loopback_value))

    def _iter_poll(self):
        while True:
            data1 = self._poll(duration_s=0.005)
            if not data1:
                # No data anymore
                logger.debug('_iter_poll: no data')
                continue
            data2 = data1[self._subscribe_path]

            list_timestamp = data2['timestamp']
            list_x = data2['x']
            list_y = data2['y']
            list_auxin0 = data2['auxin0']

            assert len(list_timestamp) == len(list_x)
            assert len(list_timestamp) == len(list_y)
            assert len(list_timestamp) == len(list_auxin0)

            for values in zip(list_timestamp, list_x, list_y, list_auxin0):
                yield values

    def _iter_poll_loopback(self, _iter_poll):
        for _timestamp, _x, _y, auxin0 in _iter_poll:
            yield auxin0

    def _iter_poll_lockin(self, _iter_poll):
        counter_same_x = 0
        x_last = None
        timestamp_start = None
        for timestamp, x, y, _auxin0 in _iter_poll:
            if x_last == None:
                # First time: special case: remember the x and now start for watching for changes of x
                x_last = x
                timestamp_start = timestamp
                continue
            if x_last != x:
                x_last = x
                if timestamp_start is not None:
                    logger.debug('_iter_poll_lockin: delta timestamp: {}ms'.format(self.get_time_diff_ms(timestamp_start, timestamp)))
                logger.debug('_iter_poll_lockin: counter_same_x: {}'.format(counter_same_x))
                logger.debug('_iter_poll_lockin: timestamp, x, y: {} {:1.9f} {:1.9f}'.format(timestamp, x, y))

                yield timestamp, x, y

                timestamp_start = timestamp
                counter_same_x = 0
                continue

            # TODO: Hack, constant
            timeout_ms = 2*30
            if self.get_time_diff_ms(timestamp_start, timestamp) > timeout_ms:
                # It may happen, that x is 0.0000, so 'x_last != x' will never be true.
                # We safe us from entering an endless loop
                logger.debug("_iter_poll_lockin: x didn't change within %d ms!" % timeout_ms)
                yield timestamp, x, y

                timestamp_start = timestamp
                counter_same_x = 0
                continue

            counter_same_x += 1

    def _trash_measurements(self):
        # Trash all incoming data
        self.statistics.add_time('Trash begin')
        trash_counter = 0
        while True:
            trash_counter += 1
            sample = self._poll(duration_s=0.0001)
            if sample is None:
                break
        self.statistics.add_counter('trash_counter', trash_counter)
        self.statistics.add_time('Trash end')

    def _read_and_trash_first_measurement(self, _iter_poll):
        self.statistics.add_time('Wait First begin')
        counter_samples = 0
        for _timestamp, _x, _y in self._iter_poll_lockin(_iter_poll):
            counter_samples += 1
            self._watchdog()
        self.statistics.add_counter('Wait First Samples', counter_samples)
        self.statistics.add_time('Wait First end')

    def _create_criterion(self):
        if self._time_start_lockin > self.time_last_import + 5.0:
            # Reload criterion-module after some time
            self.time_last_import = self._time_start_lockin
            importlib.reload(criterion)
            logger.debug('reloaded module "criterion"')
            self.criterion_class = getattr(criterion, self.criterion_name, None)

        obj_criterion = self.criterion_class(self._last_criterion)

        if self.list_logging is not None:
            self.list_logging.append(obj_criterion)

        return obj_criterion

    def _do_measure_loopback(self, _iter_poll):
        # Set for Loopback-Reply
        self._toggle_loopback_output()

        # Wait for Loopback-Reply
        self.statistics.add_time('Loopback begin')
        for loopback_measured_V in self._iter_poll_loopback(_iter_poll):
            loopback_measured_flag = loopback_measured_V > self._loopback_value_avg_V
            if loopback_measured_flag == self._loopback_flag:
                # We got the reply from the loopback-loop
                break
            self._watchdog()
            logger.debug('waiting for loopback-reply')
        logger.debug('got loopback-reply')
        self.statistics.add_time('Loopback end')

    def _measurement_unil_satisfied(self, _iter_poll, obj_criterion):
        # Read measurements until the criterion gets satisfied
        self.statistics.add_time('Wait Sample begin')
        counter_samples = 0
        for timestamp, x, y in self._iter_poll_lockin(_iter_poll):
            counter_samples += 1
            obj_criterion.append_values(timestamp, x, y)
            self._watchdog()
            if obj_criterion.satisfied():
                if obj_criterion.skip_count > 0:
                    self._skip_count = obj_criterion.skip_count
                self._last_criterion = obj_criterion
                self.statistics.add_counter('Wait Sample', counter_samples)
                self.statistics.add_time('Wait Sample end')
                self.statistics.end_line()
                return obj_criterion
        assert False

    def _watchdog(self):
        time_elapsed = time.time() - self._time_start_lockin
        if time_elapsed > 2.0:
            raise Exception('Watchdog')


    def get_lockin(self):
        '''
          TODO: Wait for the correct 'frame'
          TODO: Measure the time:
            Between get_lockin()
            a) Clear buffer
            b) Between start get_lockin() und Loopback
            c) Between Loopback and the first lock-in
            d) Between last lock-in and _poll
        '''
        if self._skip_count > 0:
            self._skip_count -= 1
            return criterion.criterion_skip

        self._time_start_lockin = time.time()
        self.statistics.start_line(self._time_start_lockin)

        # Trash all incoming data
        if self.trash_previous_samples:
            self._trash_measurements()

        _iter_poll = self._iter_poll()

        if self.measure_loopback:
            self._do_measure_loopback(_iter_poll)

        if not self.skip_first_measurement:
            # Wait for First Lock-In sample: Trash it
            self._read_and_trash_first_measurement(_iter_poll)

        obj_criterion = self._create_criterion()

        if self.start_using_last_measurement:
            self.statistics.add_time('Wait Last Sample begin')
            for timestamp, x, y, _auxin0 in _iter_poll:
                obj_criterion.append_values(timestamp, x, y)
                break
            self.statistics.add_time('Wait Last Sample end')

        # Read measurements until the criterion gets satisfied
        self._measurement_unil_satisfied(_iter_poll, obj_criterion)
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
        # dev.set_criterion('CriterionOne')
        dev.set_criterion('CriterionLogging')
        # dev.measure_loopback = False
        dev.start_logging()

        for i in range(10):
            # x, y, r, theta = dev.get_lockin()
            obj_criterion = dev.get_lockin()
            logger.info('get_lockin() returned {}'.format(obj_criterion.as_string()))
            # break

        dev.stop_logging()
        dev.disconnect()
