import os
import numpy as np
import pandas as pd
import geopandas as gpd

from src import UsefulPaths, utils
from src.data.esco import EscoDs


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
        UsefulPaths.__init__(self=self, config_fname=fn_config_path)

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
        self.df_isco08 = self._read_isco08()
        self.df_nace = self._read_nace()
        self.gdf_nuts = self._read_nuts()

    # TODO (low priority): implement reading 1D ISCO classification
    def _read_isco08(self):
        """
        Read ISCO-08 occupation data. Granularity depends on the data configuration
        file parameter "n_digits_isco08".

        Returns
        -------
        df_isco : pd.DataFrame
            Mapping of ISCO-08 codes and labels at the desired granularity.
        """
        # read original data from ESCO
        fpath = self.path_clsf_isco08.format(self.config_data["ESCO"]["VERSION_NEWEST"])
        df_isco = pd.read_csv(
            fpath,
            usecols=["code", "preferredLabel"],
        )

        # subset depending on desired granularity
        df_isco = df_isco.loc[
            df_isco.code.astype(str).str.len() <= self.n_digits_isco08
        ].reset_index(drop=True)

        # format and pad
        df_isco.code = df_isco.code.astype(int)
        # df_isco.code = df_isco.code.str.pad(
        #     width=self.n_digits_isco08, side="left", fillchar="0"
        # )

        # rename
        df_isco = df_isco.rename(
            columns={
                "code": "ISCO{}D".format(self.n_digits_isco08),
                "preferredLabel": "ISCO{}D_label".format(self.n_digits_isco08),
            }
        )
        return df_isco

    def _read_nace(self):
        return pd.read_csv(self.path_clsf_nace, delimiter=";")

    def _read_nuts(self):
        return {
            "3035": gpd.read_file(self.path_geodata_nuts_3035),
            "4326": gpd.read_file(self.path_geodata_nuts_4326),
        }


class EulfsDs(LmData, EscoDs):
    """EU LFS Dataset Class"""

    def __init__(self, fn_config_data, fn_config_path):
        # inheritance
        LmData.__init__(
            self=self, fn_config_data=fn_config_data, fn_config_path=fn_config_path
        )

        EscoDs.__init__(
            self=self, fn_config_data=fn_config_data, fn_config_path=fn_config_path
        )

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

        # TODO: implement multiple years
        self.years = self.config_data["lfs_eu"]["years"]
        self.countries = self.config_data["lfs_eu"]["countries"]
        self.variables = self.config_data["lfs_eu"]["variables"]
        self.na_values = self.config_data["lfs_eu"]["na_values"]
        self.dtypes = self.config_data["lfs_eu"]["dtypes"]

        # column name formatters
        self.isco08_colname_other = "isco_level_{}".format(self.n_digits_isco08)
        self.isco08_colname_eulfs = "ISCO{}D".format(self.n_digits_isco08)
        self.nace_colname = "NACE{}D".format(self.n_digits_nace)

        # read occupation metadata
        self.occupation_metadata = self.merge_occupation_metadata()
        self.occupation_metadata_agg = self.aggregate_occ_data_by_isco()
        self.occupation_metadata_agg_subset = self.occupation_metadata_agg[
            self.isco08_colname_other
        ]

    def preprocess(self):
        """"""
        list_of_dfs = []

        for year in self.years:
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
                    dtype=self.dtypes,
                    converters={
                        "COEFF": lambda x: float(x) * 1000 if x != "" else np.nan
                    },
                )

                # define filtering conditions
                cond_is_working = df_cy.WSTATOR.isin(["1", "2"])  # beschäftigt
                cond_private_household = df_cy.HHTYPE.isin(["1"])  # privater wohnraum
                cond_has_isco_code = df_cy.ISCO3D.notna()
                cond_not_inactive = df_cy.ILOSTAT.isin(["1", "2"])  # inaktiv
                cond_in_country = df_cy.COUNTRYW.isin([country])  # pendler
                cond_valid_region = df_cy.REGIONW != "00"
                cond_age = df_cy.AGE <= 77  # (77 is the center of the 75-79 age band)
                cond_military = ~df_cy.ISCO3D.isin(["011"])  # military

                # filter subset
                df_sub = df_cy.loc[
                    cond_is_working
                    & cond_private_household
                    & cond_not_inactive
                    & cond_in_country
                    & cond_valid_region
                    & cond_has_isco_code
                    & cond_military
                    & cond_age
                ]

                # remove categories that remain unused after filtering
                # TODO: fix SettingWithCopyWarning
                for col_name in df_sub.columns:
                    if pd.api.types.is_categorical_dtype(df_sub[col_name]):
                        df_sub.loc[:, col_name] = df_sub.loc[
                            :, col_name
                        ].cat.remove_unused_categories()

                # set NUTS code
                df_sub.loc[:, "NUTS_ID"] = df_sub.loc[:, "COUNTRYW"].astype(
                    str
                ) + df_sub.loc[:, "REGIONW"].astype(str)

                # append clean df
                list_of_dfs.append(df_sub)

        # Combine country-level data
        # note: merging/concatenating does not preserve categorical dtypes
        df_merged = pd.concat(list_of_dfs, axis=0).reset_index(drop=True)
        df_merged = df_merged.astype(self.dtypes)

        # save merged LFS data w/o additional covariates
        utils.save_df_to_files(
            df=df_merged,
            output_dir=self.path_eulfs_interim,
            fname_no_ext=self.fmt_file_orig_vars_out.format(year),
        )

        # merge covariates (ESCO, ONET)
        # note: temporary trick to make merging work.
        # todo: figure out role of dtypes in merging
        df_merged[self.isco08_colname_eulfs] = df_merged[
            self.isco08_colname_eulfs
        ].astype(int)

        # merge occupation metadata on ISCO code
        df_merged_all_vars = pd.merge(
            df_merged,
            self.occupation_metadata_agg_subset,
            left_on=self.isco08_colname_eulfs,
            right_on=self.isco08_colname_other,
            how="left",
        )

        # merge NACE code names
        df_merged_all_vars = pd.merge(
            df_merged_all_vars, self.df_nace, on=self.nace_colname, how="left"
        )

        # merge ISCO code names
        df_merged_all_vars = pd.merge(
            df_merged_all_vars, self.df_isco08, on=self.isco08_colname_eulfs, how="left"
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

        # Save to disk
        utils.save_df_to_files(
            df=df_merged_all_vars,
            output_dir=self.path_eulfs_interim,
            fname_no_ext=self.fmt_file_all_vars_out.format(year),
        )

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
    config_paths = "paths_config.yml"
    config_data = "data_config.yml"

    lm_data = EulfsDs(fn_config_path=config_paths, fn_config_data=config_data)
    df = lm_data.occupation_metadata_agg
    print(df["isco_level_3"].info())

    # esco = EscoDs(fn_config_path=config_paths, fn_config_data=config_data)
    # esco.aggregate_occ_data_by_isco()

    # class_vars = vars(lm_data)
    # for key, val in class_vars.items():
    #     print(key, val)
