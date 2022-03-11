import logging
import os

import numpy as np
import pandas as pd
from tqdm import tqdm

from src import UsefulPaths
from src.utils import load_config


class EscoDs(UsefulPaths):
    """ESCO Dataset Class"""

    def __init__(self, fn_config_data, fn_config_path):
        """
        TODO: description

        Parameters
        ----------
        fn_config_data : str
            Name of yml file with ESCO-specific configurations.
        """
        # inherit class storing useful paths
        UsefulPaths.__init__(self=self, config_fname=fn_config_path)

        # TODO: dynamically assign class variables based on data config file?
        self.config_data = load_config(
            os.path.join(self.config_dir, fn_config_data)
        )

        self.onet_esco_crosswalk = pd.read_csv(self.path_crosswalk_onet_esco)

        # esco configurations
        self.esco_language = self.config_data["ESCO"]["LANGUAGE"]  # "en"
        self.esco_version = self.config_data["ESCO"][
            "VERSION"
        ]  # "v1.0.3" or "v1.1.0"
        self.esco_version_newest = self.config_data["ESCO"]["VERSION_NEWEST"]
        self.esco_skills_hierarchy_version = (
            "v1.0.8" if self.esco_version == "v1.0.3" else "v1.1.0"
        )

        # static params
        self.green_id_colname = "skillGreen"

        # containers
        self.osm = None
        self.osim = None
        self.data = None

        # read data
        self.data = self._read()

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
        # additional
        # -----------------------------------------------------------------------------
        # green skill labels
        green_skills = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version_newest,
                "greenSkillsCollection_{}.csv".format(self.esco_language),
            )
        )
        green_skills[self.green_id_colname] = True

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

        # skill groups
        skill_groups = pd.read_csv(
            os.path.join(
                self.data_raw,
                "esco",
                self.esco_version,
                "skillGroups_{}.csv".format(self.esco_language),
            )
        )
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

        return {
            "occ": occ,
            "skills": skills,
            "occ_skills_mapping": occ_skills_mapping,
            "skills_green": green_skills,
            "skills_coreness": skills_coreness,
            "skills_hierarchy": skills_hierarchy,
            "skills_hierarchy_kanders": skills_hierarchy_kanders,
            "skill_groups": skill_groups,
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
                for j, skill in enumerate(
                    self.data["skills"].conceptUri.values
                ):

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

        return self._calc_osm_variants(
            occ_skills_matrix_eo=occ_skills_matrix_eo
        )

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

            logger.info(
                "Calculating {} occupation similarity matrix.".format(variant)
            )
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
                osim_dict["osim_{}".format(variant)] = pd.read_pickle(
                    target_path
                )

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
            # Coreness Metric
            # -------------------------------------------------------------------------
            # append conceptUri of ESCO v1.0.3 skills
            skills_v103 = pd.read_csv(
                os.path.join(
                    self.data_raw,
                    "esco",
                    "v1.0.3",
                    "skills_{}.csv".format(
                        self.config_data["ESCO"]["LANGUAGE"]
                    ),
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
            skills_metadata = pd.read_csv(target_path)
            self.data["skills_metadata"] = skills_metadata
        return skills_metadata

    # todo: implement weighted form of esco-based greenness measure
    def calc_greenness_skill_based(self, weighted=False):
        osm = self.occupation_skills_matrix()
        occ_skills_matrix_unweighted = osm["osm_unweighted"]

        # number of occupation-specific skills
        n_total_specific_skills = occ_skills_matrix_unweighted.sum(
            axis=1
        ).values

        # number of occupation-specific green skills
        green_specific_skills = (
            occ_skills_matrix_unweighted.values
            * self.data["skills_metadata"].skillGreen.astype(np.int8).values
        )

        n_green_specific_skills = green_specific_skills.sum(axis=1)

        # greenness
        greenness_esco = n_green_specific_skills / n_total_specific_skills

        # create df
        data = {
            "n_total_specific_skills": n_total_specific_skills,
            "n_green_specific_skills": n_green_specific_skills,
            "greenness_esco": greenness_esco,
        }

        df_greenness_esco = pd.DataFrame(
            index=occ_skills_matrix_unweighted.index, data=data
        )
        return df_greenness_esco.reset_index()

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
            os.path.join(
                self.data_interim, "onet", "task_based_greenness_onet.csv"
            )
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

    def occupation_metadata(self):
        """

        Returns
        -------

        """
        target_fpath = os.path.join(
            self.data_interim,
            "esco",
            self.esco_version,
            "occ_metadata_{}.csv".format(self.esco_language),
        )

        if not os.path.exists(target_fpath):
            # ESCO-based Greenness (skill-based, supply side)
            df_greenness_esco = self.calc_greenness_skill_based()

            # ONET-based Greenness (task-based, demand side)
            df_greenness_onet_esco = self.read_greenness_task_based()

            # merge ESCO and O*NET greenness scores to occupation df
            occ_metadata = self.data["occ"].copy()

            # ESCO-based
            occ_metadata = occ_metadata.merge(
                right=df_greenness_esco,
                on="conceptUri",
                how="left",
                validate="one_to_one",
            )

            # O*NET-based
            occ_metadata = occ_metadata.merge(
                right=df_greenness_onet_esco,
                left_on="conceptUri",
                right_on="concept_uri",
                how="left",
                validate="1:m",
            )

            occ_metadata.to_csv(target_fpath)
        else:
            occ_metadata = pd.read_csv(target_fpath)

        return occ_metadata
