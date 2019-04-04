import os
import matplotlib
import matplotlib.pyplot as plt

import criterion

if __name__ == '__main__':
    # filename = os.path.join(os.path.dirname(__file__), 'data_2019-04-04_19-42-04.pickle')
    # filename = os.path.join(os.path.dirname(__file__), 'data_2019-04-04_21-06-06.pickle')
    filename = os.path.join(os.path.dirname(__file__), 'data_2019-04-04_22-39-19_horn_simple.pickle')

    list_criterion = list(criterion.iter_criterion_pickle(criterion.CriterionStepresponse, filename))
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

    # fig.savefig("test.png")
    plt.show()

    if False:
        for obj_criterion in criterion.iter_criterion_pickle(criterion.CriterionStepresponse, filename):
            pass