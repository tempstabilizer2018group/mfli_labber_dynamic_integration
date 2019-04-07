import os

import criterion

if __name__ == '__main__':
    # filename = os.path.join(os.path.dirname(__file__), 'data_2019-04-04_19-42-04.pickle')
    # filename = os.path.join(os.path.dirname(__file__), 'data_2019-04-04_21-06-06.pickle')
    for filename in sorted(os.listdir(os.path.dirname(__file__))):
        if not filename.endswith('.pickle'):
            continue
        filename_save = filename.replace('.pickle', '.png')
        filename_full = os.path.join(os.path.dirname(__file__), filename)
        filename_save_full = os.path.join(os.path.dirname(__file__), filename_save)
        if os.path.exists(filename_save_full):
            continue

        criterion.plot_stepresponse(filename_full, filename_save=filename_save_full)
    if False:
        for obj_criterion in criterion.iter_criterion_pickle(criterion.CriterionStepresponse, filename):
            pass