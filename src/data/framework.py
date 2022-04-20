import os
import logging
import numpy as np
import pandas as pd
from tqdm import tqdm

from src import UsefulPaths, utils, stats_utils


class OccFramework(UsefulPaths):
    """
    Implements an occupational framework rooted in the European ESCO classification
    and augmented by the US O*NET.
    """

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

        # -----------------------------------------------------------------------------
        # parse config file
        # -----------------------------------------------------------------------------
        self.config_data = utils.load_config(
            os.path.join(self.config_dir, fn_config_data)
        )

        # extract language and versions
        self.esco_language = self.config_data["ESCO"]["LANGUAGE"]  # "en"
        self.esco_version = self.config_data["ESCO"]["VERSION"]  # "v1.0.3" or "v1.1.0"
        self.esco_version_newest = self.config_data["ESCO"]["VERSION_NEWEST"]
        self.esco_skills_hierarchy_version = (
            "v1.0.8" if self.esco_version == "v1.0.3" else "v1.1.0"
        )
        # -----------------------------------------------------------------------------
        # static parameters for GBN skill and occupation classifications
        # -----------------------------------------------------------------------------
        self.skill_types_gbn = ["green", "brown", "neutral"]
        self.skill_clsf_ds = ["esco", "eth"]
        self.skill_col_fmt = "skill_{type}_{ds}"

        # note: formatting string below needs to start with "share"
        self.gbn_share_fmt = "share_{type}_{ds}"

        # column names of unvalidated GBN skills in ESCO
        self.green_id_colname_esco = "skill_green_esco"
        self.brown_id_colname_esco = "skill_brown_esco"
        self.neutral_id_colname_esco = "skill_neutral_esco"

        # column names of ETH-validated GBN skills in ESCO
        self.green_id_colname_eth = "skill_green_eth"
        self.brown_id_colname_eth = "skill_brown_eth"
        self.neutral_id_colname_eth = "skill_neutral_eth"

        # column names of merged classification columns
        self.skills_clsf_colname_esco = "skill_classification_esco"
        self.skills_clsf_colname_eth = "skill_classification_eth"

        # column names of GBN occupations in O*NET
        self.green_id_onet = "is_green_onet"
        self.brown_id_onet = "is_brown_onet"
        self.neutral_id_onet = "is_neutral_onet"

        # define fmt strings for ISCO classification
        self.fmt_string_isco_lvl = "isco_level_{}"
        self.fmt_string_isco_label = "isco_label_{}"
        self.isco_join_col_of = "isco_code"

        # -----------------------------------------------------------------------------
        # functions for the aggregation of occupation data
        # -----------------------------------------------------------------------------
        # TODO: add agg func for discrete GBN classifications
        self.agg_func_dict = {
            "mean": np.nanmean,
            # "std": np.nanstd,
            # "median": np.nanmedian,
            # "iqr": stats_utils.naniqr,
        }
        # -----------------------------------------------------------------------------
        # initialise class variables, to be assigned later
        # -----------------------------------------------------------------------------
        self.osm = None
        self.osim = None

        # ESCO Core Data
        self._occupations = None
        self._occupations_to_skills = None
        self._skills = None
        self._skills_v103 = None
        self._skills_green = None
        self._skills_brown = None
        self._skills_hierarchy = None
        self._skills_groups = None
        self._isco_groups = None

        # Mapping Career Causeways
        self._skills_hierarchy_mcc = None
        self._skills_coreness_mcc = None
        self._job_zones_mcc = None
        self._covid_exposure_mcc = None

        # MCC crosswalks to onet
        self._crosswalk_onet_esco_mcc_full = None
        self._crosswalk_onet_esco_mcc_reduced = None

        # ONET-specific data
        self._green_occupations_onet = None
        self._brown_occupations_onet = None

        # merged data
        self.skills_metadata = None
        self.occupation_metadata = None

    @property
    def occupations(self):
        """
        ESCO occupations pillar.

        Returns
        -------

        """
        if self._occupations is None:
            self._occupations = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    self.esco_version,
                    "occupations_{}.csv".format(self.esco_language),
                ),
                dtype={"iscoGroup": "str"}
            )
        return self._occupations

    @property
    def skills(self):
        """
        ESCO skills, knowledge & competences pillar.

        Returns
        -------

        """
        if self._skills is None:
            self._skills = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    self.esco_version,
                    "skills_{}.csv".format(self.esco_language),
                )
            )
        return self._skills

    @property
    def skills_v103(self):
        """
        ESCO skills, knowledge & competences pillar from v.1.0.3. Needed for joining
        skills coreness data from MCC project.

        Returns
        -------

        """
        if self._skills_v103 is None:
            self._skills_v103 = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    "v1.0.3",
                    "skills_{}.csv".format(self.esco_language),
                )
            )
        return self._skills_v103

    @property
    def occupations_to_skills(self):
        """
        Mapping between ESCO occupations and skills.

        Returns
        -------

        """
        if self._occupations_to_skills is None:
            self._occupations_to_skills = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    self.esco_version,
                    "occupationSkillRelations.csv",
                )
            )
        return self._occupations_to_skills

    @property
    def skills_green(self):
        """
        ESCO green skill labels

        Returns
        -------

        """
        if self._skills_green is None:
            self._skills_green = pd.read_excel(
                os.path.join(
                    self.data_external,
                    "esco",
                    self.esco_version_newest,
                    "GreenBrownSkillsValidationETH.xlsx",
                ),
                sheet_name="greenSkillsCollection_en",
            )
        return self._skills_green

    @property
    def skills_brown(self):
        """
        ESCO brown skill labels

        Returns
        -------

        """
        if self._skills_brown is None:
            self._skills_brown = pd.read_excel(
                os.path.join(
                    self.data_external,
                    "esco",
                    self.esco_version_newest,
                    "GreenBrownSkillsValidationETH.xlsx",
                ),
                sheet_name="brownSkillsCollection_en",
            )
        return self._skills_brown

    @property
    def skills_hierarchy(self):
        """
        ESCO skills hierarchy

        Returns
        -------

        """
        if self._skills_hierarchy is None:
            self._skills_hierarchy = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    self.esco_skills_hierarchy_version,
                    "skillsHierarchy_{}.csv".format(self.esco_language),
                )
            )
        return self._skills_hierarchy

    @property
    def skills_groups(self):
        if self._skills_groups is None:
            self._skills_groups = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    self.esco_version,
                    "skillGroups_{}.csv".format(self.esco_language),
                )
            )
        return self._skills_groups

    @property
    def isco_groups(self):
        if self._isco_groups is None:
            self._isco_groups = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    self.esco_version,
                    "ISCOGroups_{}.csv".format(self.esco_language),
                ),
                dtype={"code": "str"}
            )
        return self._isco_groups

    @property
    def skills_hierarchy_mcc(self):
        if self._skills_hierarchy_mcc is None:
            self._skills_hierarchy_mcc = pd.read_csv(
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
        return self._skills_hierarchy_mcc

    @property
    def skills_coreness_mcc(self):
        """
        Skills coreness for ESCO v.1.0.3. A composite measure for the centrality of a
        skill in the overall ESCO skill network.

        Returns
        -------

        """
        if self._skills_coreness_mcc is None:
            self._skills_coreness_mcc = pd.read_csv(
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
        return self._skills_coreness_mcc

    @property
    def job_zones_mcc(self):
        """
        O*NET job zone mapped to ESCO v.1.0.3. Comprises a worker's education level,
        related work experience and on-the-job training.

        Returns
        -------

        """
        if self._job_zones_mcc is None:
            self._job_zones_mcc = pd.read_csv(
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
        return self._job_zones_mcc

    @property
    def covid_exposure_mcc(self):
        if self._covid_exposure_mcc is None:
            self._covid_exposure_mcc = pd.read_csv(
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
        return self._covid_exposure_mcc

    @property
    def crosswalk_onet_esco_mcc_full(self):
        """
        ONET-ESCO crosswalk for the full set of ESCO v.1.0.3 occupations (n=2941).

        Returns
        -------

        """
        if self._crosswalk_onet_esco_mcc_full is None:
            self._crosswalk_onet_esco_mcc_full = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "mapping-career-causeways",
                    "codebase",
                    "data",
                    "processed",
                    "ESCO_ONET_xwalk_full.csv",
                )
            )
        return self._crosswalk_onet_esco_mcc_full

    @property
    def crosswalk_onet_esco_mcc_reduced(self):
        pass

    """

    # ONET-specific data
    self._green_occupations_onet = None
    self._brown_occupations_onet = None
    """

    def occupations_to_skills_md(self):
        """Enrich occupation-skills mapping with additional metadata."""
        cols_to_use = self.skills_metadata.columns.difference(
            self.occupations_to_skills.columns)

        # join select skills metadata to mapping
        keep_cols_skills_md = [
            'conceptUri', 'reuseLevel',
            'preferredLabel', 'description', 'skill_classification_esco', 'coreness'
        ]
        join_col_right = "conceptUri"
        occ_skills_mapping_smd_merged = pd.merge(
            left=self.occupations_to_skills,
            right=self.skills_metadata[keep_cols_skills_md],
            left_on="skillUri",
            right_on=join_col_right,
            how="left",
        ).drop(columns=[join_col_right])

        # join select occ metadata to mapping
        occupations = self.occupations.reset_index().rename(columns={"index": "id"})

        keep_cols_occ_md = [
            'id', 'conceptUri', 'iscoGroup', 'preferredLabel', 'description'
        ]

        occ_skills_mapping_all_merged = pd.merge(
            left=occ_skills_mapping_smd_merged,
            right=occupations[keep_cols_occ_md],
            left_on="occupationUri",
            right_on=join_col_right,
            how="left",
            suffixes=("_skills", "_occs")
        ).drop(columns=[join_col_right])

        return occ_skills_mapping_all_merged

    def get_skills_for_occ(self, id=None, metadata=True, summary_only=True):
        if metadata:
            df_all = self.occupations_to_skills_md()
        else:
            raise NotImplementedError

        # subset based on occupation id or label
        if isinstance(id, str):
            search_col = "preferredLabel_occs"
        elif isinstance(id, int):
            search_col = "id"
        else:
            raise NotImplementedError

        df = df_all[df_all[search_col] == id]
        df = df.reset_index(drop=True)

        # summary
        if summary_only:
            keep_cols = [
                "preferredLabel_occs", "preferredLabel_skills", "relationType",
                "reuseLevel", "skillType", "skill_classification_esco", "coreness"
            ]
            df = df[keep_cols]

        return df

    # TODO: write function to get tasks for greening occupations/

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

            for i in tqdm(range(len(self.occupations))):
                occ_uri = self.occupations.iloc[i, :][1]

                # lookup corresponding skills
                skill_list = self.occupations_to_skills[
                    self.occupations_to_skills["occupationUri"] == occ_uri
                ]

                # create vector
                skill_vector = []
                for j, skill in enumerate(self.skills.conceptUri.values):

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
                index=self.occupations.conceptUri,
                columns=self.skills.conceptUri,
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
                    index=self.occupations.conceptUri,
                    columns=self.occupations.conceptUri,
                    data=occ_sim_matrix_coo,
                )

                # save
                df_occ_sim_matrix_weighted_coo.to_pickle(target_path)

            else:
                osim_dict["osim_{}".format(variant)] = pd.read_pickle(target_path)

        return osim_dict

    def combine_skills_metadata(self, export=True, fpath_out=None):
        """
        Combine all skill-level metadata (SMD).

        Evaluation comments
            - ESCO v.1.1.0 comprises 13891 skills compared to v.1.0.3 with 13485 skills.
            - Hence, overall 406 new skills in v.1.1.0 compared to v.1.0.3.
            - 570 skills labelled as green in v.1.1.0, some of which are presumably new,
            while other's already existed.
            - After merging we don't obtain coreness values for 512 skills in v.1.1.0.
            - This means that the conceptUri of 512 - 406 = 106 skills that existed in
            the last version must have changed.

        Returns
        -------
        smd : pd.DataFrame
            DataFrame containing the raw ESCO skills pillar data enriched by additional
            metadata (green labels, coreness).
        """

        # output fpath
        target_path = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "skills_metadata_{}.csv".format(self.esco_language),
        )

        if self.skills_metadata is None:
            # -------------------------------------------------------------------------
            # Green Skills
            # -------------------------------------------------------------------------
            set_diff = utils.get_set_diff(self.skills_green, self.skills, "conceptUri")

            # copy skills df and join green skills information
            smd = self.skills.copy()
            smd = smd.merge(
                right=self.skills_green[set_diff],
                on="conceptUri",
                how="left",
                suffixes=["", "_green"],
                validate="one_to_one",
            )

            # TODO: add eth colnames once skills are fully classified
            smd = smd.fillna(value={self.green_id_colname_esco: False})

            # -------------------------------------------------------------------------
            # Brown Skills
            # -------------------------------------------------------------------------
            set_diff = utils.get_set_diff(self.skills_brown, self.skills, "conceptUri")

            smd = smd.merge(
                right=self.skills_brown[set_diff],
                on="conceptUri",
                how="left",
                validate="one_to_one",
                suffixes=["", "_brown"],
            )

            # TODO: add eth column names once skills are fully classified
            smd = smd.fillna(value={self.brown_id_colname_esco: False})

            # -------------------------------------------------------------------------
            # Derive Neutral Skills
            # -------------------------------------------------------------------------
            smd = classify_by_gbn(
                df=smd,
                col_name_green=self.green_id_colname_esco,
                col_name_brown=self.brown_id_colname_esco,
                col_name_neutral=self.neutral_id_colname_esco,
                col_name_clfc=self.skills_clsf_colname_esco,
            )

            # TODO: repeat for eth data once skills are fully classified
            # classify_neutral_skills(
            #     df=smd,
            #     col_name_green=self.green_id_colname_eth,
            #     col_name_brown=self.brown_id_colname_eth,
            #     col_name_neutral=self.neutral_id_colname_eth,
            #     col_name_clfc=self.skills_clsf_colname_eth
            # )

            # -------------------------------------------------------------------------
            # Coreness Metric
            # -------------------------------------------------------------------------
            # append conceptUri of ESCO v1.0.3 skills
            keep_cols = ["conceptUri", "preferredLabel"]
            skills_coreness_with_uri = self.skills_coreness_mcc.merge(
                right=self.skills_v103[keep_cols],
                left_on="preferred_label",
                right_on="preferredLabel",
                how="left",
                validate="one_to_one",
            )

            # Merge Coreness to Skills Pillar
            keep_cols = ["conceptUri", "coreness"]
            smd = smd.merge(
                right=skills_coreness_with_uri[keep_cols],
                on="conceptUri",
                how="left",
                validate="one_to_one",
            )

            # optionally save for inspection
            if export:
                if fpath_out is None:
                    fpath_out = target_path
                smd.to_csv(fpath_out, sep=";")

            # assign
            self.skills_metadata = smd

        return smd

    # todo: implement weighted form of esco-based greenness measure
    def calc_gbn_shares_skill_based(self, weighted=False):
        # read
        osms = self.occupation_skills_matrix()

        if not weighted:
            osm = osms["osm_unweighted"]
        else:
            osm = osms["osm_weighted"]

        if self.skills_metadata is None:
            self.combine_skills_metadata()

        # number of occupation-specific skills
        n_total_specific_skills = osm.sum(axis=1).values

        data_out = {
            "n_total_specific_skills": n_total_specific_skills,
        }

        # calc occupational shares for each skill type
        colnames = []

        # TODO: remove [:1] once ETH skill classification is finished
        for ds in self.skill_clsf_ds[:1]:
            for skill_type in self.skill_types_gbn:
                col = self.skill_col_fmt.format(type=skill_type, ds=ds)
                colname_shares = self.gbn_share_fmt.format(type=skill_type, ds=ds)

                # number of occupation-specific green/brown/neutral skills
                specific_skills = (
                    osm.values
                    * self.skills_metadata[col].astype(np.int8).values
                )

                n_gbn_specific_skills = specific_skills.sum(axis=1)

                # occupational share
                occ_share = n_gbn_specific_skills / n_total_specific_skills

                # append to dict
                data_out[
                    "n_{type}_specific_skills_{ds}".format(type=skill_type, ds=ds)
                ] = n_gbn_specific_skills

                data_out[colname_shares] = occ_share
                colnames.append(colname_shares)

        df_occ_shares_per_skill_type = pd.DataFrame(
            index=osm.index, data=data_out
        )

        # check if shares sum to 100%
        assert np.allclose(df_occ_shares_per_skill_type[colnames].sum(axis=1).values, 1)

        # classify into discrete GBN categories
        # TODO: check if only one True per col.
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
            right=self.crosswalk_onet_esco_mcc_full,
            on="onet_code",
            how="left",
            validate="1:m",
        )

        # downcast dtypes
        greenness_onet_esco = utils.downcast_df(greenness_onet_esco)

        # save
        greenness_onet.to_csv(
            os.path.join(self.data_interim, "onet", "task_based_greenness_onet.csv"),
            sep=";",
        )

        greenness_onet_esco.to_csv(
            os.path.join(
                self.data_interim,
                "onet",
                "task_based_greenness_onet_esco_{}.csv".format(
                    self.esco_version.replace(".", "")
                ),
            ),
            sep=";",
        )

        return greenness_onet_esco

    def read_brown_occupations_vona2018(self):
        """
        Read Vona et al. 2019 brown occupation classification and merge to ESCO occupations via Nesta ONET-ESCO crosswalk.

        Returns
        -------

        """
        brown_occs_vona2018 = pd.read_csv(
            os.path.join(
                self.data_raw, "onet", "vona_2018", "brown_occupations_vona2018.csv"
            )
        )

        # pad to 8 digits
        brown_occs_vona2018["soc_code"] = brown_occs_vona2018["soc_code"] + ".00"

        # add binary brown occupation classification
        brown_occs_vona2018[self.brown_id_onet] = np.ones(
            brown_occs_vona2018.shape[0], dtype=bool
        )

        # merge to ESCO occupations pillar via crosswalk
        brown_occs_vona2018_esco = brown_occs_vona2018.merge(
            right=self.crosswalk_onet_esco_mcc_full,
            left_on="soc_code",
            right_on="onet_code",
            how="left",
            # validate="m:1",
        ).drop(columns=["soc_code", "occupation"], axis=1)

        # drop duplicates & missing vals
        dups = brown_occs_vona2018_esco.concept_uri.duplicated()
        brown_occs_vona2018_esco = brown_occs_vona2018_esco.loc[~dups]

        brown_occs_vona2018_esco.dropna(subset="concept_uri", inplace=True)

        # downcast dtype
        brown_occs_vona2018_esco = utils.downcast_df(brown_occs_vona2018_esco)

        # rearrange
        col_order = [
            "id",
            "concept_uri",
            "preferred_label",
            "isco_level_4",
            "is_brown_onet",
            "onet_code",
            "onet_occupation",
        ]
        brown_occs_vona2018_esco = brown_occs_vona2018_esco[col_order]

        # save
        brown_occs_vona2018_esco.to_csv(
            os.path.join(
                self.data_interim,
                "onet",
                "brown_occupations_vona2018_esco_{}.csv".format(
                    self.esco_version.replace(".", "")
                ),
            ),
            sep=";",
        )

        return brown_occs_vona2018_esco

    def isco_correspondence_table(self):
        df_isco = self.isco_groups.copy()

        for lvl in [1, 2, 3, 4]:
            df_sub = df_isco.loc[
                df_isco.code.str.len() == lvl, "preferredLabel"
            ].reindex(df_isco.index)
            df_isco["isco_label_{}".format(lvl)] = df_sub

        df_isco = df_isco.rename(
            columns={
                "code": "isco_code",
                "preferredLabel": "isco_label",
            }
        )

        return df_isco

    def combine_occupation_metadata(self, export=True, fpath_out=None):
        # target fpath
        output_dir = os.path.join(self.data_interim, "esco", self.esco_version)
        fname_no_ext = "occ_metadata_{}".format(self.esco_language)

        if self.occupation_metadata is None:
            # init container
            omd = self.occupations.copy()

            # pad at 4d level
            top_level = 4
            omd[self.fmt_string_isco_lvl.format(top_level)] = (
                omd["iscoGroup"].str.pad(width=top_level, side="left", fillchar="0")
            )

            # decompose isco 4-digit into lower levels
            for lvl in [1, 2, 3]:
                new_colname = self.fmt_string_isco_lvl.format(lvl)
                omd[new_colname] = omd["isco_level_4"].str[0:lvl]

            # attach labels at each level
            df_isco = self.isco_correspondence_table()

            for lvl in [1, 2, 3, 4]:
                omd = omd.merge(
                    left_on=self.fmt_string_isco_lvl.format(lvl),
                    right=df_isco.loc[:, ("isco_code",
                                          self.fmt_string_isco_label.format(lvl))],
                    right_on="isco_code",
                ).drop(columns=["isco_code"])

            # merge onet codes and names via crosswalk
            # omd = omd.merge(
            #     right=self.crosswalk_onet_esco_mcc_full,
            #     left_on="conceptUri",
            #     right_on="concept_uri",
            #     how="left",
            #     suffixes=["", "_y"],
            #     validate="1:1",
            # )

            # Read data sets
            df_gbn_shares_esco = self.calc_gbn_shares_skill_based()
            df_greenness_onet_esco = self.read_greenness_task_based()
            df_brown_occs_vona2018_esco = self.read_brown_occupations_vona2018()

            # merge variables to occupation df
            # -------------------------------------------------------------------------
            # TODO: join --> ONET job zone, COVID Exposure

            # join ESCO-based GBN shares
            omd = omd.merge(
                right=df_gbn_shares_esco,
                on="conceptUri",
                how="left",
                suffixes=["", "_y"],
                validate="1:1",
            )

            # join O*NET-based G shares
            omd = omd.merge(
                right=df_greenness_onet_esco.dropna(subset="concept_uri"),
                left_on="conceptUri",
                right_on="concept_uri",
                how="left",
                suffixes=["", "_y"],
                validate="1:1",
            )

            # join O*Net based Brown occupations
            omd = omd.merge(
                right=df_brown_occs_vona2018_esco,
                left_on="conceptUri",
                right_on="concept_uri",
                how="left",
                suffixes=["", "_y"],
                validate="1:1",
            )

            # create ONET-based G/B/N classification

            # TODO: refactor to function
            # classify green  & neutral occupations (data from GTP covers more
            # occupations, therefore using those. correlation with Vona 2018
            # greenness scores ~ 1)
            green_threshold = 0

            omd[self.green_id_onet] = (
                omd[self.gbn_share_fmt.format(type="green", ds="gtp")] > green_threshold
            )

            omd[self.brown_id_onet] = omd[self.brown_id_onet].fillna(False)

            omd[self.neutral_id_onet] = (omd[self.green_id_onet] == False) & (
                omd[self.brown_id_onet] == False
            )

            # there are 30 occupations that have been matched to both brown and green
            query_ambiguous_cases = (omd[self.brown_id_onet] == True) & (
                omd[self.green_id_onet] == True
            )

            # define ambiguous cases as brown (see thesis)
            omd.loc[query_ambiguous_cases, self.green_id_onet] = False
            # occ_metadata = occ_metadata.reset_index(drop=True)

            # create single classification column
            # TODO: assert check if only one True per col.
            omd["gbn_classification_onet"] = omd[
                [self.brown_id_onet, self.green_id_onet, self.neutral_id_onet]
            ].idxmax(axis=1)

            # rename to green/brown/neutral.
            omd["gbn_classification_onet"] = (
                omd["gbn_classification_onet"]
                .str.split(pat="_", expand=True)
                .iloc[:, 1]
            )

            # filter out duplicate columns
            omd = omd.drop(omd.filter(regex="_y$").columns.tolist(), axis=1)

            # check if all occs are classified
            assert omd["gbn_classification_onet"].isna().sum() == 0

            # make sure there are no duplicates
            assert omd.conceptUri.duplicated().sum() == 0

            # update class variable
            self.occupation_metadata = omd

            # optional: save for inspection
            if export:
                if fpath_out is None:
                    utils.save_df_to_files(
                        omd, output_dir=output_dir, fname_no_ext=fname_no_ext, sep=";"
                    )
                else:
                    omd.to_csv(fpath_out, sep=";")
        else:
            print("Occupation metadata already loaded.")
            omd = self.occupation_metadata

        return omd

    # todo (minor): add COVID and automation-related data to agg process
    def aggregate_occ_data_by_isco(
        self,
        isco08_digits=[1, 2, 3, 4],
        use_weights=False,
    ):
        if self.occupation_metadata is None:
            self.combine_occupation_metadata()
        self.occupation_metadata["n_occ_esco"] = np.ones(len(self.occupation_metadata))

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
            group_var_1 = self.fmt_string_isco_lvl.format(n_digits)
            group_var_2 = self.fmt_string_isco_label.format(n_digits)

            # aggregate
            if not use_weights:
                occ_grouped = self.occupation_metadata.groupby([group_var_1, group_var_2
                                                                ]).agg(agg_dict)
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
            occ_grouped[self.isco_join_col_of] = occ_grouped[group_var_1]
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


