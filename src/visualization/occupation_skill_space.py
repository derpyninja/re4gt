import os
import scipy
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

from src import dictionaries, utils
from src.data.framework import Esco
from src.plotting_utils import discrete_cmap_with_manual_colors

useful_paths = utils.UsefulPaths()


def plot_occ_sim_matrix_ordered_by_isco(
    version="unweighted",
    n_classes=10,
    cmap_type="Blues",
    annotate_isco1d=True,
    figsize=(16, 9),
    despine=False,
    save_fig=True,
    out_path=os.path.join(
        useful_paths.figure_dir,
        "occupation_skill_space",
        "occ_sim_matrix_cooc_isco_groups_{version}_cmap_{cmap_type}{n_classes}.png",
    ),
):
    """
    Plot occupation similarity matrix based on skills overlap. Based on ESCO v.1.1.

    Parameters
    ----------
    version : str
        Version of the COOC matrix.
    n_classes : int
        N classes of discrete cmap.
    cmap_type : str
        Cmap name.
    annotate_isco1d : bool
        Whether ISCO-08 1-digit categories should be indicated.
    figsize : tuple
        Figure size.
    despine : boolean
        Whether to despine all axis
    save_fig : boolean
        Whether to save the figure.
    out_path : str
        Target path for saved plots.

    Returns
    -------

    """
    esco = Esco()
    occ = esco.occupations

    # read bipartite adjecency matrix for occupations and skills
    osm = esco.read_occ_skills_matrix(return_version=version)
    osm_sparse = scipy.sparse.csr_matrix(osm.values)

    # Co-occurrence matrix
    sim_matrix_sparse = osm_sparse.dot(osm_sparse.T)
    sim_matrix = sim_matrix_sparse.toarray()
    np.fill_diagonal(sim_matrix, 0)

    # reindex matrix by isco level
    reindex_by_isco4 = occ.sort_values("iscoGroup").index.values
    x, y = np.meshgrid(reindex_by_isco4, reindex_by_isco4)

    # plot
    cmap_new = discrete_cmap_with_manual_colors(cmap_type, n_classes)

    plt.figure(figsize=figsize)
    plt.imshow(sim_matrix[x, y], cmap=cmap_new, vmin=0, vmax=n_classes)
    cbar = plt.colorbar(
        fraction=0.046, pad=0.04, orientation="vertical", extend="max"
    )
    cbar.ax.set_ylabel("Skills overlap [-]")
    plt.xlabel("Target occupations")
    plt.ylabel("Source occupations")

    if despine:
        sns.despine(left=True, bottom=True)

    # indicate isco major groups
    if annotate_isco1d:
        rdict = {110: 0000, 210: 0000, 310: 0000}
        reindex_isco_lvl1 = (
            occ.sort_values("iscoGroup")
                .iscoGroup.replace(rdict)
                .astype(str)
                .str.slice(0, 1)
                .astype(int)
        )
        df_reindex_isco_lvl1 = reindex_isco_lvl1.diff().reset_index()
        lvl1_boundaries = df_reindex_isco_lvl1.loc[
            df_reindex_isco_lvl1.iscoGroup == 1]
        tick_locs = np.insert(lvl1_boundaries.index.values, [0, 9], [0, len(occ)])

        center_ticks = []
        for i in range(len(tick_locs) - 1):
            c = (tick_locs[i] + tick_locs[i + 1]) / 2
            center_ticks.append(c)

        plt.xticks(
            center_ticks, list(dictionaries.isco_lvl1_mapping.values()), rotation=90
        )
        plt.yticks(center_ticks, list(dictionaries.isco_lvl1_mapping.values()))

        for i in df_reindex_isco_lvl1.index.values:
            if df_reindex_isco_lvl1.loc[i, "iscoGroup"] == 1:
                plt.axvline(x=i, color="grey", linewidth=1, alpha=0.5, linestyle="--")
                plt.axhline(y=i, color="grey", linewidth=1, alpha=0.5, linestyle="--")

    plt.tight_layout()

    if save_fig:
        plt.savefig(
            out_path.format(version=version, cmap_type=cmap_type, n_classes=n_classes),
            bbox_inches="tight",
            dpi=300,
        )
    else:
        plt.show()


if __name__ == "__main__":
    sns.axes_style("ticks")
    sns.plotting_context("paper", font_scale=1)

    plot_occ_sim_matrix_ordered_by_isco(version="unweighted", despine=True,
                                        cmap_type="Blues", n_classes=20)
    plot_occ_sim_matrix_ordered_by_isco(version="weighted", despine=True,
                                        cmap_type="Blues", n_classes=20)
