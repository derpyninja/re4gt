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


def read_esco(input_folder, config):
    """

    Parameters
    ----------
    input_folder
    config

    Returns
    -------

    """

    # esco configurations
    esco_language = config["ESCO"]["LANGUAGE"]  # "en"
    esco_version = config["ESCO"]["VERSION"]  # "v1.0.3" or "v1.1.0"
    esco_skills_hierarchy_version = "v1.0.8" if esco_version == "v1.0.3" else "v1.1.0"

    # core
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

    # additional
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
        "skill_groups": skill_groups,
        "skills_hierarchy": skills_hierarchy,
        "skills_hierarchy_kanders": skills_hierarchy_kanders,
    }


def occ_skills_matrix(input_folder, output_folder, config):
    """

    Parameters
    ----------
    input_folder
    output_folder
    config

    Returns
    -------

    """

    # read esco data
    esco_data = read_esco(input_folder=input_folder, config=config)
    occ, skills, occ_skills_mapping, _, _, _ = esco_data

    esco_version = config["ESCO"]["VERSION"]

    target_path = os.path.join(
        output_folder, "esco", esco_version, "occ_skills_matrix_weighted.pkl"
    )

    if not os.path.exists(target_path):
        # build occupation skills matrix
        errors = 0
        skill_vectors = []

        for i in tqdm(range(len(occ))):
            occ_uri = occ.iloc[i, :][1]

            # lookup corresponding skills
            skill_list = occ_skills_mapping[
                occ_skills_mapping["occupationUri"] == occ_uri
            ]

            # create vector
            skill_vector = []
            for j, skill in enumerate(skills.conceptUri.values):

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
            index=occ.conceptUri,
            columns=skills.conceptUri,
            data=np.array(skill_vectors),
        )

        # save to disk
        occ_skills_matrix_eo.to_pickle(target_path)
    else:
        # read from disk
        occ_skills_matrix_eo = pd.read_pickle(target_path)

    return occ_skills_matrix_eo


@click.command()
@click.argument("input_filepath", type=click.Path(exists=True))
@click.argument("output_filepath", type=click.Path())
@click.argument("config_filepath", type=click.Path(exists=True))
def main(input_filepath, output_filepath, config_filepath):
    """Runs data processing scripts to turn raw data from (../raw) into
    cleaned data ready to be analyzed (saved in ../processed).
    """
    logger = logging.getLogger(__name__)
    logger.info("making interim data sets from raw data")

    # define config file
    config = load_config(config_filepath)

    # pre-processing chain
    occ_skills_matrix(input_filepath, output_filepath, config)


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]
    print(project_dir)

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
