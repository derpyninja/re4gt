# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from tqdm import tqdm

import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

from src.utils import load_config


# todo: refactor code into object-based structure (otherwise --> too much repetition!)
def read_esco(input_folder, config):
    """
    Read main ESCO pillars (occupations, skills, occupation-skills mapping) and skills hierarchy.

    Parameters
    ----------
    input_folder : str
        Folder where raw data is stored.
    config : dict
        Parsed yml file in form of a dictionary.

    Returns
    -------
    dict
        Dictionary containing data frames of the relevant ESCO variables.
    """

    # esco configurations
    esco_language = config["ESCO"]["LANGUAGE"]  # "en"
    esco_version = config["ESCO"]["VERSION"]  # "v1.0.3" or "v1.1.0"
    esco_skills_hierarchy_version = "v1.0.8" if esco_version == "v1.0.3" else "v1.1.0"

    # -----------------------------------------------------------------------------------------------------------------
    # core
    # -----------------------------------------------------------------------------------------------------------------
    occ = pd.read_csv(
        os.path.join(
            input_folder,
            "esco",
            esco_version,
            "occupations_{}.csv".format(esco_language),
        )
    )
    skills = pd.read_csv(
        os.path.join(
            input_folder, "esco", esco_version, "skills_{}.csv".format(esco_language)
        )
    )
    occ_skills_mapping = pd.read_csv(
        os.path.join(input_folder, "esco", esco_version, "occupationSkillRelations.csv")
    )

    # -----------------------------------------------------------------------------------------------------------------
    # additional
    # -----------------------------------------------------------------------------------------------------------------
    # green skill labels
    green_skills = pd.read_csv(
        os.path.join(
            input_folder,
            "esco",
            esco_version,
            "greenSkillsCollection_{}.csv".format(esco_language),
        )
    )
    green_id_colname = "skillGreen"
    green_skills[green_id_colname] = True

    # coreness values
    skills_coreness = pd.read_csv(
        os.path.join(
            input_folder,
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
            input_folder,
            "esco",
            esco_version,
            "skillGroups_{}.csv".format(esco_language),
        )
    )
    skills_hierarchy = pd.read_csv(
        os.path.join(
            input_folder,
            "esco",
            esco_skills_hierarchy_version,
            "skillsHierarchy_{}.csv".format(esco_language),
        )
    )

    skills_hierarchy_kanders = pd.read_csv(
        os.path.join(
            input_folder,
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
        "skill_groups": skill_groups,
        "skills_hierarchy": skills_hierarchy,
        "skills_hierarchy_kanders": skills_hierarchy_kanders,
    }


def occupation_skills_matrix(input_folder, output_folder, config):
    """
    Calculate occupation-skills matrix (OSM) based on ESCO data. In the OSM rows denote occupations and columns skills.
    Depending on the settings in the main configuration file, essential and optional skills are assigned different
    weights on an occupation-to-occupation basis. An unweighted variant is always also created as a baseline.

    Parameters
    ----------
    input_folder : str
        Folder where raw data is stored.
    output_folder : str
        Folder where interim data is stored.
    config : dict
        Parsed yml file in form of a dictionary.

    Returns
    -------
    dict
        Dictionary storing two variants of the OSM as pd.DataFrame:
            (1) the weighted form (coded as np.float),
            (2) the unweighted/uniform form (coded as np.int8)
    """
    logger = logging.getLogger(__name__)
    logger.info("Creating occupation-skills matrix.")

    # read esco data
    esco_data = read_esco(input_folder=input_folder, config=config)

    target_path = os.path.join(
        output_folder, "esco", config["ESCO"]["VERSION"], "occ_skills_matrix.pkl"
    )

    if not os.path.exists(target_path):
        # build occupation skills matrix
        errors = 0
        skill_vectors = []

        for i in tqdm(range(len(esco_data["occ"]))):
            occ_uri = esco_data["occ"].iloc[i, :][1]

            # lookup corresponding skills
            skill_list = esco_data["occ_skills_mapping"][
                esco_data["occ_skills_mapping"]["occupationUri"] == occ_uri
            ]

            # create vector
            skill_vector = []
            for j, skill in enumerate(esco_data["skills"].conceptUri.values):

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
            index=esco_data["occ"].conceptUri,
            columns=esco_data["skills"].conceptUri,
            data=np.array(skill_vectors),
        )

        # save to disk
        occ_skills_matrix_eo.to_pickle(target_path)
    else:
        # read matrix from disk
        occ_skills_matrix_eo = pd.read_pickle(target_path)

        # get weights of weighted form
        replace_weighted = {
            1: config["ESCO"]["WEIGHT_ESSENTIAL_SKILL"],
            2: config["ESCO"]["WEIGHT_OPTIONAL_SKILL"],
        }

        # calc weighted form
        occ_skills_matrix_weighted = occ_skills_matrix_eo.replace(
            to_replace=replace_weighted
        )

        # calc unweighted form
        occ_skills_matrix_unweighted = occ_skills_matrix_eo.replace(
            to_replace=[1, 2], value=config["ESCO"]["WEIGHT_UNIFORM"]
        )
    return {
        "osm_weighted": occ_skills_matrix_weighted,
        "osm_unweighted": occ_skills_matrix_unweighted,
    }


