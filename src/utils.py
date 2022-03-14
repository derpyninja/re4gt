import os
import yaml
from pathlib import Path
from pprint import pprint


project_path = Path(__file__).resolve().parents[1]


class UsefulPaths:
    """
    Facilitates access to useful paths, to project base directory and other
    folders. Copied and adapted from
    https://github.com/nestauk/mapping-career-causeways/blob/main/mapping_career_causeways/__init__.py.
    """

    def __init__(self, config_fname=None):
        """

        Parameters
        ----------
        config_fname : str
            Name of yml file storing additional path-specific configurations.
        """

        self.project_dir = str(project_path)
        self.data_dir = os.path.join(self.project_dir, "data")
        self.data_raw = os.path.join(self.project_dir, "data", "raw")
        self.data_interim = os.path.join(self.project_dir, "data", "interim")
        self.data_processed = os.path.join(self.project_dir, "data", "processed")
        self.data_external = os.path.join(self.project_dir, "data", "external")
        self.notebook_dir = os.path.join(self.project_dir, "notebooks")
        self.figure_dir = os.path.join(self.project_dir, "results", "figures")
        self.table_dir = os.path.join(self.project_dir, "results", "tables")
        self.report_dir = os.path.join(self.project_dir, "results", "reports")
        self.models_dir = os.path.join(self.project_dir, "models")
        self.config_dir = os.path.join(self.project_dir, "configs")

        # optionally parse config file params
        if config_fname is not None:
            config = load_config(os.path.join(self.config_dir, config_fname))
            metadata = config["metadata"]
            config.pop("metadata")

            # unpack variables
            for k, v in config.items():
                for k2, v2 in v.items():
                    k_new = "{}_{}".format(k, k2)

                    # strings in this list are relative paths in the config
                    # file, starting from the project directory
                    if k in metadata["relative_paths"]:
                        v_new = os.path.join(self.project_dir, v2)
                    else:
                        v_new = v2
                    # instantiate class attributes
                    # TODO: check if that really makes sense. don't think so.
                    setattr(self, k_new, v_new)


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


def get_dict_subset(d, keys):
    """Subset dict based on a set of keys."""
    return {k: d.get(k, None) for k in keys}


def ccdir(path):
    """check create output directory"""
    if not os.path.exists(path):
        os.makedirs(path)
    return None


def print_dict(d):
    """Print dict keys and values"""
    for k, v in d.items():
        print("{} : {}".format(k, v))
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


if __name__ == "__main__":
    paths = UsefulPaths(config_fname="paths_config.yml")

    class_vars = vars(paths)
    for key, val in class_vars.items():
        print(key, val)
