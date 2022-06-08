import os
from nlu import utils


###
# loads config from yaml-files based on python-environment
# returns config-dictionary
###
def load_config():
    config_dir = './nlu/config/'

    return utils.yaml_load(config_dir+'config.yml')