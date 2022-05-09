import os
import numpy as np
import pandas as pd
import geopandas as gpd

import src
from src import UsefulPaths, utils
from src.data.framework import Esco
useful_paths = src.UsefulPaths()


class EuLfs(UsefulPaths):
    def __init__(
            self,
            config=None,
            path_eulfs_raw=None,
            path_eulfs_raw_yf=None,
            path_eulfs_interim=None,
            path_eulfs_processed=None,
            fmt_folder=None,
            fmt_file=None,
    ):
        # inherit path structure
        UsefulPaths.__init__(self=self)

        # paths
        if config is None:
            self.config = None
            self.path_eulfs_raw = path_eulfs_raw
            self.path_eulfs_raw_yf = path_eulfs_raw_yf
            self.path_eulfs_interim = path_eulfs_interim
            self.path_eulfs_processed = path_eulfs_processed
            self.fmt_folder = fmt_folder
            self.fmt_file = fmt_file
        else:
            self.config = config
            self.path_eulfs_raw = self.config["paths"]["raw"]
            self.path_eulfs_raw_yf = self.config["paths"]["raw_yf"]
            self.path_eulfs_interim = self.config["paths"]["interim"]
            self.path_eulfs_processed = self.config["paths"]["processed"]
            self.fmt_folder = self.config["paths"]["fmt_folder"]
            self.fmt_file = self.config["paths"]["fmt_file"]

            # countries and years
            self.years = self.config["preprocessing"]["years"]
            self.countries = self.config["preprocessing"]["countries"]

            # special cases
            self.countries_isco08_2d = self.config["preprocessing"]["countries_isco08_2d"]
            self.countries_isco08_1d = self.config["preprocessing"]["countries_isco08_1d"]
            self.countries_nuts_1d = self.config["preprocessing"]["countries_nuts_1d"]
            self.countries_nuts_0d = self.config["preprocessing"]["countries_nuts_0d"]

            self.scaling_factor_coeff = self.config["preprocessing"][
                "scaling_factor_coeff"]
            self.pension_age = self.config["preprocessing"]["pension_age"]

            self.variables = self.config["preprocessing"]["variables"]
            self.na_values = self.config["preprocessing"]["na_values"]
            self.dtypes_in = self.config["preprocessing"]["dtypes_in"]
            self.dtypes_out = self.config["preprocessing"]["dtypes_out"]

    def _build_fpath(self, country, year):
        # define fpath
        folder = self.fmt_folder.format(country=country)
        file = self.fmt_file.format(country=country, year=year)
        fpath_full = os.path.join(self.path_eulfs_raw_yf, folder, file)
        return fpath_full

    def read_raw_file(self, country, year):
        fpath_full = self._build_fpath(country=country, year=year)
        return pd.read_csv(fpath_full)

    def read_filtered_file(
            self,
            country,
            year,
            variables=None,
            na_values=None,
            dtypes_in=None,
            isco_colname_all_digits="ISCO",
            return_filtering_stats=True
    ):
        # read selection of variables and optionally assign dtypes and NA vals
        df_cy = pd.read_csv(
            self._build_fpath(country=country, year=year),
            usecols=variables if variables is not None else self.variables,
            na_values=na_values if na_values is not None else self.na_values,
            dtype=dtypes_in if dtypes_in is not None else self.dtypes_in,
        )

        # apply scaling factor to COEFF
        df_cy["COEFF"] *= self.scaling_factor_coeff

        # define filtering conditions
        cond_coeff_is_not_zero = ~np.isclose(df_cy["COEFF"], 0)
        cond_is_working = df_cy.WSTATOR.isin(["1", "2"])  # beschäftigt
        cond_private_household = df_cy.HHTYPE.isin(["1"])  # privater wohnraum
        cond_has_isco_code = df_cy.ISCO3D.notna()
        cond_not_inactive = df_cy.ILOSTAT.isin(["1", "2"])  # inaktiv
        # cond_military = ~df_cy.ISCO3D.isin(["011", "021", "031"]) # spare out military sector

        # exclude cross-border commuters
        if country == "MT":
            # special case for malta
            df_cy.COUNTRYW = df_cy.COUNTRYW.replace("000-OWN COUNTRY", "MT")
        cond_in_country = df_cy.COUNTRYW.isin([country])

        # remove obs over retirement age
        # (77 is the center of the 75-79 age band)
        cond_age = ~df_cy.AGE.isin(self.pension_age)

        # filter subset
        df_sub = df_cy.loc[
            cond_coeff_is_not_zero
            & cond_is_working
            & cond_private_household
            & cond_not_inactive
            & cond_in_country
            & cond_has_isco_code
            & cond_age
            ]

        # copy
        df_sub = df_sub.copy()

        # set NUTS code
        if country in self.countries_nuts_1d:
            # NUTS 1 only
            nuts_id = df_sub["COUNTRYW"] + df_sub["REGIONW"].str[:1]
        elif country in self.countries_nuts_0d:
            # NUTS 0 only
            nuts_id = df_sub["COUNTRYW"]
        else:
            # NUTS 2
            nuts_id = df_sub["COUNTRYW"] + df_sub["REGIONW"]

        df_sub["NUTS_ID"] = nuts_id

        # assign new ISCO column to differentiate 1D, 2D & 3D codes
        if country in self.countries_isco08_2d:
            # 2D
            if df_sub["ISCO3D"].str.endswith("0").all():
                df_sub[isco_colname_all_digits] = df_sub["ISCO3D"].str[:2]
        elif country in self.countries_isco08_1d:
            # 1D
            if df_sub["ISCO3D"].str.endswith("00").all():
                df_sub[isco_colname_all_digits] = df_sub["ISCO3D"].str[:1]
        else:
            # 3D
            df_sub[isco_colname_all_digits] = df_sub["ISCO3D"]

        # summary stats
        filtering_stats = {
            "n_obs_before": len(df_cy),
            "n_obs_after": len(df_sub),
            "ratio": len(df_sub) / len(df_cy),
        }

        if return_filtering_stats:
            return df_sub, filtering_stats
        else:
            return df_sub

    def preprocess_files(
            self,
            years=None,
            countries=None,
            variables=None,
            na_values=None,
            dtypes_in=None,
            dtypes_out=None,
            isco_colname_all_digits="ISCO",
            return_filtering_stats=True,
            save_file=True,
            optional_output_dir=None,
            output_fname="eu_lfs_merged_{year}",
            summary_stats_fname="eu_lfs_merged_{year}_summary_stats"
    ):
        """"""

        # initialise containers
        list_of_dfs = []
        summary_stats = {}

        # select variable states
        years = years if years is not None else self.years
        countries = countries if countries is not None else self.countries
        variables = variables if variables is not None else self.variables
        na_values = na_values if na_values is not None else self.na_values
        dtypes_in = dtypes_in if dtypes_in is not None else self.dtypes_in
        dtypes_out = dtypes_out if dtypes_out is not None else self.dtypes_out

        # iterate across years and countries
        for year in years:
            print(year)
            for country in countries:
                print(country)
                df_sub, filtering_stats = self.read_filtered_file(
                    country=country, year=year, variables=variables, na_values=na_values,
                    dtypes_in=dtypes_in, isco_colname_all_digits=isco_colname_all_digits,
                    return_filtering_stats=return_filtering_stats
                )

                # append clean df
                list_of_dfs.append(df_sub)

                # populate summary stats
                summary_stats["{}_{}".format(country, year)] = filtering_stats

        # Combine country-level data
        df_merged = pd.concat(list_of_dfs, axis=0).reset_index(drop=True)

        # combine summary stats
        df_summary_stats = pd.DataFrame.from_dict(summary_stats).T

        # save merged LFS data w/o additional covariates
        if save_file:
            if optional_output_dir is not None:
                output_dir = optional_output_dir
            else:
                output_dir = self.path_eulfs_interim
            utils.save_df_to_files(
                df=df_merged.astype(dtypes_out),
                output_dir=output_dir,
                fname_no_ext=output_fname.format(year=year),
            )

            utils.save_df_to_files(
                df=df_summary_stats,
                output_dir=output_dir,
                fname_no_ext=summary_stats_fname.format(year=year),
            )

        else:
            return df_merged

    def read_preprocessed_file(
            self,
            year=None,
            input_fname_lfs="eu_lfs_merged_{year}",
            optional_input_dir=None,
            ffmt="pkl"
    ):

        # select input directory
        if optional_input_dir is not None:
            input_dir = optional_input_dir
        else:
            input_dir = self.path_eulfs_interim

        # compile path
        fpath = os.path.join(
            input_dir,
            input_fname_lfs.format(year=year) + ".{}".format(ffmt),
        )

        # read depending on file type
        if ffmt == "pkl":
            df_out = pd.read_pickle(fpath)
        else:
            df_out = pd.read_csv(fpath, index_col=0)
        return df_out

    def read_merged_file(
            self,
            year=None,
            input_fname_lfs="eu_lfs_merged_{year}_with_covariates",
            optional_input_dir=None,
            ffmt="pkl"
    ):

        # select input directory
        if optional_input_dir is not None:
            input_dir = optional_input_dir
        else:
            input_dir = self.path_eulfs_interim

        # compile path
        fpath = os.path.join(
            input_dir,
            input_fname_lfs.format(year=year) + ".{}".format(ffmt),
        )

        # read depending on file type
        if ffmt == "pkl":
            df_out = pd.read_pickle(fpath)
        else:
            df_out = pd.read_csv(fpath, index_col=0)
        return df_out

    def join_covariates(
            self,
            year=None,
            optional_input_dir=None,
            input_fname_lfs="eu_lfs_merged_{year}",
            input_file_covariates_isco=os.path.join(useful_paths.data_interim, "esco",
                                               "occ_metadata_en_by_isco08.pkl"),
            input_file_covariates_nace=os.path.join(useful_paths.data_raw, "classifications",
                                               "NACE_REV2_1d_section_codes.csv"),
            isco_join_col_eulfs="ISCO",
            isco_join_col_covariates="isco_code",
            isco_covariate_selection=None,
            nace_join_col_eulfs="NACE1D",
            nace_join_col_covariates="NACE1D",
            nace_covariate_selection=None,
            multiply_by_coeff_if_starts_with="share",
            save_file=True,
            optional_output_dir=None,
            output_fname_lfs="eu_lfs_merged_{year}_with_covariates",
            dtypes_out=None
    ):
        dtypes_out = dtypes_out if dtypes_out is not None else self.dtypes_out

        # read preprocessed EU-LFS file for certain year
        df_preprocessed = self.read_preprocessed_file(
            year=year,
            input_fname_lfs=input_fname_lfs,
            optional_input_dir=optional_input_dir
        )

        # read occupation metadata aggregated at ISCO level
        covariates_by_isco = pd.read_pickle(input_file_covariates_isco)

        # optionally make selection of covariates to attach
        if isco_covariate_selection is not None:
            isco_covariate_selection.insert(0, isco_join_col_covariates)
            covariates_by_isco = covariates_by_isco[isco_covariate_selection]

        # join occupation metadata on EU-LFS ISCO codes
        df_merged = pd.merge(
            left=df_preprocessed,
            right=covariates_by_isco,
            left_on=isco_join_col_eulfs,
            right_on=isco_join_col_covariates,
            how="left",
        ).drop(columns=[isco_join_col_covariates])

        # read industry metadata aggregated at NACE level
        covariates_by_nace = pd.read_csv(input_file_covariates_nace, delimiter=";")

        # optionally make selection of covariates to attach
        if nace_covariate_selection is not None:
            nace_covariate_selection.insert(0, nace_join_col_covariates)
            covariates_by_nace = covariates_by_nace[nace_covariate_selection]

        # join industry metadata on EU-LFS NACE codes
        df_merged = pd.merge(
            left=df_merged,
            right=covariates_by_nace,
            left_on=nace_join_col_eulfs,
            right_on=nace_join_col_covariates,
            how="left",
        )

        # calc absolute employment numbers from shares
        if multiply_by_coeff_if_starts_with is not None:
            # note: column names of variables that should be multiplied with COEFF
            #  need to start with "share"
            share_cols = df_merged.columns[
                df_merged.columns.str.startswith(multiply_by_coeff_if_starts_with)
            ].values.tolist()

            for col_name in share_cols:
                col_name_new = "COEFF_{}".format(col_name)
                df_merged[col_name_new] = (
                        df_merged[col_name] * df_merged["COEFF"]
                )

        # sort cols alphabetically
        df_merged = utils.sort_columns(df_merged)

        # optionally save
        if save_file:
            if optional_output_dir is not None:
                output_dir = optional_output_dir
            else:
                output_dir = self.path_eulfs_interim
            utils.save_df_to_files(
                df=df_merged.astype(dtype=dtypes_out),
                output_dir=output_dir,
                fname_no_ext=output_fname_lfs.format(year=year),
            )

        return df_merged


