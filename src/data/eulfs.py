import os
import numpy as np
import pandas as pd

from src import utils
from src import UsefulPaths


class EulfsDs(UsefulPaths):
    """EU LFS Dataset Class"""

    def __init__(self, fn_config_data, fn_config_path):
        # inherit
        UsefulPaths.__init__(self=self, config_fname=fn_config_path)

        # static params
        self.fmt_folder = "{}_YEAR_1998_onwards"
        self.fmt_file = "{}{}_y.csv"
        self.fmt_file_out = "lfs_eu_merged_{}.csv"

        # read data configs
        self.config_data = utils.load_config(
            os.path.join(self.config_dir, fn_config_data)
        )

        # assign vars
        # TODO: implement multiple years
        self.years = self.config_data["lfs_eu"]["years"]
        self.countries = self.config_data["lfs_eu"]["countries"]
        self.variables = self.config_data["lfs_eu"]["variables"]
        self.na_values = self.config_data["lfs_eu"]["na_values"]
        self.dtypes = self.config_data["lfs_eu"]["dtypes"]

        utils.print_dict(self.config_data)

    def preprocess(self):
        """"""
        list_of_dfs = []

        for year in self.years:
            for country in self.countries:

                # define fpath
                folder = self.fmt_folder.format(country)
                file = self.fmt_file.format(country, year)
                fpath_full = os.path.join(self.path_eulfs_raw_yf, folder, file)

                # read raw data
                df = pd.read_csv(
                    fpath_full,
                    usecols=self.variables,
                    na_values=self.na_values,
                    dtype=self.dtypes,
                    converters={
                        "COEFF": lambda x: float(x) * 1000
                        if x != ""
                        else np.nan
                    },
                )

                # filter based on conditions
                cond_is_working = df.WSTATOR.isin(["1", "2"])  # beschäftigt
                cond_private_household = df.HHTYPE.isin(
                    ["1"]
                )  # privater wohnraum
                cond_has_isco_code = df.ISCO3D.notna()
                cond_not_inactive = df.ILOSTAT.isin(["1", "2"])  # inaktiv
                cond_in_country = df.COUNTRYW.isin([country])  # pendler
                cond_valid_region = df.REGIONW != "00"
                cond_age = (
                    df.AGE <= 77
                )  # (77 is the center of the 75-79 age band)
                cond_military = ~df.ISCO3D.isin(["011"])  # military

                df_sub = df.loc[
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
                for col in df_sub.columns:
                    if pd.api.types.is_categorical_dtype(df_sub[col]):
                        df_sub.loc[:, col] = df_sub[
                            col
                        ].cat.remove_unused_categories()

                # set NUTS code
                df_sub["NUTS_ID"] = df_sub["COUNTRYW"].astype(str) + df_sub[
                    "REGIONW"
                ].astype(str)

                # append clean df
                list_of_dfs.append(df_sub)

        # Combine country-level data
        df_merged = pd.concat(list_of_dfs, axis=0).reset_index(drop=True)
        df_merged = df_merged.astype(self.dtypes)

        # Save to disk
        # TODO: fix sluggish code regarding year formatting
        df_merged.to_csv(
            os.path.join(
                self.path_eulfs_interim, self.fmt_file_out.format(year)
            )
        )


if __name__ == "__main__":
    lfs = EulfsDs(
        fn_config_data="data_config.yml", fn_config_path="paths_config.yml"
    )
    lfs.preprocess()
