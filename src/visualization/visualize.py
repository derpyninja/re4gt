import os
import copy
import numpy as np
import pandas as pd
import geopandas as gpd
import logging
import seaborn as sns
import matplotlib.pyplot as plt

from src import utils
from src.data.datasets import EulfsDs


class EulfsVis(EulfsDs):
    def __init__(self, fn_config_data, fn_config_path, fn_vis_config, year=2019):

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

    # todo: move to new class in features submodule
    def aggregate_by_region(self, epsg="3035"):

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

        return gdf_sub

    def aggregate_by_industry(self):
        # aggregate over industries and countries
        df_all_agg_by_cntr_ind = (
            self.data_panel.groupby(["NACE1D_label", "COUNTRYW"])[self.cols_to_calc_all]
            .sum()
            .reset_index()
        )

        for col in self.cols_main:
            df_all_agg_by_cntr_ind["{}_relative".format(col)] = (
                df_all_agg_by_cntr_ind[col] / df_all_agg_by_cntr_ind["COEFF"]
            )
        return df_all_agg_by_cntr_ind

    def create_maps(
        self,
        figsize=(10, 10),
        legend=True,
        vmin=0,
        cbar_label="Employment fraction [-]",
    ):

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
            ax.set_title(column)
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
        df_all_agg_by_cntr_ind = self.aggregate_by_industry()

        plotting_cols = [
            "COEFF_share_green_gtp_mean_relative",
            "COEFF_share_green_esco_mean_relative",
            "COEFF_share_brown_esco_mean_relative",
            "COEFF_share_neutral_esco_mean_relative",
        ]

        y_var = "NACE1D_label"
        hue_var = "COUNTRYW"

        n_colors = len(df_all_agg_by_cntr_ind[hue_var].unique())
        palette = sns.color_palette("cubehelix", n_colors=n_colors)

        for x_var in plotting_cols:
            fig, ax = plt.subplots(figsize=(20, 10))

            sns.boxplot(
                data=df_all_agg_by_cntr_ind,
                x=x_var,
                y=y_var,
                color=".5",
            )

            sns.stripplot(
                data=df_all_agg_by_cntr_ind,
                x=x_var,
                y=y_var,
                hue=hue_var,
                palette=palette,
            )

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


if __name__ == "__main__":
    config_paths = "paths_config.yml"
    config_data = "data_config.yml"
    config_vis = "vis_config.yml"

    eulfs_visualiser = EulfsVis(
        fn_config_data=config_data,
        fn_config_path=config_paths,
        fn_vis_config=config_vis,
    )

    eulfs_visualiser.create_industry_barplots()