def occupation_similarity_matrix(input_folder, output_folder, config):
    """
    Calculate weighted and unweighted forms of the co-occurrence occupation similarity matrix (OSIM).

    Parameters
    ----------
    input_folder : str
        Folder where raw data is stored.
    output_folder : str
        Folder where interim data is stored.
    config : dict
        Parsed yml file in form of a dictionary.

    Returns
    -------
    dict
        Dictionary containing X versions of the OSIM:
            (1) Skills COO based on weighted OSM
            (2) Skills COO based on unweighted OSM
    """
    logger = logging.getLogger(__name__)

    # read ESCO data
    occ = read_esco(input_folder=input_folder, config=config)["occ"]

    # read base OSM and calculate variants
    osm_dict = occupation_skills_matrix(input_folder, output_folder, config)

    esco_version = config["ESCO"]["VERSION"]
    target_path_template = os.path.join(
        project_dir,
        "data",
        "interim",
        "esco",
        esco_version,
        "occ_sim_matrix_{}_coo.pkl",
    )

    # calculate co-occurrence matrices for both variants (via matrix multiplication with transpose form)
    osim_dict = {}
    for osm_version, osm_data in osm_dict.items():
        variant = osm_version.split("_")[1]

        # fixme: calculation of unweighted COOC matrix does not work
        if variant == "unweighted":
            continue

        logger.info("Calculating {} occupation similarity matrix.".format(variant))
        target_path = target_path_template.format(variant)

        if not os.path.exists(target_path):
            occ_sim_matrix_coo = np.dot(osm_data.values, osm_data.values.transpose())

            # to df
            df_occ_sim_matrix_weighted_coo = pd.DataFrame(
                index=occ.conceptUri, columns=occ.conceptUri, data=occ_sim_matrix_coo
            )

            # save
            df_occ_sim_matrix_weighted_coo.to_pickle(target_path)

        else:
            osim_dict["osim_{}".format(variant)] = pd.read_pickle(target_path)

    return osim_dict