def classify_by_gbn(
    df,
    col_name_green,
    col_name_brown,
    col_name_neutral,
    col_name_clfc="skillClassification",
):

    df[col_name_neutral] = (df[col_name_green] == False) & (df[col_name_brown] == False)
    # sanity check
    ambiguous_cases = (df[col_name_brown] == True) & (df[col_name_green] == True)
    assert ambiguous_cases.sum() == 0

    if col_name_clfc is not None:
        # create skill classification column: green/brown/neutral
        gbn_classification = df[
            [col_name_green, col_name_brown, col_name_neutral]
        ].idxmax(axis=1)

        df[col_name_clfc] = gbn_classification.str.split(pat="_", expand=True).iloc[
            :, 1
        ]
    return df


if __name__ == "__main__":
    # CONFIGS
    config_paths = "paths_config.yml"
    config_data = "data_config.yml"
    config_model = "model_config.yml"
    config_vis = "vis_config.yml"

    # ESCO
    esco = OccFramework(
        fn_config_path=config_paths,
        fn_config_data=config_data,
    )

    # esco.occupation_skills_matrix()
    # esco.occupation_similarity_matrix()
    esco.combine_skills_metadata()
    # esco.read_greenness_task_based()
    esco.combine_occupation_metadata()
    # esco.aggregate_occ_data_by_isco()