class LmData(UsefulPaths):
    def __init__(self, fn_config_path, fn_config_data):
        """
        Basic class for storing Labour Market Data Classifications across 3 dimensions:
        occupations, industries and regions.

        Parameters
        ----------
        fn_config_path : str
            Name of config file storing relevant static parameters.
        fn_config_data : str
            Name of configuration file storing relevant paths.
        """
        # inherit path structure
        UsefulPaths.__init__(self=self, fn_config_path=fn_config_path)

        # read data configs
        self.config_data = utils.load_config(
            os.path.join(self.config_dir, fn_config_data)
        )

        # unpack data config
        self.n_digits_isco08 = self.config_data["lfs_eu"]["n_digits_isco08"]

        # parametrise data paths
        # TODO: make reading industry & geo-data flexible with respect to the desired
        #   granularity. Similar to ISCO data approach below.
        self.path_clsf_isco08 = self.path_clsf_isco08.format(
            self.config_data["ESCO"]["VERSION_NEWEST"]
        )
        self.path_clsf_nace = self.path_clsf_nace_1d
        self.path_geodata_nuts_3035 = self.path_geodata_nuts_3035
        self.path_geodata_nuts_4326 = self.path_geodata_nuts_4326

        # read relevant data across 3 dimensions: industry, occupation, region
        self.df_nace = self._read_nace()
        self.gdf_nuts = self._read_nuts()

    def _read_nace(self):
        return pd.read_csv(self.path_clsf_nace, delimiter=";")

    def _read_nuts(self):
        return {
            "3035": gpd.read_file(self.path_geodata_nuts_3035),
            "4326": gpd.read_file(self.path_geodata_nuts_4326),
        }


