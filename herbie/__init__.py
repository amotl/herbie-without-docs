## Brian Blaylock
## April 28, 2021

import warnings
import configparser
from pathlib import Path

########################################################################
# Load custom xarray accessors
try:
    import herbie.accessors
except:
    warnings.warn("heribe xarray accessors could not be imported.")
    pass

########################################################################
# Configure Herbie
# Configuration file is save in `~/config/herbie/config.cfg`
# `_default_save_dir` is the default path to save GRIB2 files.

config = configparser.ConfigParser()
_config_path = Path('~').expanduser() / '.config' / 'herbie' / 'config.cfg'

user_home_default = str(Path('~').expanduser() / 'data')
source_priority_default = ','.join(['aws', 'nomads', 'google', 'azure', 'pando', 'pando2'])

if not _config_path.exists():
    _config_path.parent.mkdir(parents=True)
    _config_path.touch()
    config.read(_config_path)
    config.add_section('download')
    config.set('download', 'default_save_dir', user_home_default)
    config.set('download', 'default_priority', source_priority_default)
    with open(_config_path, 'w') as configfile:
        config.write(configfile)
    print(f'⚙ Created config file [{_config_path}]',
          f'with default download directory set as [{user_home_default}]', 
          f'and default source priority as ')

config.read(_config_path)

try:
    _default_save_dir = Path(config.get('download', 'default_save_dir'))
    _default_priority = config.get('download', 'default_priority').split(',')
except:
    print(f'🦁🐯🐻 oh my! {_config_path} looks weird,',
          f'but I will add new settings')
    try:
        config.add_section('download')
    except:
        pass  # section already exists
    config.set('download', 'default_save_dir', user_home_default)
    config.set('download', 'default_priority', source_priority_default)
    with open(_config_path, 'w') as configfile:
        config.write(configfile)
    _default_save_dir = Path(config.get('download', 'default_save_dir'))
    _default_priority = config.get('download', 'default_priority').split(',')