def esco_skills_metadata(input_folder, output_folder, config):
    """
    Calculate and merge relevant metadata to the ESCO skills pillar (greenness, coreness).

    Evaluation
        - ESCO v.1.1.0 comprises 13891 skills compared to v.1.0.3 with 13485 skills.
        - Hence, overall 406 new skills in v.1.1.0 compared to v.1.0.3.
        - 570 skills labelled as green in v.1.1.0, some of which are presumably new, while other's already existed.
        - After merging we don't obtain coreness values for 512 skills in v.1.1.0.
        - This means that the conceptUri of 512 - 406 = 106 skills that existed in the last version must have changed.

    Parameters
    ----------
    input_folder : str
        Folder where raw data is stored.
    output_folder : str
        Folder where interim data is stored.
    config : dict
        Parsed yml file in form of a dictionary.

    Returns
    -------
    skills_metadata : pd.DataFrame
        DataFrame containing the raw ESCO skills pillar data enriched by additional metadata (green labels, coreness).
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "Calculating & merging ESCO occupation metadata (green labels, coreness)."
    )

    # read esco data
    esco_data = read_esco(input_folder=input_folder, config=config)
    green_id_colname = "skillGreen"

    # output fpath
    target_path = os.path.join(
        output_folder,
        "esco",
        config["ESCO"]["VERSION"],
        "skills_metadata_{}.csv".format(config["ESCO"]["LANGUAGE"]),
    )

    if not os.path.exists(target_path):
        # Green Skills

        # Find cols that are unique in green skills file compared to general skills file
        # "The difference between A and B contains all elements that are in A but not in B."
        # Source: https://www.kaggle.com/ashukr/sets-and-venn-diagram-in-python
        set_diff = list(
            set(esco_data["skills_green"].columns.values.tolist())
            - set(esco_data["skills"].columns.values.tolist())
        )
        set_diff.insert(0, "conceptUri")

        # copy skills df and join information on green skills
        skills_metadata = esco_data["skills"].copy()
        skills_metadata = skills_metadata.merge(
            right=esco_data["skills_green"][set_diff],
            on="conceptUri",
            how="left",
            validate="one_to_one",
        )
        skills_metadata = skills_metadata.fillna(value={green_id_colname: False})

        # Coreness Metric
        if not config["ESCO"]["VERSION"] == "v1.0.3":

            # append conceptUri of ESCO v1.0.3 skills
            skills_v103 = pd.read_csv(
                os.path.join(
                    input_folder,
                    "esco",
                    "v1.0.3",
                    "skills_{}.csv".format(config["ESCO"]["LANGUAGE"]),
                )
            )
            keep_cols = ["conceptUri", "preferredLabel"]
            skills_coreness = esco_data["skills_coreness"].merge(
                right=skills_v103[keep_cols],
                left_on="preferred_label",
                right_on="preferredLabel",
                how="left",
                validate="one_to_one",
            )

        # Merge Green Labels and Coreness to Skills Pillar
        keep_cols = ["conceptUri", "coreness"]
        skills_metadata = skills_metadata.merge(
            right=skills_coreness[keep_cols],
            on="conceptUri",
            how="left",
            validate="one_to_one",
        )

        # save
        # note: this dataset refers to variable "greenskill" in the FDZ Verfahrensbeschreibung
        skills_metadata.to_csv(target_path)
    else:
        skills_metadata = pd.read_csv(target_path)

    return skills_metadata


# todo: write function
def esco_occupation_metadata(input_folder, output_folder, config):
    pass


# TODO: need to uncomment click commands for CLI usage
# @click.command()
# @click.argument("input_filepath", type=click.Path(exists=True))
# @click.argument("output_filepath", type=click.Path())
# @click.argument("config_filepath", type=click.Path(exists=True))
def main(input_filepath, output_filepath, config_filepath):
    """
    Runs data processing scripts to turn raw data from (../raw) into
    cleaned data ready to be analyzed (saved in ../processed).

    Parameters
    ----------
    input_filepath : str
        Path where raw data is stored.
    output_filepath : str
        Path where interim data is stored.
    config_filepath : dict
        Path to yml file containing pre-processing configurations.

    Returns
    -------
    None
    """
    logger = logging.getLogger(__name__)
    logger.info("Making interim data sets from raw data.")

    # load config file
    config = load_config(config_filepath)

    # pre-processing chain
    occupation_skills_matrix(input_filepath, output_filepath, config)
    occupation_similarity_matrix(input_filepath, output_filepath, config)
    esco_skills_metadata(input_filepath, output_filepath, config)


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]
    print(project_dir)

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    # load_dotenv(find_dotenv())

    main(
        input_filepath=os.path.join(project_dir, "data", "raw"),
        output_filepath=os.path.join(project_dir, "data", "interim"),
        config_filepath=os.path.join(project_dir, "configs", "main_config.yml"),
    )
