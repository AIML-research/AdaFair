import warnings
warnings.filterwarnings("ignore")
import copy
import random
from collections import defaultdict
from multiprocessing import Process, Lock
import pickle
import os
import matplotlib
from sklearn.model_selection import ShuffleSplit, train_test_split, StratifiedShuffleSplit

matplotlib.use('Agg')
import sys

from AdaFair import AdaFair

sys.path.insert(0, 'DataPreprocessing')

import time

from Competitors.AdaCost import AdaCostClassifier

from load_compas_data import load_compas
from load_adult import load_adult
from load_kdd import load_kdd

from load_bank import load_bank
from my_useful_functions import calculate_performance, plot_my_results
# from Competitors import utils as ut, funcs_disp_mist as fdm


class serialazible_list(object):
    def __init__(self):
        self.performance = []


def create_temp_files(dataset, suffixes):
    for suffix in suffixes:
        outfile = open(dataset + suffix, 'wb')
        pickle.dump(serialazible_list(), outfile)
        outfile.close()

    if not os.path.exists("Images/"):
        os.makedirs("Images/")


def delete_temp_files(dataset, suffixes):
    for suffix in suffixes:
        os.remove(dataset + suffix)


def predict(clf, X_test, y_test, sa_index, p_Group):
    y_pred_probs = clf.predict_proba(X_test)[:, 1]
    y_pred_labels = clf.predict(X_test)
    return calculate_performance(X_test, y_test, y_pred_labels, y_pred_probs, sa_index, p_Group)


def run_eval(dataset, iterations):
    # suffixes = ['Zafar et al.', 'Adaboost', 'AdaFair', 'SMOTEBoost' ]
    suffixes = ['Zafar et al.', 'Adaboost', 'AdaFair CSB2', 'AdaFair CSB1' ]

    if dataset == "compass-gender":
        X, y, sa_index, p_Group, x_control = load_compas("sex")
    elif dataset == "compass-race":
        X, y, sa_index, p_Group, x_control = load_compas("race")
    elif dataset == "adult-gender":
        X, y, sa_index, p_Group, x_control = load_adult("sex")
    elif dataset == "adult-race":
        X, y, sa_index, p_Group, x_control = load_adult("race")
    elif dataset == "bank":
        X, y, sa_index, p_Group, x_control = load_bank()
    elif dataset == "kdd":
        X, y, sa_index, p_Group, x_control = load_kdd()

    else:
        exit(1)
    create_temp_files(dataset, suffixes)

    # init parameters for zafar method (default settings)
    tau = 3.0
    mu = 1.2
    cons_type = 4
    sensitive_attrs = x_control.keys()
    loss_function = "logreg"
    EPS = 1e-6
    # sensitive_attrs_to_cov_thresh = {sensitive_attrs[0]: {0: {0: 0, 1: 0}, 1: {0: 0, 1: 0}, 2: {0: 0, 1: 0}}}
    sensitive_attrs_to_cov_thresh = {0: {0: {0: 0, 1: 0}, 1: {0: 0, 1: 0}, 2: {0: 0, 1: 0}}}
    cons_params = {"cons_type": cons_type, "tau": tau, "mu": mu,
                   "sensitive_attrs_to_cov_thresh": sensitive_attrs_to_cov_thresh}

    threads = []
    mutex = []
    for lock in range(0, 8):
        mutex.append(Lock())

    random.seed(int(time.time()))

    for iter in range(0, iterations):

        sss = StratifiedShuffleSplit(n_splits=1, test_size=0.5)
        for train_index, test_index in sss.split(X, y):

            X_train, X_test = X[train_index], X[test_index]
            y_train, y_test = y[train_index], y[test_index]

            for proc in range(0, 4):
                if proc < 3 :
                    time.sleep(1)
                    continue

                if proc > 0:
                    threads.append(Process(target=train_classifier, args=( copy.deepcopy(X_train),
                                                                           X_test, copy.deepcopy(y_train),
                                                                           y_test, sa_index, p_Group,
                                                                           dataset + suffixes[proc],
                                                                           mutex[proc],proc, 500, 1)))

                # elif proc == 0:
                #     temp_x_control_train = defaultdict(list)
                #     temp_x_control_test = defaultdict(list)
                #
                #     temp_x_control_train[sensitive_attrs[0]] = x_control[sensitive_attrs[0]][train_index]
                #     temp_x_control_test[sensitive_attrs[0]] = x_control[sensitive_attrs[0]][test_index]
                #
                #     x_zafar_train, y_zafar_train, x_control_train = ut.conversion(X[train_index], y[train_index],dict(temp_x_control_train), 1)
                #
                #     x_zafar_test, y_zafar_test, x_control_test = ut.conversion(X[test_index], y[test_index],dict(temp_x_control_test), 1)
                #
                #     threads.append(Process(target=train_zafar, args=(x_zafar_train, y_zafar_train, x_control_train,
                #                                                      x_zafar_test, y_zafar_test, x_control_test,
                #                                                      cons_params, loss_function, EPS,
                #                                                      dataset + suffixes[proc], mutex[proc],
                #                                                      sensitive_attrs)))
            break

    for process in threads:
        process.start()

    for process in threads:
        process.join()

    threads = []

    results = []
    for suffix in suffixes:
        infile = open(dataset + suffix, 'rb')
        temp_buffer = pickle.load(infile)
        results.append(temp_buffer.performance)
        infile.close()

    plot_my_results(results, suffixes, "Images/" + dataset, dataset)
    delete_temp_files(dataset, suffixes)
