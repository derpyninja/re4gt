import os
import yaml


def load_config(config_filepath):
    """
    Load yaml configuration file.

    Parameters
    ----------
    config_filepath

    Returns
    -------

    """
    with open(config_filepath) as file:
        config_file = yaml.safe_load(file)
    return config_file


def get_dict_subset(dict, keys):
    """Subset dict based on a set of keys."""
    return {k: dict.get(k, None) for k in keys}


def ccdir(path):
    """check create output directory"""
    if not os.path.exists(path):
        os.makedirs(path)
    return None


def trim_whitespace(df):
    """Trim whitespaces from all text columns."""
    return df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)


def save_df_to_files(df, output_dir, fname_no_ext, ftypes=["csv", "pkl"]):
    """Save pd.DataFrame or pd.Series to multiple file types."""

    # check-create output directory
    ccdir(output_dir)

    # iteratively store files to specified file types
    for ftype in ftypes:
        if ftype == "csv":
            df.to_csv(
                os.path.join(
                    output_dir,
                    "{fname}.{ext}".format(fname=fname_no_ext, ext=ftype),
                )
            )
        elif ftype == "pkl":
            df.to_pickle(
                os.path.join(
                    output_dir,
                    "{fname}.{ext}".format(fname=fname_no_ext, ext=ftype),
                )
            )
        else:
            raise NotImplementedError("Some file types are not supported.")

    return None
