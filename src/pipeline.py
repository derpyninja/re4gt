import logging
from src.data import preprocess
from src.visualization import visualize

# CONFIGS
config_paths = "paths_config.yml"
config_data = "data_config.yml"
config_model = "model_config.yml"
config_vis = "vis_config.yml"

if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # Preprocessing
    preprocess.main(config_paths=config_paths, config_data=config_data)

    # Visualisation
