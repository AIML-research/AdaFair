import random
from multiprocessing import Process, Lock
import pickle
import os
import matplotlib
from sklearn.model_selection import ShuffleSplit, StratifiedShuffleSplit

from AdaFairEQOP import AdaFairEQOP

matplotlib.use('Agg')
import sys


sys.path.insert(0, 'DataPreprocessing')

import time

from load_compas_data import load_compas
from load_adult import load_adult
from load_kdd import load_kdd
from load_bank import load_bank

from my_useful_functions import calculate_performanceEQOP, plot_my_results_single_vs_amort_eqop


class serialazible_list(object):
    def __init__(self):
        self.performance = []


def create_temp_files(dataset, suffixes):
    for suffix in suffixes:
        outfile = open(dataset + suffix+ "_eqop_acc", 'wb')
        pickle.dump(serialazible_list(), outfile)
        outfile.close()

    if not os.path.exists("Images/"):
        os.makedirs("Images/")


def delete_temp_files(dataset, suffixes):
    for suffix in suffixes:
        os.remove(dataset + suffix+ "_eqop_acc")

def run_eval(dataset, iterations):
    suffixes = ['AdaFair NoCumul', 'AdaFair']
    create_temp_files(dataset, suffixes)

    if dataset == "compass-gender":
        X, y, sa_index, p_Group, x_control = load_compas("sex")
    elif dataset == "adult-gender":
        X, y, sa_index, p_Group, x_control = load_adult("sex")
    elif dataset == "bank":
        X, y, sa_index, p_Group, x_control = load_bank()
    elif dataset == "kdd":
        X, y, sa_index, p_Group, x_control = load_kdd()
    else:
        exit(1)
    create_temp_files(dataset, suffixes)



    threads = []
    mutex = []
    for lock in range(0, 2):
        mutex.append(Lock())

    random.seed(int(time.time()))

    for iter in range(0, iterations):
        start = time.time()

        sss = StratifiedShuffleSplit(n_splits=1, test_size=.5, random_state=iter)

        for train_index, test_index in sss.split(X, y):

            X_train, X_test = X[train_index], X[test_index]
            y_train, y_test = y[train_index], y[test_index]

            for proc in range(0, 2):
                threads.append(Process(target=train_classifier, args=(X_train, X_test, y_train, y_test, sa_index, p_Group, dataset + suffixes[proc], mutex[proc], proc, 500)))

            break
    for process in threads:
        process.start()

    for process in threads:
        process.join()

    print ("elapsed time = " + str(time.time() - start))

    results = []
    for suffix in suffixes:
        infile = open(dataset + suffix+ "_eqop_acc", 'rb')
        temp_buffer = pickle.load(infile)
        results.append(temp_buffer.performance)
        infile.close()

    plot_my_results_single_vs_amort_eqop(results, suffixes, "Images/vsNoCumul/" + dataset + "_eqop_single", dataset)
    delete_temp_files(dataset, suffixes)

def train_classifier(X_train, X_test, y_train, y_test, sa_index, p_Group, dataset, mutex, mode, base_learners):

    if mode == 0:
        classifier = AdaFairEQOP(n_estimators=base_learners, saIndex=sa_index, saValue=p_Group, cumul=False, CSB="CSB1")
    elif mode == 1:
        classifier = AdaFairEQOP(n_estimators=base_learners, saIndex=sa_index, saValue=p_Group, CSB="CSB1")

    classifier.fit(X_train, y_train)

    y_pred_labels = classifier.predict(X_test)

    mutex.acquire()
    infile = open(dataset+ "_eqop_acc", 'rb')
    dict_to_ram = pickle.load(infile)
    infile.close()
    dict_to_ram.performance.append(calculate_performanceEQOP(X_test, y_test, y_pred_labels, sa_index, p_Group))
    outfile = open(dataset+ "_eqop_acc", 'wb')
    pickle.dump(dict_to_ram, outfile)
    outfile.close()
    mutex.release()


if __name__ == '__main__':
    run_eval("compass-gender", 10)
    run_eval("adult-gender", 10)
    run_eval("bank", 10)
    run_eval("kdd", 10)
