import os
import copy
import numpy as np
import pandas as pd
import geopandas as gpd
import logging
import seaborn as sns
import matplotlib.pyplot as plt

from src import utils
from src.data.lfs import EulfsDs


class EulfsVis(EulfsDs):
    """Class for visualising EU-LFS data."""

    def __init__(self, fn_config_path, fn_config_data, fn_vis_config, year=2019):
        """

        Parameters
        ----------
        fn_config_path : str
        Name of yml file containing path configurations.
        fn_config_data : str
            Name of yml file containing data configurations.
        fn_vis_config : str
            Name of yml file containing visualisation configurations.
        year : int
            Year subset of eu lfs data
        """
        # inheritance
        EulfsDs.__init__(
            self=self, fn_config_data=fn_config_data, fn_config_path=fn_config_path
        )

        self.year = year

        # parse config file and unpack
        self.config_vis = utils.load_config(
            os.path.join(self.config_dir, fn_vis_config)
        )

        self.epsg = str(self.config_vis["EU_MAPS"]["epsg"])
        self.bbox_eu_epsg_3035 = self.config_vis["EU_MAPS"]["bbox_eu_epsg_3035"]
        self.missing_kwds = self.config_vis["EU_MAPS"]["missing_kwds"]
        self.edgecolor = self.config_vis["EU_MAPS"]["edgecolor"]
        self.linewidth = self.config_vis["EU_MAPS"]["linewidth"]
        self.robust_cmap_percentiles = self.config_vis["EU_MAPS"][
            "robust_cmap_percentiles"
        ]
        self.cmap = self.config_vis["EU_MAPS"]["cmap"]

        # read country borders
        self.gdf_nuts_0 = self.gdf_nuts[self.epsg].loc[
            self.gdf_nuts[self.epsg]["LEVL_CODE"] == 0
        ]

        # read data panel
        self.data_panel = self.read(year=self.year)

        # todo: needs to become less hardcoded. what about wanting to plot other
        #  variables than the GBN employment shares?
        # retrieve cols that should be aggregated
        self.cols_to_calc = self.data_panel.columns[
            self.data_panel.columns.str.startswith("COEFF_")
        ].to_list()
        self.cols_to_calc_all = copy.copy(self.cols_to_calc)
        self.cols_to_calc_all.insert(0, "COEFF")

        self.cols_main = [
            "COEFF_share_green_gtp_mean",
            "COEFF_share_green_esco_mean",
            "COEFF_share_brown_esco_mean",
            "COEFF_share_neutral_esco_mean",
        ]

    # todo: potentially move to new class in features submodule
    def aggregate_by_region(self, epsg="3035"):
        """
        Aggregate variables by NUTS regions.

        Parameters
        ----------
        epsg : str
            EPSG code of map projection

        Returns
        -------
        gdf_sub : gpd.GeoDataFrame
            Variables aggregated by NUTS regions. Ready to plot maps from.
        """
        target_fdir = os.path.join(self.path_eulfs_processed, "aggregated_by_region")
        target_fname = "eulfs_vars_by_nuts_{}_{}.shp".format(
            self.n_digits_nuts, self.year
        )
        target_fpath = os.path.join(target_fdir, target_fname)
        utils.ccdir(target_fdir)

        if not os.path.exists(target_fpath):
            # get correct shapefile
            gdf_digits_match = self.gdf_nuts[epsg].loc[
                self.gdf_nuts[epsg]["LEVL_CODE"] == self.n_digits_nuts
            ]

            # aggregate over regions
            df_all_agg = (
                self.data_panel.groupby("NUTS_ID")[self.cols_to_calc_all]
                .sum()
                .reset_index()
            )

            # combine
            gdf_sub = pd.merge(gdf_digits_match, df_all_agg, on="NUTS_ID", how="left")

            # calculate relative shares at regional level
            for col in self.cols_to_calc:
                gdf_sub["{}_relative".format(col)] = gdf_sub[col] / gdf_sub["COEFF"]

            gdf_sub.to_file(target_fpath)
        else:
            gdf_sub = gpd.read_file(target_fpath)

        return gdf_sub

    def aggregate_by_industry(self):
        """
        Aggregate variables by NACE industrial sectors.

        Returns
        -------
        df_all_agg_by_cntr_ind : pd.DataFrame
            Variables aggregated by sector-country pairs.
        """
        target_fdir = os.path.join(self.path_eulfs_processed, "aggregated_by_industry")
        target_fname = "eulfs_vars_by_nace_{}_{}".format(self.n_digits_nace, self.year)
        utils.ccdir(target_fdir)
        target_fpath = os.path.join(target_fdir, target_fname + ".pkl")

        if not os.path.exists(target_fpath):
            # aggregate over industries and countries
            # todo: make more flexible to work with different NACE digit levels
            df_all_agg_by_cntr_ind = (
                self.data_panel.groupby(["NACE1D_label", "COUNTRYW"])[
                    self.cols_to_calc_all
                ]
                .sum()
                .reset_index()
            )

            for col in self.cols_main:
                df_all_agg_by_cntr_ind["{}_relative".format(col)] = (
                    df_all_agg_by_cntr_ind[col] / df_all_agg_by_cntr_ind["COEFF"]
                )

            utils.save_df_to_files(df_all_agg_by_cntr_ind, target_fdir, target_fname)
        else:
            df_all_agg_by_cntr_ind = pd.read_pickle(target_fpath)

        return df_all_agg_by_cntr_ind

    def aggregate_by_occupation(self):
        """
        Aggregate variables by ISCO occupations.

        Returns
        -------
        df_all_agg_by_cntr_occ : pd.DataFrame
            Variables aggregated by occupation-country pairs.
        """
        target_fdir = os.path.join(
            self.path_eulfs_processed, "aggregated_by_occupation"
        )
        target_fname = "eulfs_vars_by_isco_{}_{}".format(
            self.n_digits_isco08, self.year
        )
        utils.ccdir(target_fdir)
        target_fpath = os.path.join(target_fdir, target_fname + ".pkl")

        if not os.path.exists(target_fpath):
            # aggregate over occupations and countries
            df_all_agg_by_cntr_occ = (
                self.data_panel.groupby(
                    ["ISCO{}D_label".format(self.n_digits_isco08), "COUNTRYW"]
                )[self.cols_to_calc_all]
                .sum()
                .reset_index()
            )

            for col in self.cols_main:
                df_all_agg_by_cntr_occ["{}_relative".format(col)] = (
                    df_all_agg_by_cntr_occ[col] / df_all_agg_by_cntr_occ["COEFF"]
                )

            utils.save_df_to_files(df_all_agg_by_cntr_occ, target_fdir, target_fname)
        else:
            df_all_agg_by_cntr_occ = pd.read_pickle(target_fpath)

        return df_all_agg_by_cntr_occ

    def create_maps(
        self,
        figsize=(10, 10),
        legend=True,
        vmin=0,
        cbar_label="Employment fraction [-]",
    ):
        """
        Create EU maps based on LFS data.

        Parameters
        ----------
        figsize
        legend
        vmin
        cbar_label

        Returns
        -------
        Saves plots in dedicated folder.

        """
        logger = logging.getLogger(__name__)
        logger.info("GBN employment shares by region.")

        # read aggregated data
        # todo: should be read from an existing file
        gdf_sub = self.aggregate_by_region()

        # select cols that should be plotted
        # todo: fix hardcoded retrieval of column name identifiers
        cols_to_plot = gdf_sub.columns[
            gdf_sub.columns.str.startswith("COEFF_")
            & gdf_sub.columns.str.endswith("relative")
        ].to_list()

        # parse plotting params
        legend_kwds = {"label": cbar_label, "fraction": 0.03, "extend": "max"}
        p_low, p_high = self.robust_cmap_percentiles
        xmin, xmax, ymin, ymax = self.bbox_eu_epsg_3035

        for column in cols_to_plot:
            # create figure
            fig, ax = plt.subplots(figsize=figsize)

            # dynamically set n categories and vmax
            q_high, q_low = np.nanpercentile(gdf_sub[column].values, q=[p_high, p_low])
            n_cats = np.ceil(q_high * 100)
            # vmax = np.ceil(gdf_sub[column].max() * 100) / 100
            cmap = plt.get_cmap("Greys")

            # plot data
            gdf_sub.plot(
                ax=ax,
                column=column,
                figsize=figsize,
                legend=legend,
                cmap=cmap,
                vmax=q_high,
                vmin=vmin,
                missing_kwds=self.missing_kwds,
                legend_kwds=legend_kwds,
                edgecolor=self.edgecolor,
                linewidth=self.linewidth,
            )

            # add country borders (NUTS 0)
            self.gdf_nuts_0.geometry.boundary.plot(
                ax=ax, color=None, edgecolor="black", linewidth=0.5
            )

            # labelling
            ax.set_title("{} ({})".format(column, self.year))
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)

            # layout
            ax.axis("off")
            plt.tight_layout()

            # save
            out_dir = os.path.join(
                self.figure_dir,
                "03_eulfs",
                str(self.year),
                "employment_shares_by_region",
            )
            utils.ccdir(out_dir)

            plt.savefig(
                os.path.join(out_dir, "{}.png".format(column)),
                dpi=150,
                bbox_inches="tight",
            )

            plt.close(fig)

        return None

    def create_industry_barplots(self):
        logger = logging.getLogger(__name__)
        logger.info("GBN employment shares by industry.")

        df_all_agg_by_cntr_ind = self.aggregate_by_industry()

        plotting_cols = [
            "COEFF_share_green_gtp_mean_relative",
            "COEFF_share_green_esco_mean_relative",
            "COEFF_share_brown_esco_mean_relative",
            "COEFF_share_neutral_esco_mean_relative",
        ]

        y_var = "NACE{}D_label".format(self.n_digits_nace)
        hue_var = "COUNTRYW"

        n_hue_colors = len(df_all_agg_by_cntr_ind[hue_var].unique())
        palette = sns.color_palette("cubehelix", n_colors=n_hue_colors)

        for x_var in plotting_cols:
            print("plotting variable: {}".format(x_var))

            # infer order (sorted by median in descending order)
            plotting_order = (
                df_all_agg_by_cntr_ind.loc[:, (y_var, x_var)]
                .groupby(y_var)
                .median()
                .sort_values(by=x_var, ascending=False)
                .index.values
            )

            # create plot
            fig, ax = plt.subplots(figsize=(20, 10))

            sns.boxplot(
                data=df_all_agg_by_cntr_ind,
                x=x_var,
                y=y_var,
                color=".5",
                fliersize=0,
                order=plotting_order,
            )

            sns.scatterplot(
                data=df_all_agg_by_cntr_ind.set_index([y_var, hue_var])
                .reindex(plotting_order, level=0)
                .reset_index(),
                x=x_var,
                y=y_var,
                hue=hue_var,
                style=hue_var,
                palette=palette,
                zorder=5,
                edgecolor="black"
                # order=plotting_order,
            )

            # labelling

            # Shrink current axis by x %
            shrinkage_factor = 0.2
            box = ax.get_position()
            ax.set_position(
                [box.x0, box.y0, box.width * (1 - shrinkage_factor), box.height]
            )

            # Put a legend to the right of the current axis
            ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

            ax.grid(axis="x", linestyle="--", zorder=0)
            ax.set_xlabel("{} ({})".format(x_var, self.year))
            sns.despine()

            # save
            out_dir = os.path.join(
                self.figure_dir,
                "03_eulfs",
                str(self.year),
                "employment_shares_by_industry",
            )
            utils.ccdir(out_dir)

            plt.savefig(
                os.path.join(out_dir, "{}.png".format(x_var)),
                dpi=150,
                bbox_inches="tight",
            )

            plt.close(fig)

    def create_occupation_barplots(self, n_occ="all"):
        logger = logging.getLogger(__name__)
        logger.info("GBN employment shares by occupation.")

        df_all_agg_by_cntr_occ = self.aggregate_by_occupation()

        plotting_cols = [
            "COEFF_share_green_gtp_mean_relative",
            "COEFF_share_green_esco_mean_relative",
            "COEFF_share_brown_esco_mean_relative",
            "COEFF_share_neutral_esco_mean_relative",
        ]

        y_var = "ISCO{}D_label".format(self.n_digits_isco08)
        hue_var = "COUNTRYW"

        n_colors = len(df_all_agg_by_cntr_occ[hue_var].unique())
        palette = sns.color_palette("cubehelix", n_colors=n_colors)

        for x_var in plotting_cols:
            print("plotting variable: {}".format(x_var))

            # infer order (sorted by median in descending order)
            plotting_order = (
                df_all_agg_by_cntr_occ.loc[:, (y_var, x_var)]
                .groupby(y_var)
                .median()
                .sort_values(by=x_var, ascending=False)
                .index.values
            )

            # extract and reorder data
            plotting_data = (
                df_all_agg_by_cntr_occ.set_index([y_var, hue_var])
                .reindex(plotting_order, level=0)
                .reset_index()
            )

            if n_occ != "all":
                plotting_data = plotting_data.head(n_occ * len(self.countries))
                figsize = (10, n_occ / 2)
                x_min = 0
            else:
                figsize = (10, 20)
                x_min = None

            fig, ax = plt.subplots(figsize=figsize)

            # sns.boxplot(
            #     data=df_all_agg_by_cntr_occ,
            #     x=x_var,
            #     y=y_var,
            #     color=".5",
            #     fliersize=5,
            #     order=plotting_order,
            # )

            # sns.pointplot(
            #     data=df_all_agg_by_cntr_occ.set_index([y_var, hue_var])
            #         .reindex(plotting_order, level=0)
            #         .reset_index(),
            #     x=x_var,
            #     y=y_var,
            #     join=False,
            #     scale=0.5,
            #     estimator=np.median,
            # )

            sns.scatterplot(
                data=plotting_data,
                x=x_var,
                y=y_var,
                hue=hue_var,
                style=hue_var,
                palette=palette,
                zorder=5,
                edgecolor="black"
                # order=plotting_order,
            )

            # labelling

            # Shrink current axis by x %
            shrinkage_factor = 0.2
            box = ax.get_position()
            ax.set_position(
                [box.x0, box.y0, box.width * (1 - shrinkage_factor), box.height]
            )

            # Put a legend to the right of the current axis
            ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))

            ax.grid(axis="x", linestyle="--", zorder=0)
            ax.set_xlabel("{} ({})".format(x_var, self.year))
            ax.set_xlim(xmin=x_min)
            sns.despine()

            # save
            out_dir = os.path.join(
                self.figure_dir,
                "03_eulfs",
                str(self.year),
                "employment_shares_by_occupation",
            )
            utils.ccdir(out_dir)

            plt.savefig(
                os.path.join(out_dir, "{}_n_{}.png".format(x_var, n_occ)),
                dpi=150,
                bbox_inches="tight",
            )

            plt.close(fig)


# note: need to uncomment click commands for CLI usage
# @click.command()
# @click.argument("input_filepath", type=click.Path(exists=True))
# @click.argument("output_filepath", type=click.Path())
# @click.argument("config_filepath", type=click.Path(exists=True))
def main(config_paths, config_data, config_vis):
    """
    Runs data visualisation scripts.

    Parameters
    ----------
    config_paths : str
        Name of yml file containing path configurations.
    config_data : str
        Name of yml file containing data configurations.
    config_vis : str
        Name of yml file containing visualisation configurations.
    Returns
    -------
    None
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating data visualisations.")
    pass


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    config_paths = "paths_config.yml"
    config_data = "data_config.yml"
    config_vis = "vis_config.yml"

    main(config_paths=config_paths, config_data=config_data, config_vis=config_vis)
