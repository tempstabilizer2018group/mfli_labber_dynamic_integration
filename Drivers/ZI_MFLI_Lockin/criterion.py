

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
            return self.list_values_V[1]
        return self.list_values_V[len(self.sorted_values_V)//2]


class CriterionBase:
    def __init__(self):
        self.values_X = Values()
        self.values_Y = Values()

    def append_values(self, timestamp, x_V, y_V):
        self.values_X.append_value(x_V)
        self.values_Y.append_value(y_V)


class CriterionSimple(CriterionBase):
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
        return True
