import os
import math
import time
import pickle

def get_pickle_filename(filename_helper):
    time_string = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
    return os.path.join(os.path.dirname(__file__), 'data_{}{}.pickle'.format(time_string, filename_helper))

def pickle_dump(list_criterions, filename_helper):
    l = list(map(lambda c: c.get_values(), list_criterions))
    filename = get_pickle_filename(filename_helper)
    with open(filename, 'wb') as f:
        pickle.dump(l, f)

def iter_xy_pickle(filename):
    with open(filename, 'rb') as f:
        list_pickle = pickle.load(f)

    for d in list_pickle:
        list_x = d['x']
        list_y = d['y']
        assert len(list_x) == len(list_y)
        yield list_x, list_y

def iter_criterion_pickle(criterion_class, filename):
    timestamp = 0
    obj_criterion_last = None
    for list_x, list_y in iter_xy_pickle(filename):
        assert len(list_x) == len(list_y)
        obj_criterion = criterion_class(obj_criterion_last)
        for x, y in zip(list_x, list_y):
            obj_criterion.append_values(timestamp, x, y)

        obj_criterion_last = obj_criterion

        yield obj_criterion

def plot_stepresponse(filename, show=False, filename_save=None):
    import matplotlib.pyplot as plt

    list_criterion = list(iter_criterion_pickle(CriterionStepresponse, filename))
    # Skip the first: It doesn't have a 'last' which is needed for the calculation
    list_criterion = list_criterion[1:]
    list_stepresponses_X = list(map(lambda crit: crit.get_stepresponse(), list_criterion))
    list_stepresponses_X = sorted(list_stepresponses_X, key=lambda crit: crit.rating, reverse=True)
    count = len(list_stepresponses_X)//10
    list_stepresponses_X = list_stepresponses_X[:count]

    fig, ax = plt.subplots()
    
    for stepresponse in list_stepresponses_X:
        list_Y = list(stepresponse.list_values_scaled)
        list_X = list(range(0, len(list_Y)))
        ax.plot(list_X, list_Y)

    ax.set(xlabel='lockin periods (33ms)', ylabel='step 0 to 1', title='Step response normalized')
    ax.set_ylim(ymin=0)
    ax.grid()

    if filename_save is not None:
        fig.savefig(filename_save)
    if show:
        plt.show()

class Values:
    def __init__(self):
        self.list_values_V = []
    
    def append_value(self, value_V):
        self.list_values_V.append(value_V)
        self.sorted_values_V = sorted(self.list_values_V)
  
    def get_count(self):
        return len(self.list_values_V)

    def get_median(self, skip=0):
        if self.get_count() <= 2:
            return self.list_values_V[-1]
        # The point in the middle. If we skip the first datapoints, the middle moves to the right
        middle = (len(self.sorted_values_V)+skip)//2
        # If skip is big, watch out not to be out of range
        middle = min(middle, len(self.sorted_values_V)-1)
        return self.sorted_values_V[middle]


class CriterionSkip:
    def __init__(self):
        self.last_criterion = None
        self.skip_count = None
        self.x_V = math.nan
        self.y_V = math.nan
        self.r_V = math.nan
        self.theta_rad = math.nan
        self.quality = math.nan

criterion_skip = CriterionSkip()

class CriterionBase:
    def __init__(self, last_criterion):
        self.last_criterion = last_criterion
        self.values_X = Values()
        self.values_Y = Values()

    def append_values(self, timestamp, x_V, y_V):
        self.values_X.append_value(x_V)
        self.values_Y.append_value(y_V)

    def get_count(self):
        return self.values_X.get_count()

    def get_values(self):
        return dict(x=self.values_X.list_values_V, y=self.values_Y.list_values_V)
    
    def as_string(self):
        return '{c.x_V:1.9f} {c.y_V:1.9f} {c.r_V:1.9f} {c.theta_rad:1.3f}'.format(c=self)

class CriterionSimple(CriterionBase):
    def determine_skip_count(self):
        return 0
        if self.x_V > 5e-6:
            return 0
        if self.x_V > 2e-6:
            return 1
        return 2

    def satisfied(self):
        '''
          return False
          return True if sufficient data is available
            x_V, y_V, r_V and theta_rad will hold the result
        '''
        assert self.values_X.get_count() == self.values_Y.get_count()
        self.x_V = self.values_X.get_median(skip=2) # empirisch from the step response: The first two samples are wrong
        self.y_V = self.values_Y.get_median()
        self.r_V = 47.11
        self.theta_rad = 0.12
        self.quality = '47.11'
        self.skip_count = 0
        if self.x_V < 2e-6:
            # The signal is small
            # success
            if self.get_count() >= 6:
                # success
                return True
        if self.x_V < 4e-6:
            # The signal is medium
            if self.get_count() >= 6:
                # success
                return True
        if self.get_count() >= 20:
            # success
            return True
        # We need more samples
        return False

class CriterionOne(CriterionBase):
    def satisfied(self):
        assert self.values_X.get_count() == self.values_Y.get_count()
        self.x_V = self.values_X.get_median()
        self.y_V = self.values_Y.get_median()
        self.r_V = 47.11
        self.theta_rad = 0.12
        self.quality = '47.11'
        self.skip_count = 0
        return True

class CriterionLogging(CriterionBase):
    def satisfied(self):
        assert self.values_X.get_count() == self.values_Y.get_count()
        if self.values_X.get_count() < 10:
            return False
        self.x_V = self.values_X.get_median()
        self.y_V = self.values_Y.get_median()
        self.r_V = 47.11
        self.theta_rad = 0.12
        self.quality = '47.11'
        self.skip_count = 0
        return True

class Stepresponse:
    def __init__(self, list_V, list_last_V):
        import statistics

        self.list_V = list_V
        self.list_last_V = list_last_V
        self.median_last = list_last_V.get_median()
        self.median = list_V.get_median()
        self.rating = abs(self.median_last-self.median)/statistics.stdev(self.list_V.list_values_V)
    
    @property
    def list_values_scaled(self):
        l = map(lambda v: (v-self.median_last)/(self.median-self.median_last), self.list_V.list_values_V)
        return l

class CriterionStepresponse(CriterionBase):
    def get_stepresponse(self):
        stepresponse_X = Stepresponse(self.values_X, self.last_criterion.values_X)
        return stepresponse_X

    def satisfied(self):
        assert False