#
# def train_zafar(x_train, y_train, x_control_train, x_test, y_test, x_control_test, cons_params, loss_function, EPS, dataset, mutex, sensitive_attrs):
#
#     cnt = 1
#     while True:
#         if cnt > 41:
#             return
#         try:
#             w = fdm.train_model_disp_mist(x_train, y_train, x_control_train, loss_function, EPS, cons_params)
#             rates, acc, balanced_acc,_ = fdm.get_clf_stats(w, x_train, y_train, x_control_train, x_test, y_test, x_control_test, sensitive_attrs)
#             print ("Solved !!!")
#             break
#         except Exception as e:
#             if cnt % 4 == 0:
#                 cons_params['tau'] *= 1.10
#             print (str(e) + ", tau = " + str(cons_params['tau']))
#             cnt += 1
#             pass
#
#     results = dict()
#
#     results["balanced_accuracy"] = balanced_acc
#     results["accuracy"] = acc
#     results["TPR_protected"] = rates["TPR_Protected"]
#     results["TPR_non_protected"] = rates["TPR_Non_Protected"]
#     results["TNR_protected"] = rates["TNR_Protected"]
#     results["TNR_non_protected"] = rates["TNR_Non_Protected"]
#     results["fairness"] = abs(rates["TPR_Protected"] - rates["TPR_Non_Protected"]) + abs(rates["TNR_Protected"] - rates["TNR_Non_Protected"])
#
#     mutex.acquire()
#     infile = open(dataset, 'rb')
#     dict_to_ram = pickle.load(infile)
#     infile.close()
#     dict_to_ram.performance.append(results)
#     outfile = open(dataset, 'wb')
#     pickle.dump(dict_to_ram, outfile)
#     outfile.close()
#     mutex.release()


def train_classifier(X_train, X_test, y_train, y_test, sa_index, p_Group, dataset, mutex, mode, base_learners, c):
    if mode == 1:
        classifier = AdaCostClassifier(saIndex=sa_index, saValue=p_Group, n_estimators=base_learners, CSB="CSB1")
    elif mode == 2:
        classifier = AdaFair(n_estimators=base_learners, saIndex=sa_index, saValue=p_Group, CSB="CSB2", c=c, use_validation=False)
    elif mode == 3:
        classifier = AdaFair(n_estimators=base_learners, saIndex=sa_index, saValue=p_Group, CSB="CSB1", c=c, use_validation=False)
    classifier.fit(X_train, y_train)

    y_pred_probs = classifier.predict_proba(X_test)[:, 1]
    y_pred_labels = classifier.predict(X_test)

    mutex.acquire()
    infile = open(dataset, 'rb')
    dict_to_ram = pickle.load(infile)
    infile.close()
    dict_to_ram.performance.append(
        calculate_performance(X_test, y_test, y_pred_labels, y_pred_probs, sa_index, p_Group))
    outfile = open(dataset, 'wb')
    pickle.dump(dict_to_ram, outfile)
    outfile.close()
    mutex.release()


if __name__ == '__main__':
    # run_eval(sys.argv[1], int(sys.argv[2]))
    # run_eval("compass-race", 10)
    run_eval("compass-gender", 10)
    run_eval("adult-gender", 10)
    run_eval("bank", 10)
    run_eval("kdd", 10)
