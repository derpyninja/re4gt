import os
import logging
import numpy as np
import pandas as pd
from tqdm import tqdm

from src import UsefulPaths, utils, stats_utils


class EscoDs(UsefulPaths):
    """ESCO Dataset Class"""

    def __init__(self, fn_config_data, fn_config_path):
        """
        Initialise ESCO class based on configuration file settings.

        Parameters
        ----------
        fn_config_data : str
            Name of yml file with ESCO-specific configurations.
        fn_config_path : str
            Name of yml file storing additional path-specific configurations.
        """
        # inherit class storing useful paths
        UsefulPaths.__init__(self=self, fn_config_path=fn_config_path)

        # parse config file
        self.config_data = utils.load_config(
            os.path.join(self.config_dir, fn_config_data)
        )

        # language and versions
        self.esco_language = self.config_data["ESCO"]["LANGUAGE"]  # "en"
        self.esco_version = self.config_data["ESCO"]["VERSION"]  # "v1.0.3" or "v1.1.0"
        self.esco_version_newest = self.config_data["ESCO"]["VERSION_NEWEST"]
        self.esco_skills_hierarchy_version = (
            "v1.0.8" if self.esco_version == "v1.0.3" else "v1.1.0"
        )

        # additional static parameters
        self.skill_types_gbn = ["green", "brown", "neutral"]
        self.skill_col_fmt = "skill_{}"
        # note: formatting string below needs to start with "share"
        self.gbn_share_fmt = "share_{type}_{ds}"

        # column names of GBN skills in ESCO
        self.green_id_colname = "skill_green"
        self.brown_id_colname = "skill_brown"
        self.neutral_id_colname = "skill_neutral"

        # column names of GBN skills in O*NET
        self.green_id_onet = "is_green_onet"
        self.brown_id_onet = "is_brown_onet"
        self.neutral_id_onet = "is_neutral_onet"

        # functions for the aggregation of occupation data
        # TODO: add agg func for discrete GBN classifications
        self.agg_func_dict = {
            "mean": np.nanmean,
            "std": np.nanstd,
            "median": np.nanmedian,
            "iqr": stats_utils.naniqr,
        }

        # initialise containers
        self.osm = None
        self.osim = None
        self.data = None

        # read data
        self.data = self._read()

        # crosswalk to onet
        self.onet_esco_crosswalk = self._read_crosswalk_to_onet()

    def _read_crosswalk_to_onet(self):
        return pd.read_csv(self.path_crosswalk_onet_esco)

    def _read(self):
        """
        Read main ESCO pillars (occupations, skills, occupation-skills mapping)
        and skills hierarchy.

        Returns
        -------
        self.esco_data : dict
            Dictionary containing pd.DataFrame's of the relevant ESCO pillars and
            metadata.
        """

        # -----------------------------------------------------------------------------
        # core
        # -----------------------------------------------------------------------------
        occ = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version,
                "occupations_{}.csv".format(self.esco_language),
            )
        )
        skills = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version,
                "skills_{}.csv".format(self.esco_language),
            )
        )
        occ_skills_mapping = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version,
                "occupationSkillRelations.csv",
            )
        )

        # -----------------------------------------------------------------------------
        # additional (ESCO)
        # -----------------------------------------------------------------------------
        # ESCO green skill labels
        green_skills = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version_newest,
                "greenSkillsCollection_{}.csv".format(self.esco_language),
            )
        )
        green_skills[self.green_id_colname] = True

        # ESCO brown skill labels
        brown_skills = pd.read_excel(
            os.path.join(
                self.data_external,
                "esco",
                self.esco_version_newest,
                "BrownSkillsKnowledge.xlsx",
            )
        )
        brown_skills[self.brown_id_colname] = True

        # ESCO skills hierarchies
        skills_hierarchy = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_skills_hierarchy_version,
                "skillsHierarchy_{}.csv".format(self.esco_language),
            )
        )

        skills_hierarchy_kanders = pd.read_csv(
            os.path.join(
                self.data_raw,
                "mapping-career-causeways",
                "codebase",
                "data",
                "processed",
                "ESCO_skills_hierarchy",
                "ESCO_skills_hierarchy.csv",
            )
        )

        # ESCO skill groups
        skill_groups = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version,
                "skillGroups_{}.csv".format(self.esco_language),
            )
        )

        # -----------------------------------------------------------------------------
        # additional (Nesta)
        # -----------------------------------------------------------------------------

        # coreness values
        skills_coreness = pd.read_csv(
            os.path.join(
                self.data_raw,
                "mapping-career-causeways",
                "codebase",
                "data",
                "interim",
                "upskilling_analysis",
                "skills_coreness_measure.csv",
            )
        )

        job_zones_onet = pd.read_csv(
            os.path.join(
                self.data_raw,
                "mapping-career-causeways",
                "codebase",
                "data",
                "processed",
                "linked_data",
                "ESCO_occupations_Job_Zones.csv",
            )
        )

        covid_exposure = pd.read_csv(
            os.path.join(
                self.data_raw,
                "mapping-career-causeways",
                "codebase",
                "data",
                "processed",
                "linked_data",
                "ESCO_occupations_COVID_Exposure.csv",
            )
        )

        return {
            "occ": occ,
            "skills": skills,
            "occ_skills_mapping": occ_skills_mapping,
            "skills_green": green_skills,
            "skills_brown": brown_skills,
            "skills_coreness": skills_coreness,
            "skills_hierarchy": skills_hierarchy,
            "skills_hierarchy_kanders": skills_hierarchy_kanders,
            "skill_groups": skill_groups,
            "job_zones_onet": job_zones_onet,
            "covid_exposure": covid_exposure,
        }

    def _calc_osm_variants(self, occ_skills_matrix_eo):
        """
        Calculate weighted and unweighted forms from raw OSM.

        Parameters
        ----------
        occ_skills_matrix_eo

        Returns
        -------

        """
        # get weights of weighted form
        replace_weighted = {
            1: self.config_data["ESCO"]["WEIGHT_ESSENTIAL_SKILL"],
            2: self.config_data["ESCO"]["WEIGHT_OPTIONAL_SKILL"],
        }

        # calc weighted form
        occ_skills_matrix_weighted = occ_skills_matrix_eo.replace(
            to_replace=replace_weighted
        )

        # calc unweighted form
        occ_skills_matrix_unweighted = occ_skills_matrix_eo.replace(
            to_replace=[1, 2], value=self.config_data["ESCO"]["WEIGHT_UNIFORM"]
        )

        return {
            "osm_weighted": occ_skills_matrix_weighted,
            "osm_unweighted": occ_skills_matrix_unweighted,
        }

    def occupation_skills_matrix(self):
        """
        Calculate occupation-skills matrix (OSM) based on ESCO data. In the OSM rows
        denote occupations and columns skills. Depending on the settings in the main
        configuration file, essential and optional skills are assigned different
        weights on an occupation-to-occupation basis. An unweighted variant is
        always also created as a baseline.

        Returns
        -------
        dict
            Dictionary storing two variants of the OSM as pd.DataFrame:
                (1) the weighted form (coded as np.float),
                (2) the unweighted/uniform form (coded as np.int8)
        """
        logger = logging.getLogger(__name__)
        logger.info("Creating occupation-skills matrix.")

        target_path = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_skills_matrix.pkl",
        )

        if not os.path.exists(target_path):
            # build occupation skills matrix
            errors = 0
            skill_vectors = []

            for i in tqdm(range(len(self.data["occ"]))):
                occ_uri = self.data["occ"].iloc[i, :][1]

                # lookup corresponding skills
                skill_list = self.data["occ_skills_mapping"][
                    self.data["occ_skills_mapping"]["occupationUri"] == occ_uri
                ]

                # create vector
                skill_vector = []
                for j, skill in enumerate(self.data["skills"].conceptUri.values):

                    if skill in skill_list.skillUri.values:
                        relation_type = skill_list.loc[
                            skill_list.skillUri == skill, "relationType"
                        ].values[0]

                        # skill needed for occupation and essential
                        if relation_type == "essential":
                            skill_vector.append(1)
                        # skill needed for occupation and optional
                        elif relation_type == "optional":
                            skill_vector.append(2)
                    else:
                        # skill not needed for occupation
                        skill_vector.append(0)

                # checkme: what is this line good for?
                indices = [i for i, j in enumerate(skill_vector) if j == 1]

                # sanity check
                if len(skill_list.skillUri) != np.sum(
                    np.invert(np.array(skill_vector) == 0)
                ):
                    errors += 1

                # append
                skill_vectors.append(skill_vector)

            # info
            print("n_errors: ", errors)

            # create df
            occ_skills_matrix_eo = pd.DataFrame(
                index=self.data["occ"].conceptUri,
                columns=self.data["skills"].conceptUri,
                data=np.array(skill_vectors),
            )

            # save to disk
            occ_skills_matrix_eo.to_pickle(target_path)
        else:
            # read matrix from disk
            occ_skills_matrix_eo = pd.read_pickle(target_path)

        return self._calc_osm_variants(occ_skills_matrix_eo=occ_skills_matrix_eo)

    def occupation_similarity_matrix(self):
        """
        Calculate weighted and unweighted forms of the co-occurrence occupation
        similarity matrix (OSIM).

        Returns
        -------
        dict
            Dictionary containing X versions of the OSIM:
                (1) Skills COO based on weighted OSM
                (2) Skills COO based on unweighted OSM
        """
        logger = logging.getLogger(__name__)

        # read base OSM and calculate variants
        osm_dict = self.occupation_skills_matrix()

        target_path_template = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_sim_matrix_{}_coo.pkl",
        )

        # calculate co-occurrence matrices for both variants
        # (via matrix multiplication with transpose form)
        osim_dict = {}
        for osm_version, osm_data in osm_dict.items():
            variant = osm_version.split("_")[1]

            # fixme: calculation of unweighted COOC matrix does not work
            if variant == "unweighted":
                continue

            logger.info("Calculating {} occupation similarity matrix.".format(variant))
            target_path = target_path_template.format(variant)

            if not os.path.exists(target_path):
                occ_sim_matrix_coo = np.dot(
                    osm_data.values, osm_data.values.transpose()
                )

                # to df
                df_occ_sim_matrix_weighted_coo = pd.DataFrame(
                    index=self.data["occ"].conceptUri,
                    columns=self.data["occ"].conceptUri,
                    data=occ_sim_matrix_coo,
                )

                # save
                df_occ_sim_matrix_weighted_coo.to_pickle(target_path)

            else:
                osim_dict["osim_{}".format(variant)] = pd.read_pickle(target_path)

        return osim_dict

    def skills_metadata(self):
        """
        Calculate and merge relevant metadata to the ESCO skills pillar (greenness,
        coreness).

        Evaluation
            - ESCO v.1.1.0 comprises 13891 skills compared to v.1.0.3 with 13485 skills.
            - Hence, overall 406 new skills in v.1.1.0 compared to v.1.0.3.
            - 570 skills labelled as green in v.1.1.0, some of which are presumably new,
            while other's already existed.
            - After merging we don't obtain coreness values for 512 skills in v.1.1.0.
            - This means that the conceptUri of 512 - 406 = 106 skills that existed in
            the last version must have changed.

        Returns
        -------
        skills_metadata : pd.DataFrame
            DataFrame containing the raw ESCO skills pillar data enriched by additional
            metadata (green labels, coreness).
        """
        logger = logging.getLogger(__name__)
        logger.info(
            "Calculating & merging ESCO occupation metadata (green labels, coreness)."
        )

        # output fpath
        target_path = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "skills_metadata_{}.csv".format(self.esco_language),
        )

        if not os.path.exists(target_path):
            # -------------------------------------------------------------------------
            # Green Skills
            # -------------------------------------------------------------------------
            # TODO: refactor to static function
            # Find cols that are unique in green skills file compared to general
            # skills file: "The difference between A and B contains all elements that
            # are in A but not in B."
            # Source: https://www.kaggle.com/ashukr/sets-and-venn-diagram-in-python
            set_diff = list(
                set(self.data["skills_green"].columns.values.tolist())
                - set(self.data["skills"].columns.values.tolist())
            )
            set_diff.insert(0, "conceptUri")

            # copy skills df and join information on green skills
            skills_metadata = self.data["skills"].copy()
            skills_metadata = skills_metadata.merge(
                right=self.data["skills_green"][set_diff],
                on="conceptUri",
                how="left",
                validate="one_to_one",
            )
            skills_metadata = skills_metadata.fillna(
                value={self.green_id_colname: False}
            )

            # -------------------------------------------------------------------------
            # Brown Skills
            # -------------------------------------------------------------------------
            # TODO: refactor to static function
            set_diff = list(
                set(self.data["skills_brown"].columns.values.tolist())
                - set(self.data["skills"].columns.values.tolist())
            )
            set_diff.insert(0, "conceptUri")

            skills_metadata = skills_metadata.merge(
                right=self.data["skills_brown"][set_diff],
                on="conceptUri",
                how="left",
                validate="one_to_one",
            )
            skills_metadata = skills_metadata.fillna(
                value={self.brown_id_colname: False}
            )

            # -------------------------------------------------------------------------
            # Derive Neutral Skills
            # -------------------------------------------------------------------------
            # TODO: refactor to class function
            skills_metadata[self.neutral_id_colname] = (
                skills_metadata[self.green_id_colname] == False
            ) & (skills_metadata[self.brown_id_colname] == False)

            # sanity check
            ambiguous_cases = (skills_metadata[self.brown_id_colname] == True) & (
                skills_metadata[self.green_id_colname] == True
            )
            assert ambiguous_cases.sum() == 0

            # create skill classification column: green/brown/neutral
            skills_metadata["skillClassification"] = skills_metadata[
                [self.green_id_colname, self.brown_id_colname, self.neutral_id_colname]
            ].idxmax(axis=1)

            skills_metadata["skillClassification"] = (
                skills_metadata["skillClassification"]
                .str.split(pat="_", expand=True)
                .iloc[:, 1]
            )

            # -------------------------------------------------------------------------
            # Coreness Metric
            # -------------------------------------------------------------------------
            # append conceptUri of ESCO v1.0.3 skills
            skills_v103 = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    "v1.0.3",
                    "skills_{}.csv".format(self.config_data["ESCO"]["LANGUAGE"]),
                )
            )
            keep_cols = ["conceptUri", "preferredLabel"]
            skills_coreness_with_uri = self.data["skills_coreness"].merge(
                right=skills_v103[keep_cols],
                left_on="preferred_label",
                right_on="preferredLabel",
                how="left",
                validate="one_to_one",
            )

            # Merge Green Labels and Coreness to Skills Pillar
            keep_cols = ["conceptUri", "coreness"]
            skills_metadata = skills_metadata.merge(
                right=skills_coreness_with_uri[keep_cols],
                on="conceptUri",
                how="left",
                validate="one_to_one",
            )

            # note: this dataset refers to variable "greenskill"
            #  in the FDZ Verfahrensbeschreibung
            # save
            self.data["skills_metadata"] = skills_metadata
            skills_metadata.to_csv(target_path)

        else:
            skills_metadata = pd.read_csv(target_path, index_col=0)
            self.data["skills_metadata"] = skills_metadata
        return skills_metadata

    # todo: implement weighted form of esco-based greenness measure
    def calc_gbn_shares_skill_based(self, weighted=False):
        # read
        osm = self.occupation_skills_matrix()
        occ_skills_matrix_unweighted = osm["osm_unweighted"]
        self.skills_metadata()

        # number of occupation-specific skills
        n_total_specific_skills = occ_skills_matrix_unweighted.sum(axis=1).values

        data_out = {
            "n_total_specific_skills": n_total_specific_skills,
        }

        # calc occupational shares for each skill type
        colnames = []
        for skill_type in self.skill_types_gbn:
            col = self.skill_col_fmt.format(skill_type)
            colname_shares = self.gbn_share_fmt.format(type=skill_type, ds="esco")

            # number of occupation-specific green/brown/neutral skills
            specific_skills = (
                occ_skills_matrix_unweighted.values
                * self.data["skills_metadata"][col].astype(np.int8).values
            )

            n_partial_specific_skills = specific_skills.sum(axis=1)

            # occupational share
            occ_share = n_partial_specific_skills / n_total_specific_skills

            # append to dict
            data_out[
                "n_{}_specific_skills".format(skill_type)
            ] = n_partial_specific_skills
            data_out[colname_shares] = occ_share
            colnames.append(colname_shares)

        df_occ_shares_per_skill_type = pd.DataFrame(
            index=occ_skills_matrix_unweighted.index, data=data_out
        )

        # check if shares sum to 100%
        assert np.allclose(df_occ_shares_per_skill_type[colnames].sum(axis=1).values, 1)

        # classify into discrete GBN categories
        # TODO: check if only one True per col.
        # TODO: rename to green/brown/neutral.
        df_occ_shares_per_skill_type[
            "gbn_classification_esco"
        ] = df_occ_shares_per_skill_type[colnames].idxmax(axis=1)

        # rename to green/brown/neutral.
        df_occ_shares_per_skill_type["gbn_classification_esco"] = (
            df_occ_shares_per_skill_type["gbn_classification_esco"]
            .str.split(pat="_", expand=True)
            .iloc[:, 1]
        )

        return df_occ_shares_per_skill_type.reset_index()

    def read_greenness_task_based(self):
        greenness_onet_gtp = pd.read_excel(
            io=os.path.join(
                self.data_raw,
                "onet",
                "green_task_project",
                "Onet_GreenTask_AppA.xlsx",
            ),
            sheet_name="Occupations",
        )

        greenness_onet_vona = pd.read_excel(
            io=os.path.join(
                self.data_raw, "onet", "vona_2018", "vona_2018_table_a1.xlsx"
            ),
            sheet_name="Greenness",
        )

        # merge GTP and Vona variants
        greenness_onet = greenness_onet_gtp.copy()
        greenness_onet = greenness_onet.merge(
            right=greenness_onet_vona,
            on="onet_code",
            how="left",
            validate="1:1",
            suffixes=["_gtp", "_vona2018"],
        )

        # merge to ESCO occupations pillar via crosswalk
        greenness_onet_esco = greenness_onet.copy()
        greenness_onet_esco = greenness_onet_esco.merge(
            right=self.onet_esco_crosswalk,
            on="onet_code",
            how="left",
            validate="1:m",
        )

        # save
        greenness_onet.to_csv(
            os.path.join(self.data_interim, "onet", "task_based_greenness_onet.csv")
        )

        greenness_onet_esco.to_csv(
            os.path.join(
                self.data_interim,
                "onet",
                "task_based_greenness_onet_esco_{}.csv".format(
                    self.esco_version.replace(".", "")
                ),
            )
        )

        return greenness_onet_esco

    def _read_brown_occupations_vona2018(self):
        brown_occs_vona2018 = pd.read_csv(
            os.path.join(
                self.data_raw, "onet", "vona_2018", "brown_occupations_vona2018.csv"
            )
        )

        # pad to 8 digits
        brown_occs_vona2018["soc_code"] = brown_occs_vona2018["soc_code"] + ".00"

        # add brown occupation classification
        brown_occs_vona2018[self.brown_id_onet] = np.ones(
            brown_occs_vona2018.shape[0], dtype=bool
        )

        # merge to ESCO occupations pillar via crosswalk
        brown_occs_vona2018_esco = brown_occs_vona2018.merge(
            right=self.onet_esco_crosswalk,
            left_on="soc_code",
            right_on="onet_code",
            how="left",
            # validate="1:1",
        )

        # save
        brown_occs_vona2018_esco.to_csv(
            os.path.join(
                self.data_interim,
                "onet",
                "brown_occupations_vona2018_esco_{}.csv".format(
                    self.esco_version.replace(".", "")
                ),
            )
        )

        return brown_occs_vona2018_esco

    # TODO: refactor code from other functions
    def classify_occupations_gbn(self):
        pass

    def merged_occupation_metadata(self):
        """

        Returns
        -------

        """
        target_fpath_csv = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_metadata_{}.csv".format(self.esco_language),
        )

        target_fpath_pkl = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_metadata_{}.pkl".format(self.esco_language),
        )

        if not os.path.exists(target_fpath_pkl):
            # init container
            occ_metadata = self.data["occ"].copy()

            # decompose isco 4-digit level
            occ_metadata["isco_level_4"] = (
                occ_metadata["iscoGroup"]
                .astype(str)
                .str.pad(width=4, side="left", fillchar="0")
            )
            for lvl in [1, 2, 3]:
                new_colname = "isco_level_{}".format(lvl)
                occ_metadata[new_colname] = occ_metadata["isco_level_4"].str[0:lvl]

            # merge onet codes and names via crosswalk
            occ_metadata = occ_metadata.merge(
                right=self.onet_esco_crosswalk,
                left_on="conceptUri",
                right_on="concept_uri",
                how="left",
                suffixes=["", "_y"],
                validate="1:1",
            )

            # Read data sets
            df_gbn_shares_esco = self.calc_gbn_shares_skill_based()
            df_greenness_onet_esco = self.read_greenness_task_based()
            df_brown_occs_vona2018_esco = self._read_brown_occupations_vona2018()
            # TODO: join --> ONET job zone, COVID Exposure

            # merge variables to occupation df

            # ESCO-based
            occ_metadata = occ_metadata.merge(
                right=df_gbn_shares_esco,
                on="conceptUri",
                how="left",
                suffixes=["", "_y"],
                validate="1:1",
            )

            # O*NET-based
            occ_metadata = occ_metadata.merge(
                right=df_greenness_onet_esco,
                left_on="conceptUri",
                right_on="concept_uri",
                how="left",
                suffixes=["", "_y"],
                validate="1:m",
            )

            occ_metadata = occ_metadata.merge(
                right=df_brown_occs_vona2018_esco,
                left_on="conceptUri",
                right_on="concept_uri",
                how="left",
                suffixes=["", "_y"],
                validate="1:m",
            )

            # ONET-based G/B/N classification

            # TODO: refactor to function
            # classify green  & neutral occupations (data from GTP covers more
            # occupations, therefore using those. correlation with Vona 2018
            # greenness scores ~ 1)
            occ_metadata[self.green_id_onet] = (
                occ_metadata[self.gbn_share_fmt.format(type="green", ds="gtp")] > 0
            )
            occ_metadata[self.brown_id_onet] = occ_metadata[self.brown_id_onet].fillna(
                False
            )

            occ_metadata[self.neutral_id_onet] = (
                occ_metadata[self.green_id_onet] == False
            ) & (occ_metadata[self.brown_id_onet] == False)

            # there are 30 occupations that have been matched to both brown and green
            query_ambiguous_cases = (occ_metadata[self.brown_id_onet] == True) & (
                occ_metadata[self.green_id_onet] == True
            )

            # define ambiguous cases as brown (see thesis)
            occ_metadata.loc[query_ambiguous_cases, self.green_id_onet] = False
            # occ_metadata = occ_metadata.reset_index(drop=True)

            # create single classification column
            # TODO: assert check if only one True per col.
            occ_metadata["gbn_classification_onet"] = occ_metadata[
                [self.brown_id_onet, self.green_id_onet, self.neutral_id_onet]
            ].idxmax(axis=1)

            # rename to green/brown/neutral.
            occ_metadata["gbn_classification_onet"] = (
                occ_metadata["gbn_classification_onet"]
                .str.split(pat="_", expand=True)
                .iloc[:, 1]
            )

            # filter out duplicate columns
            occ_metadata = occ_metadata.drop(
                occ_metadata.filter(regex="_y$").columns.tolist(), axis=1
            )

            # check if all occs are classified
            assert occ_metadata["gbn_classification_onet"].isna().sum() == 0

            # note: comment line below for testing
            self.data["occ_metadata"] = occ_metadata
            occ_metadata.to_csv(target_fpath_csv)
            occ_metadata.to_pickle(target_fpath_pkl)
        else:
            occ_metadata = pd.read_pickle(target_fpath_pkl)
            self.data["occ_metadata"] = occ_metadata
        return occ_metadata

    # todo (minor): add COVID and automation-related data to agg process
    def aggregate_occ_data_by_isco(
        self,
        isco08_digits=[1, 2, 3, 4],
        use_weights=False,
    ):
        occ = self.merged_occupation_metadata().copy()
        occ["n_occ_esco"] = np.ones(len(occ))

        # one csv per isco level
        target_fpath_csv = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_metadata_{esco_lang}_by_isco08.csv".format(
                esco_lang=self.esco_language
            ),
        )

        # dict storing data across all agg levels
        target_fpath_pkl = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_metadata_{esco_lang}_by_isco08.pkl".format(
                esco_lang=self.esco_language
            ),
        )

        # TODO: add ONET-based GBN data
        agg_funcs = list(self.agg_func_dict.values())
        agg_dict = {
            "share_green_gtp": agg_funcs,
            "n_occ_esco": np.sum,
        }
        for skill_type in self.skill_types_gbn:
            agg_dict[self.gbn_share_fmt.format(type=skill_type, ds="esco")] = agg_funcs

        list_of_occ_data = []
        for n_digits in isco08_digits:
            group_var = "isco_level_{}".format(n_digits)

            # aggregate
            if not use_weights:
                occ_grouped = occ.groupby(group_var).agg(agg_dict)
            else:
                raise NotImplementedError("TODO: implement weighted aggregation")

            # rename cols
            occ_grouped.columns = [
                "_".join(col).replace("nan", "") for col in occ_grouped.columns
            ]

            # reset index
            occ_grouped = occ_grouped.reset_index()

            # fill nans in GTP columns with zeros
            gtp_cols = occ_grouped.columns[
                occ_grouped.columns.str.startswith("share_green_gtp")
            ]
            occ_grouped[gtp_cols] = occ_grouped[gtp_cols].fillna(0)

            # rename
            occ_grouped["ISCO"] = occ_grouped[group_var]
            # occ_grouped = occ_grouped.rename(columns={group_var: "ISCO"})

            # append to dict
            list_of_occ_data.append(occ_grouped)

        df_out = pd.concat(list_of_occ_data, axis=0).reset_index(drop=True)

        df_out.to_csv(target_fpath_csv)
        df_out.to_pickle(target_fpath_pkl)
        # if not os.path.exists(target_fpath_pkl):
        #     pd.to_pickle(obj=df_out, filepath_or_buffer=target_fpath_pkl)
        # else:
        #     df_out = pd.read_pickle(target_fpath_pkl)

        return df_out


if __name__ == "__main__":
    # CONFIGS
    config_paths = "paths_config.yml"
    config_data = "data_config.yml"
    config_model = "model_config.yml"
    config_vis = "vis_config.yml"

    # ESCO
    esco = EscoDs(
        fn_config_path=config_paths,
        fn_config_data=config_data,
    )

    # esco.occupation_skills_matrix()
    # esco.occupation_similarity_matrix()
    esco.skills_metadata()
    # esco.merged_occupation_metadata()
    # esco.aggregate_occ_data_by_isco()
