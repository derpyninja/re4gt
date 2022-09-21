import os
import numpy as np
import pandas as pd
from tqdm import tqdm
import geopandas as gpd

import seaborn as sns
from matplotlib import colors
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

from src import utils, plotting_utils
from src.data.framework import Esco
from src.modelling import occupation_distance

# init objects used by classes below
esco = Esco()
useful_paths = utils.UsefulPaths()


class ReskillingPathways:
    """
    Class for simulating occupation transition pathways and re/upskilling interventions
    for EU-LFS labour force survey data.
    """

    def __init__(self, osm_version="weighted", sim_metric="cooc", lfs_data=None):
        """

        Parameters
        ----------
        osm_version : str
            Version of occupation skill matrix. Whether optional skills are weighted.
        sim_metric : str
            Version of occupation similarity metric. One of self.sim_metrics
        lfs_data : pd.DataFrame
            Input EU-LFS data.
        """

        # -----------------------------------------------------------------------------
        # Parameters
        # -----------------------------------------------------------------------------

        # load params from init
        self.osm_version = osm_version
        self.sim_metric = sim_metric
        self.lfs_data = lfs_data

        # phaseout scenario implementations
        self.phaseout_scenarios = ["coal", "brown_techchange", "brown"]

        # coefficient weights for each scenario
        self.transition_pool_weights = {
            "coal": "COEFF",
            "brown_techchange": "COEFF_share_brown_slt",
            "brown": "COEFF_share_brown_sl",
        }

        # criteria for coal phase-out scenario
        self.coal_occupations = {
            "Mining, manufacturing and construction supervisors": "312",
            "Mining and mineral processing plant operators": "811",
            "Manufacturing, mining, construction, and distribution managers": "132",
            "Mining and construction labourers": "931",
        }
        self.coal_industries = {
            "Electricity, Gas, Steam and Air Conditioning Supply": "D",
            "Mining and Quarrying": "B",
        }

        # occupation similarity thresholds
        self.trans_thresh = None
        self.trans_thresh_pc_approach = None

        # desirable target categories
        self.target_cats = {"neutral", "green"}

        # OSM versions
        self.osm_versions = ["weighted", "unweighted"]

        # occupation similarity metrics
        self.sim_metrics = ["cooc", "shortage_excess_avg", "shortage", "excess"]

        # whether a high or low occupation similarity score is better depends on metric
        self.best_choice = {
            "cooc": "max",
            "shortage_excess_avg": "min",
            "shortage": "min",
            "excess": "min",
        }

        # granularity levels in osim
        self.level_dict = {1: "esco_5_digit", 2: "isco_4_digit", 3: "isco_3_digit"}

        # mapping to threshold categories
        self.threshold_categories = {
            "esco_5_digit": "viable_high",
            "isco_4_digit": "viable",
            "isco_3_digit": "viable_low",
        }

        # avoid transitions to same occupation
        # note: actually this should always be set to False
        self.osim_diag_zeros = False

        # checks
        assert self.sim_metric in self.sim_metrics
        assert self.osm_version in self.osm_versions

        # -----------------------------------------------------------------------------
        # DATA
        # -----------------------------------------------------------------------------
        # load similarity and annotate granularity levels
        self.df_occ_sim = occupation_distance.occ_sim_matrix_by_levels(
            sim_metric=self.sim_metric,
            osm_version=self.osm_version,
            diagonal_zeros=self.osim_diag_zeros,
        )

        # Read geodata with NUTS regions
        self.gdf = gpd.read_file(
            os.path.join(
                useful_paths.data_raw,
                "geodata",
                "NUTS_RG_03M_2021_4326_LEVL_2",
                "NUTS_RG_03M_2021_4326_LEVL_2.shp",
            )
        )

        # based on full, unaggregated matrix
        self.trans_thresh_pc_approach = np.percentile(
            self.df_occ_sim.values.flatten(), q=(96, 99)
        )

    def get_occs(self, level="isco_3_digit", lfs_subset=None):
        """
        Obtain list of occupations for given ISCO granularity level that are available in
        the occupation similarity matrix.

        Parameters
        ----------
        level : str
            ISCO occupation granularity level. One of (isco_3_digit, isco_4_digit).
        lfs_subset : pd.DataFrame
            Note: currently only works for ISCO 3D data
        Returns
        -------
        pd.DataFrame
            List of available occupations with index numbers matching those of the
            occ sim matrix.
        """
        lvl_code = utils.reverse_dict(self.level_dict)[level]
        ndigs = {"isco_4_digit": 4, "isco_3_digit": 3}
        occs_all = esco.isco_groups[
            esco.isco_groups.code.str.len() == ndigs[level]
        ].loc[:, ("conceptUri", "preferredLabel", "code")]
        occs_available = (
            self.df_occ_sim.index.get_level_values(lvl_code)
            .unique()
            .sort_values()
            .values
        )

        # subset
        occs_at_level = occs_all[occs_all.code.isin(occs_available)].reset_index(
            drop=True
        )

        # optionally join country-level means from lfs data set
        if lfs_subset is not None:
            agg_dict = {
                "COEFF": np.nansum,
                "INCDECIL": np.nanmedian,
                "share_green": np.nanmean,
                "share_brown_sl": np.nanmean,
                "share_brown_slt": np.nanmean,
                "share_neutral_sl": np.nanmean,
                "annual_earnings": np.nanmean,
            }

            isco_avg = lfs_subset.groupby(["ISCO", "ISCO3D_label"]).aggregate(agg_dict)

            # define the GBN category of an ISCO 3D group as the one with the
            # highest fraction (of ESCO occupations)
            isco_avg["category"] = isco_avg[
                ["share_green", "share_brown_sl", "share_neutral_sl"]
            ].idxmax(axis=1)

            isco_avg = isco_avg.replace(
                to_replace={
                    "category": {
                        "share_green": "green",
                        "share_brown_sl": "brown",
                        "share_neutral_sl": "neutral",
                    }
                }
            )

            # join
            occs_at_level = pd.merge(
                occs_at_level, isco_avg, left_on="code", right_on="ISCO", how="left"
            )

        return occs_at_level

    def sim_matrix_at_level(self, level="isco_3_digit", agg_func="mean"):
        """
        Average the original occupation similarity matrix at a specific occupation
        group level.

        Note: first aggregating the occupation-skills matrix at a specific level and
         then calculating the co-occurrence yields the same result.

        Todo: not sure if the above holds true for the shortage/excess metrics.

        Parameters
        ----------
        level : str
            Occupation granularity level. One of self.level_dict.values()
        agg_func : str or np.func
            Function to be used for aggregating occupation similarities

        Returns
        -------
        sim_matrix_agg : pd.DataFrame
            Aggregated occupation similarity matrix.
        """
        lvl_code = utils.reverse_dict(self.level_dict)[level]
        sim_matrix_agg = (
            self.df_occ_sim.groupby(level=lvl_code, axis=0)
            .aggregate(agg_func)
            .groupby(level=lvl_code, axis=1)
            .aggregate(agg_func)
        )
        return sim_matrix_agg

    def plot_sim_matrix_at_level(
        self,
        level="isco_3_digit",
        agg_func="mean",
        classify=False,
        vmax=10,
        cmap_type="Blues",
        over_vmax_color="pink",
        mask_upper=True,
        save_fig=True,
        out_dir=os.path.join(useful_paths.figure_dir, "reskilling_simulation"),
    ):
        """
        Plot numeric or classified occupation similarity matrix for a given granularity
        level.

        Parameters
        ----------
        level : str
            Occupation granularity level.
        agg_func : str
            Aggregation function
        classify : bool
            Whether to classifiy numeric matrix into non-viable/viable/highly viable
        vmax : int
            Max value to show and number of colors in cbar.
        cmap_type : str
            Colormap
        over_vmax_color : str
            Color of tip if cbar is extended.
        mask_upper : bool
            Whether to mask the upper triangle.
        save_fig : bool
            Whether to save the plot.
        out_dir : os.Path
            Path to output directory.

        Returns
        -------
        ax : mpl ax object
            Figure axis.
        """

        # read mat
        sim_mat = self.sim_matrix_at_level(level=level, agg_func=agg_func).values
        if mask_upper:
            sim_mat = np.tril(sim_mat)

        if classify:
            q_viable, q_highly_viable = self.trans_thresh_pc_approach

            sim_mat[sim_mat < q_viable] = 0
            sim_mat[(sim_mat >= q_viable) & (sim_mat < q_highly_viable)] = 1
            sim_mat[sim_mat >= q_highly_viable] = 2

        # define cmap
        if not classify:
            cmap = plotting_utils.discrete_cmap_with_manual_colors(cmap_type, vmax)
            cmap.set_over(over_vmax_color)
            norm = None
            label = "Skills {} [-]".format(self.sim_metric.capitalize())
            extend = "max"
        else:
            cmap = colors.ListedColormap(["white", "lightblue", "darkblue"])
            bounds = [0, 1, 2, 3]
            norm = colors.BoundaryNorm(bounds, cmap.N)
            vmax = None
            label = "Transition viability"
            extend = None

        # plot
        fig, ax = plt.subplots()
        im = ax.imshow(sim_mat, cmap=cmap, vmax=vmax, norm=norm)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, cax=cax, orientation="vertical", label=label, extend=extend)

        ax.set_ylabel("Source occupations ({})".format(level))
        ax.set_xlabel("Target occupations ({})".format(level))
        sns.despine()

        if save_fig:
            out_folder = "{}_metric_thresh_cal_diagzero_{}".format(
                self.sim_metric, self.osim_diag_zeros
            )
            utils.ccdir(os.path.join(out_dir, out_folder))

            plt.savefig(
                os.path.join(
                    out_dir,
                    out_folder,
                    "occ_sim_{}_classified_{}.png".format(level, classify),
                ),
                dpi=300,
            )

        return ax

    def calc_sim_means_by_level(self):
        """
        Calculate mean and sd of group-wise occupation similarity scores for different
        granularity levels.

        Returns
        -------
        df_sim_container : pd.DataFrame
            Mean and sd of occ_sim grouped by level and occupation
        """

        # iterate over groups
        sim_container = {}

        for level in [1, 2, 3]:
            group_res = {}
            for group in self.df_occ_sim.index.get_level_values(level).values:
                # subset row
                row_subset = self.df_occ_sim.loc[
                    self.df_occ_sim.index.get_level_values(level) == group
                ]

                # subset col
                combined_subset = row_subset.loc[
                    :, row_subset.columns.get_level_values(level) == group
                ].values.flatten()

                # stats
                mean = combined_subset.mean()
                sd = combined_subset.std()

                # append
                group_res[group] = [mean, sd]

            # append
            sim_container[level] = group_res

        # to dfs
        df_sim_container = pd.concat(
            {k: pd.DataFrame(v).T for k, v in sim_container.items()}, axis=0
        ).reset_index()

        df_sim_container = df_sim_container.rename(
            columns={
                "level_0": "level",
                "level_1": "occupation",
                0: "sim_mean",
                1: "sim_sd",
            }
        )

        # rename levels
        df_sim_container = df_sim_container.replace(
            to_replace={"level": self.level_dict}
        )

        return df_sim_container

    def calc_transition_thresholds(
        self,
        save_plots_by_level=True,
        save_plot_overview=True,
        show_plots=True,
        save_data=True,
        out_dir=os.path.join(useful_paths.figure_dir, "reskilling_simulation"),
    ):
        """
        Calculate average transition numbers within different occupation granularity
        levels. This is a crucial parameter for the calibration of a threshold
        constraining occupation transition & reskilling simulations.

        Parameters
        ----------
        save_plots_by_level : bool
            Whether plots by granularity level should be saved.
        save_plot_overview : bool
            Whether overview plot should be saved.
        show_plots : bool
            Whether plots should be shown.
        save_data : bool
            Whether numeric data should be stored
        out_dir : os.Path
            Path to output directory.

        Returns
        -------
        df_within_group_results : pd.DataFrame
            Mean and sd of within-group occupation similarities.
        """

        # load data
        df_sim_container = self.calc_sim_means_by_level()

        # create output folder
        if save_plots_by_level or save_data:
            out_folder = "{}_metric_thresh_cal_diagzero_{}".format(
                self.sim_metric, self.osim_diag_zeros
            )
            utils.ccdir(os.path.join(out_dir, out_folder))

        within_group_results = {}
        for level in list(self.level_dict.values()):
            plot_data = df_sim_container[df_sim_container.level == level]

            # calc stats
            within_group_mean = plot_data.sim_mean.mean()
            within_group_sd = plot_data.sim_mean.std()
            within_group_results[level] = [
                within_group_mean,
                within_group_sd,
                within_group_mean - within_group_sd,
                within_group_mean + within_group_sd,
            ]

            if save_plots_by_level:
                # plot
                fig = plt.figure()
                plt.hist(plot_data.sim_mean, bins=20, color="lightgrey")

                plt.axvline(within_group_mean, linestyle="--", zorder=1)
                plt.text(
                    within_group_mean,
                    0,
                    "$\mu = {:.2f}$".format(within_group_mean),
                    rotation=0,
                    va="bottom",
                    ha="left",
                    fontsize=8,
                )

                plt.grid(linestyle=":")
                plt.xlabel("Skills {} [-]".format(self.sim_metric))
                plt.ylabel("Number of {} groups [-]".format(level))

                sns.despine()
                plt.tight_layout()

                plt.savefig(
                    os.path.join(out_dir, out_folder, "{}.png".format(level)),
                    dpi=300,
                )

            if not show_plots:
                plt.cla()
                plt.clf()

        # combine and save means & sd
        df_within_group_results = pd.DataFrame(
            data=within_group_results, index=["mean", "sd", "mean-sd", "mean+sd"]
        ).T

        # annotate categories
        df_within_group_results["threshold_category"] = [
            self.threshold_categories[lvl]
            for lvl in df_within_group_results.index.values
        ]

        if save_data:
            df_within_group_results.to_csv(
                os.path.join(
                    out_dir,
                    out_folder,
                    "within_group_similarities.csv",
                )
            )

        if save_plot_overview:
            # overview
            plt.figure()
            plt.hist(
                self.df_occ_sim.values.flatten(), bins=50, log="y", color="lightgrey"
            )

            plt.grid(linestyle=":")
            plt.xlabel("Skills overlap [-]")
            plt.ylabel("Number of occupations, logged [-]")

            # annotate
            viable = df_within_group_results.loc["isco_4_digit", "mean-sd"]
            plt.axvline(viable, linestyle="--", zorder=1, color="blue")
            plt.text(
                viable,
                10e6,
                "viable = {:.1f}".format(viable),
                rotation=0,
                va="top",
                ha="left",
                fontsize=8,
                color="white",
                bbox=dict(facecolor="blue", alpha=1),
            )

            highly_viable = df_within_group_results.loc["esco_5_digit", "mean-sd"]
            plt.axvline(highly_viable, linestyle="--", zorder=1, color="darkblue")
            plt.text(
                highly_viable,
                10e5,
                "highly viable = {:.1f}".format(highly_viable),
                rotation=0,
                va="top",
                ha="left",
                fontsize=8,
                color="white",
                bbox=dict(facecolor="darkblue", alpha=1),
            )

            sns.despine()
            plt.tight_layout()

            plt.savefig(
                os.path.join(
                    out_dir,
                    "{}_metric_thresh_cal_diagzero_{}".format(
                        self.sim_metric, self.osim_diag_zeros
                    ),
                    "overview_of_thresholds.png",
                ),
                dpi=300,
            )

            if not show_plots:
                plt.cla()
                plt.clf()

        return df_within_group_results

    def define_transition_pool(self, scenario, country):
        """
        Extract a subset of the LFS data based on phase-out scenario and country.

        Parameters
        ----------
        scenario : str
            Phase-out scenario
        country : str
            Country code (ISO)

        Returns
        -------
        transition_pool : pd.DataFrame
            Subset of LFS data specific to scenario and country.
        """
        transition_pool = None
        lfs_data_country = self.lfs_data[self.lfs_data["COUNTRYW"] == country]
        if scenario == "coal":
            occ_subset = lfs_data_country["ISCO3D_label"].isin(
                list(self.coal_occupations.keys())
            )
            ind_subset = lfs_data_country["NACE1D_label"].isin(
                list(self.coal_industries.keys())
            )

            transition_pool = lfs_data_country[occ_subset & ind_subset]
        elif scenario == "brown_techchange":
            raise NotImplementedError()
        elif scenario == "brown":
            raise NotImplementedError()
        else:
            raise NotImplementedError()

        return transition_pool

    def simulate_baseline(
        self,
        level="isco_3_digit",
        countries=None,
        scenarios=None,
        out_dir=os.path.join(useful_paths.figure_dir, "reskilling_simulation"),
    ):
        """
        Simulate occupation transitions for given phase-out scenarios without
        re/upskilling or regional constraints (baseline).

        Parameters
        ----------
        level : str
            Granularity level
        countries : list of str
            Countries to process.
        scenarios : list of str
            Phase-out scenarios to process.
        out_dir : os.Path
            Path to output directory

        Returns
        -------
        simulation_results : dict of dicts of pd.DataFrame's
            Nested dictionary containing simulation results by (1) scenario and (2)
            country. Simulation results are stored as pd.DataFrame and contain worker-
            level information about: number of viable transitions, target occupation,
            earnings changes, etc.
        """
        # define transition pool based on scenario
        if scenarios is None:
            scenarios = self.phaseout_scenarios
        # todo: extend country selection
        if countries is None:
            countries = ["DE"]

        # read sim matrix
        similarity_matrix = self.sim_matrix_at_level(level=level).values

        # define transition thresholds
        q_viable, q_highly_viable = self.trans_thresh_pc_approach

        # -----------------------------------------------------------------------------
        # Scenario loop
        # -----------------------------------------------------------------------------
        simulation_results = {}
        for scenario in scenarios:
            print("scenario: {}".format(scenario))
            # select scenario-specific weighting coefficient
            coeff_weight = self.transition_pool_weights[scenario]

            # create results dir
            out_folder = "{}_occupations_by_{}".format(scenario, coeff_weight.lower())
            utils.ccdir(os.path.join(out_dir, out_folder))

            # -------------------------------------------------------------------------
            # Country loop
            # -------------------------------------------------------------------------
            for country in countries:
                print("  country: {}".format(country))
                # select scenario- and country-specific transition pool
                df_transition_pool = self.define_transition_pool(
                    scenario=scenario, country=country
                )

                # read occupation list coherent with sim matrix and enriched by means
                # across several LFS variables
                df_occs = self.get_occs(level=level, lfs_subset=df_transition_pool)

                # populate transition pool dict
                transition_pool_dict = {}
                for i, s in df_transition_pool.iterrows():
                    transition_pool_dict[s.ISCO3D_label] = s.ISCO3D

                # save numbers by source industry
                df_transition_pool.groupby("NACE1D_label").sum().iloc[:, :4].to_csv(
                    os.path.join(out_dir, "source_transition_pool.csv")
                )

                # ---------------------------------------------------------------------
                # Worker-level transition simulation
                # ---------------------------------------------------------------------
                transition_number_data = []
                for i, search_obs in tqdm(df_transition_pool.iterrows()):
                    search_label = search_obs.ISCO3D_label
                    idx = df_occs.loc[
                        df_occs["preferredLabel"] == search_label
                    ].index.values[0]

                    target_occs = occupation_distance.find_closest(
                        i=idx, similarity_matrix=similarity_matrix, df=df_occs
                    )

                    # filter: viable, green or neutral
                    target_occs_filtered = target_occs.loc[
                        target_occs.similarity > q_viable
                    ]
                    target_occs_filtered = target_occs_filtered.loc[
                        target_occs_filtered.category != "brown"
                    ]
                    target_occs_filtered = target_occs_filtered.dropna()

                    # earnings delta to next closest occupation
                    target_occs_filtered["wage_diff"] = (
                        target_occs_filtered["annual_earnings"]
                        - search_obs["annual_earnings"]
                    )

                    # if I know the wage of the source occupation, choose transition
                    # that minimises wage losses
                    if search_obs["annual_earnings"] != np.nan:
                        target = target_occs_filtered.sort_values("wage_diff").tail(1)
                    else:
                        # if not, choose transition with highest target wage
                        target = target_occs_filtered.sort_values(
                            "annual_earnings"
                        ).tail(1)

                    # check if viable transition exists
                    if not target.empty:
                        # Every worker transitions to the next-closest job and I
                        # evaluate the wage difference
                        search_obs["earnings_delta_closest_switch"] = (
                            target["annual_earnings"].values[0]
                            - search_obs["annual_earnings"]
                        )
                        search_obs["earnings_delta_closest_switch_sum"] = (
                            target["annual_earnings"].values[0]
                            - search_obs["annual_earnings"]
                        ) * search_obs[coeff_weight]
                        search_obs["n_viable_transitions"] = target_occs_filtered.shape[
                            0
                        ]
                        search_obs["n_viable_transitions_sum"] = (
                            target_occs_filtered.shape[0] * search_obs[coeff_weight]
                        )
                        search_obs["transition_viable"] = True
                        search_obs["transition_target"] = target[
                            "preferredLabel"
                        ].values[0]
                        search_obs["target_category"] = target.category.values[0]
                    else:
                        # if no viable transition exists, I assume (FOR NOW), that the
                        # salary is lost entirely and has to be provided by the state
                        # (a bit unrealistic)
                        search_obs["earnings_delta_closest_switch"] = search_obs[
                            "annual_earnings"
                        ] * (-1)
                        search_obs["earnings_delta_closest_switch_sum"] = (
                            search_obs["annual_earnings"]
                            * (-1)
                            * search_obs[coeff_weight]
                        )
                        search_obs["n_viable_transitions"] = 0
                        search_obs["n_viable_transitions_sum"] = 0
                        search_obs["transition_viable"] = False
                        search_obs["transition_target"] = None
                        search_obs["target_category"] = None

                    transition_number_data.append(search_obs)

                # to df
                df_transition_numbers = pd.concat(transition_number_data, axis=1).T
                df_transition_numbers = df_transition_numbers.infer_objects()

                # scale
                df_transition_numbers["earnings_delta_closest_switch_sum_mio"] = (
                    df_transition_numbers["earnings_delta_closest_switch_sum"] / 10**6
                )

                # ---------------------------------------------------------------------
                # regional aggregation
                # ---------------------------------------------------------------------
                # Calculate avg number of transitions per threatened job
                # df_transition_numbers_by_nuts = df_transition_numbers.groupby(
                #     "NUTS_ID"
                # ).sum()
                # df_transition_numbers_by_nuts["n_viable_transitions_rel"] = (
                #     df_transition_numbers_by_nuts.n_viable_transitions_sum
                #     / df_transition_numbers_by_nuts[coeff_weight]
                # )
                #
                # # to gdf
                # gdf_transition_numbers_by_nuts = pd.merge(
                #     self.gdf[self.gdf["CNTR_CODE"] == country],
                #     df_transition_numbers_by_nuts.reset_index(),
                #     on="NUTS_ID",
                #     how="left",
                # )

                # store results
                simulation_results[scenario] = {country: df_transition_numbers}

        return simulation_results

    def simulate_baseline_regional(self):
        pass

    def simulate_upskilling(self):
        pass

    def simulate_upskilling_regional(self):
        pass


