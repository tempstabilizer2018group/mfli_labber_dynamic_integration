import math


class Values:
    def __init__(self):
        self.list_values_V = []
    
    def append_value(self, value_V):
        self.list_values_V.append(value_V)
        self.sorted_values_V = sorted(self.list_values_V)
  
    def get_count(self):
        return len(self.list_values_V)

    def get_median(self):
        if self.get_count() <= 2:
            return self.list_values_V[-1]
        return self.list_values_V[len(self.sorted_values_V)//2]


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


class CriterionSimple(CriterionBase):
    def determine_skip_count(self):
        return 0

        if self.x_V > 5e-6:
            return 0
        if self.x_V > 2e-6:
            return 1
        return 3

    def satisfied(self):
        '''
          return False
          return True if sufficient data is available
            x_V, y_V, r_V and theta_rad will hold the result
        '''
        assert self.values_X.get_count() == self.values_Y.get_count()
        if self.values_X.get_count() < 3:
            return False
        self.x_V = self.values_X.get_median()
        self.y_V = self.values_Y.get_median()
        self.r_V = 47.11
        self.theta_rad = 0.12
        self.quality = '47.11'
        self.skip_count = self.determine_skip_count()
        return True

class CriterionOne(CriterionBase):
    def satisfied(self):
        '''
          return False
          return True if sufficient data is available
            x_V, y_V, r_V and theta_rad will hold the result
        '''
        assert self.values_X.get_count() == self.values_Y.get_count()
        assert self.values_X.get_count() == self.values_Y.get_count()
        self.x_V = self.values_X.get_median()
        self.y_V = self.values_Y.get_median()
        self.r_V = 47.11
        self.theta_rad = 0.12
        self.quality = '47.11'
        self.skip_count = 0
        return True