class EulfsDs(LmData, Esco):
    """EU LFS Dataset Class"""

    def __init__(self, fn_config_data, fn_config_path):
        # inheritance
        LmData.__init__(
            self=self, fn_config_data=fn_config_data, fn_config_path=fn_config_path
        )

        Esco.__init__(self=self)

        # static params
        self.fmt_folder = "{}_YEAR_1998_onwards"
        self.fmt_file = "{}{}_y.csv"
        self.fmt_file_orig_vars_out = "eu_lfs_merged_{}"
        self.fmt_file_all_vars_out = "eu_lfs_merged_{}_with_covariates"

        # read data configs
        self.config_data = utils.load_config(
            os.path.join(self.config_dir, fn_config_data)
        )

        # assign vars
        self.n_digits_isco08 = self.config_data["lfs_eu"]["n_digits_isco08"]
        self.n_digits_nace = self.config_data["lfs_eu"]["n_digits_nace"]
        self.n_digits_nuts = self.config_data["lfs_eu"]["n_digits_nuts"]

        self.years = self.config_data["lfs_eu"]["years"]
        self.countries = self.config_data["lfs_eu"]["countries"]

        # special cases
        self.countries_isco08_2d = self.config_data["lfs_eu"]["countries_isco08_2d"]
        self.countries_isco08_1d = self.config_data["lfs_eu"]["countries_isco08_1d"]
        self.countries_nuts_1d = self.config_data["lfs_eu"]["countries_nuts_1d"]
        self.countries_nuts_0d = self.config_data["lfs_eu"]["countries_nuts_0d"]

        self.scaling_factor_coeff = self.config_data["lfs_eu"]["scaling_factor_coeff"]
        self.pension_age = self.config_data["lfs_eu"]["pension_age"]

        self.variables = self.config_data["lfs_eu"]["variables"]
        self.na_values = self.config_data["lfs_eu"]["na_values"]
        self.dtypes_in = self.config_data["lfs_eu"]["dtypes_in"]
        self.dtypes_out = self.config_data["lfs_eu"]["dtypes_out"]

        # column name formatters
        self.isco_join_col_eulfs = "ISCO"
        self.nace_colname = "NACE{}D".format(self.n_digits_nace)

        # read aggregated occupation metadata
        # self.occupation_metadata_agg = self.aggregate_occ_data_by_isco()

    def preprocess(self):
        """"""
        list_of_dfs = []
        summary_stats = {}

        for year in self.years:
            print(year)
            for country in self.countries:
                # todo: remove/add [:1] above after/before testing
                print(country)
                # define fpath
                folder = self.fmt_folder.format(country)
                file = self.fmt_file.format(country, year)
                fpath_full = os.path.join(self.path_eulfs_raw_yf, folder, file)

                # read raw data
                df_cy = pd.read_csv(
                    fpath_full,
                    usecols=self.variables,
                    na_values=self.na_values,
                    # categories make more sense to deal with na values
                    dtype=self.dtypes_in,
                )

                # apply scaling factor to COEFF
                df_cy["COEFF"] *= self.scaling_factor_coeff

                # define filtering conditions
                cond_coeff_is_not_zero = ~np.isclose(df_cy["COEFF"], 0)
                cond_is_working = df_cy.WSTATOR.isin(["1", "2"])  # beschäftigt
                cond_private_household = df_cy.HHTYPE.isin(["1"])  # privater wohnraum
                cond_has_isco_code = df_cy.ISCO3D.notna()
                cond_not_inactive = df_cy.ILOSTAT.isin(["1", "2"])  # inaktiv

                # exclude cross-border commuters
                if country == "MT":
                    # special case for malta
                    df_cy.COUNTRYW = df_cy.COUNTRYW.replace("000-OWN COUNTRY", "MT")
                cond_in_country = df_cy.COUNTRYW.isin([country])

                # remove obs over retirement age
                # (77 is the center of the 75-79 age band)
                cond_age = ~df_cy.AGE.isin(self.pension_age)

                # spare out military sector
                # cond_military = ~df_cy.ISCO3D.isin(["011", "021", "031"])

                # filter subset
                df_sub = df_cy.loc[
                    cond_coeff_is_not_zero
                    & cond_is_working
                    & cond_private_household
                    & cond_not_inactive
                    & cond_in_country
                    & cond_has_isco_code
                    & cond_age
                ]

                # copy
                df_sub = df_sub.copy()

                # set NUTS code
                if country in self.countries_nuts_1d:
                    # NUTS 1 only
                    nuts_id = df_sub["COUNTRYW"] + df_sub["REGIONW"].str[:1]
                elif country in self.countries_nuts_0d:
                    # NUTS 0 only
                    nuts_id = df_sub["COUNTRYW"]
                else:
                    # NUTS 2
                    nuts_id = df_sub["COUNTRYW"] + df_sub["REGIONW"]

                df_sub["NUTS_ID"] = nuts_id

                # assign new ISCO column to differentiate 1D, 2D & 3D codes
                if country in self.countries_isco08_2d:
                    # 2D
                    if df_sub["ISCO3D"].str.endswith("0").all():
                        df_sub[self.isco_join_col_eulfs] = df_sub["ISCO3D"].str[:2]
                elif country in self.countries_isco08_1d:
                    # 1D
                    if df_sub["ISCO3D"].str.endswith("00").all():
                        df_sub[self.isco_join_col_eulfs] = df_sub["ISCO3D"].str[:1]
                else:
                    # 3D
                    df_sub[self.isco_join_col_eulfs] = df_sub["ISCO3D"]

                # append clean df
                list_of_dfs.append(df_sub)

                # populate summary stats
                summary_stats["{}_{}".format(country, year)] = {
                    "n_obs_before": len(df_cy),
                    "n_obs_after": len(df_sub),
                    "ratio": len(df_sub) / len(df_cy),
                }

        # 1) Combine country-level data
        df_merged = pd.concat(list_of_dfs, axis=0).reset_index(drop=True)

        # 2) save merged LFS data w/o additional covariates
        utils.save_df_to_files(
            df=df_merged.astype(self.dtypes_out),
            output_dir=self.path_eulfs_interim,
            fname_no_ext=self.fmt_file_orig_vars_out.format(year),
        )

        # 3) merge covariates (ESCO, ONET)

        # merge occupation metadata on ISCO code
        df_merged_all_vars = pd.merge(
            left=df_merged,
            right=self.occupation_metadata_agg,
            left_on=self.isco_join_col_eulfs,
            right_on=self.isco_join_col_of,
            how="left",
        )

        # merge NACE code names
        df_merged_all_vars = pd.merge(
            df_merged_all_vars, self.df_nace, on=self.nace_colname, how="left"
        )

        # calc absolute employment numbers from shares
        # note: column names of variables that should be multiplied with COEFF need to
        #  start with "share"
        share_cols = df_merged_all_vars.columns[
            df_merged_all_vars.columns.str.startswith("share")
        ].values.tolist()

        for col_name in share_cols:
            col_name_new = "COEFF_{}".format(col_name)
            df_merged_all_vars[col_name_new] = (
                df_merged_all_vars[col_name] * df_merged_all_vars["COEFF"]
            )

        # note: missing values remain (subsistence agriculture: 631, 632, 633)
        # 4) Save to disk
        utils.save_df_to_files(
            df=df_merged_all_vars.astype(dtype=self.dtypes_out),
            output_dir=self.path_eulfs_interim,
            fname_no_ext=self.fmt_file_all_vars_out.format(year),
        )

        # save preprocessing stats (missing obs)
        df_summary_stats = pd.DataFrame.from_dict(summary_stats).T
        df_summary_stats.to_csv(
            os.path.join(
                self.path_eulfs_interim,
                "eu_lfs_preprocessing_stats_{}.csv".format(year),
            )
        )

        # remove categories that remain unused after filtering
        # TODO: fix SettingWithCopyWarning
        # for col_name in df_merged.columns:
        #     if pd.api.types.is_categorical_dtype(df_merged[col_name]):
        #         df_merged.loc[:, col_name] = df_merged.loc[
        #             :, col_name
        #         ].cat.remove_unused_categories()

    def read(self, year=None, covariates=True, ffmt="pkl"):
        if covariates:
            fpath = os.path.join(
                self.path_eulfs_interim,
                self.fmt_file_all_vars_out.format(year) + ".{}".format(ffmt),
            )
        else:
            fpath = os.path.join(
                self.path_eulfs_interim,
                self.fmt_file_orig_vars_out.format(year) + ".{}".format(ffmt),
            )

        if ffmt == "pkl":
            df_out = pd.read_pickle(fpath)
        else:
            df_out = pd.read_csv(fpath, index_col=0)
        return df_out


if __name__ == "__main__":

    # load config file of EU-LFS data
    config = utils.load_config(os.path.join(useful_paths.config_dir, "eu_lfs_config.yml"))

    # create object
    lfs = EuLfs(config=config)

    # preprocess files
    lfs.preprocess_files(years=["2019"], countries=None, save_file=True)

    # join covariates
    lfs.join_covariates(
        year=2019,
        isco_covariate_selection=None
    )