if __name__ == "__main__":
    from src.data.lfs import EuLfs

    # ---------------------------------------------------------------------
    # Input data
    # ---------------------------------------------------------------------
    # earnings data for Germany
    earnings_deciles = pd.read_csv(
        os.path.join(useful_paths.data_raw, "metadata", "earnings_per_deciles.csv"),
    )

    # EU-LFS data
    config = utils.load_config(
        os.path.join(useful_paths.config_dir, "eu_lfs_config.yml")
    )
    lfs = EuLfs(config=config)

    df_all = lfs.read_preprocessed_file(
        year=2019, input_fname_lfs="eu_lfs_merged_{year}_with_final_unweighted_shares"
    )

    df_all["INCDECIL"] = df_all["INCDECIL"].astype(float)
    df_all = pd.merge(
        df_all,
        earnings_deciles,
        left_on=["COUNTRYW", "INCDECIL"],
        right_on=["country", "decile"],
        how="left",
    )

    # define the GBN category of an ISCO 3D group as the one with the highest fraction (of ESCO occupations)
    df_all["category"] = df_all[
        ["share_green", "share_brown_sl", "share_neutral_sl"]
    ].idxmax(axis=1)

    df_all = df_all.replace(
        to_replace={
            "category": {
                "share_green": "green",
                "share_brown_sl": "brown",
                "share_neutral_sl": "neutral",
            }
        }
    )

    # ---------------------------------------------------------------------
    # Simulate baseline for coal phase-out scenario in Germany
    # ---------------------------------------------------------------------

    rp = ReskillingPathways(osm_version="weighted", sim_metric="cooc", lfs_data=df_all)
    baseline_simulations = rp.simulate_baseline(
        level="isco_3_digit", countries=["DE"], scenarios=["coal"]
    )
    print(baseline_simulations)
