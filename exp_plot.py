import itertools
import os
import pickle

import matplotlib.pyplot as plt

plt.rc('text', usetex=True)
plt.rc('font', family='serif')
plt.tight_layout()


def plot_ec2(filename):
    markers = itertools.cycle(('x', '^', '+', '.', 'o', '*'))
    colors = itertools.cycle(['r', 'g', 'b', 'k', 'orange', 'm', 'y'])
    linestyles = itertools.cycle(['-', '--', '-.', ':'])

    with open(os.path.join('results', filename), 'rb') as pickle_file:
        res = pickle.load(pickle_file)

    x_vals = res['x']

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(10, 3))

    for algo in res['time']:
        mkr = next(markers)
        col = next(colors)
        lns = next(linestyles)

        ax0.plot(x_vals, res['time'][algo].values(), linestyle=lns, c=col, linewidth=3, alpha=0.7, markersize=2,
                 marker=mkr,
                 label=algo if algo != 'cplex' else 'ILP')
        x_to_consider = [x for x in x_vals if res['value'][algo][x] != 0]
        y_to_consider = [y for y in res['value'][algo].values() if y != 0]
        ax1.plot(x_to_consider, y_to_consider, linewidth=3, linestyle=lns, c=col, alpha=0.7, markersize=2, marker=mkr)

    ax0.set_xlim(min(x_vals), max(x_vals))
    ax0.set_xlabel(r'\textbf{Number of Nodes}', fontsize=13)
    ax0.set_ylabel(r'\textbf{Time (s)}', fontsize=13)
    ax0.legend(bbox_to_anchor=(0.25, 0.5), ncol=2)
    ax0.set_yscale('log')
    ax0.grid(True)

    ax1.set_xlim(min(x_vals), max(x_vals))
    ax1.set_xlabel(r'\textbf{Number of Nodes}', fontsize=13)
    ax1.set_ylabel(r'\textbf{Hourly Cost (\$)}', fontsize=13)
    ax1.grid(True)

    plt.savefig(f"plots/{filename.split('.')[0]}.pdf", bbox_inches='tight')


def plot_grid5000(filename, nw_type="ft"):
    markers = itertools.cycle(('x', '^', '+', '.', 'o', '*'))
    colors = itertools.cycle(['r', 'g', 'k', 'b', 'orange', 'm', 'y'])
    linestyles = itertools.cycle(['-', '--', '-.', ':'])

    with open(os.path.join('results', filename), 'rb') as pickle_file:
        res = pickle.load(pickle_file)
    print(res)
    x_vals = res['x']

    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(10, 3))

    for algo in res['time']:
        mkr = next(markers)
        col = next(colors)
        lns = next(linestyles)
        x_to_consider = [x for x in x_vals if res['value'][algo][x] != 0]
        y_to_consider = [y for y in res['value'][algo].values() if y != 0]
        ax0.plot(x_vals, res['time'][algo].values(), c=col, linewidth=3, linestyle=lns, markersize=4, marker=mkr,
                 label=algo if algo != 'cplex' else 'ILP', alpha=0.7)
        ax1.plot(x_to_consider, y_to_consider, c=col, linewidth=3, markersize=4, linestyle=lns, marker=mkr,
                 label=algo if algo != 'cplex' else 'ILP', alpha=0.7)

    ax0.set_xlim(min(x_vals), max(x_vals) + 0.1)
    ax0.set_yscale('log')
    if nw_type == 'random':
        ax0.set_xlabel(r'\textbf{Number of Nodes}', fontsize=13)
        ax1.set_xlabel(r'\textbf{Number of Nodes}', fontsize=13)
        plt.suptitle(r'\textbf{Random}', fontsize=14)
    else:
        ax0.set_xlabel(r'\textbf{k}', fontsize=13)
        ax1.set_xlabel(r'\textbf{k}', fontsize=13)
        plt.suptitle(r'\textbf{Fat Tree}', fontsize=14)

    ax0.set_ylabel(r'\textbf{Time (s)}', fontsize=13)

    ax1.legend(loc='upper left', ncol=2)
    ax0.grid(True)

    ax1.set_xlim(min(x_vals), max(x_vals))
    ax1.set_ylabel(r'\textbf{Number of Machines}', fontsize=13)

    ax1.grid(True)

    plt.savefig(f"plots/{nw_type}.pdf", bbox_inches='tight')


if __name__ == '__main__':
    plot_ec2('res_ec2_60s.pickle')
    plot_grid5000('res_fat-tree_60s.pickle', 'ft')
    plot_grid5000('res_random_60s.pickle', 'random')
