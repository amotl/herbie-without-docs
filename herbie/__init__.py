## Brian Blaylock
## April 28, 2021

import warnings
import toml
import os
from pathlib import Path


########################################################################
# Append Path object with my custom expand method so user can use
# environment variables in the config file (e.g., ${HOME}).
def _expand(self):
    """
    Fully expand and resolve the Path with the given environment variables.
    
    Example
    -------
    >>> Path('$HOME').expand()
    >>> PosixPath('/p/home/blaylock')
    """
    return Path(os.path.expandvars(self)).expanduser().resolve()

Path.expand = _expand

########################################################################
# Herbie configuration file
# Configuration file is save in `~/config/herbie/config.toml`
# `_default_save_dir` is the default path to save GRIB2 files.
_config_path = Path('~/.config/herbie/config.toml').expand()

########################################################################
# Default TOML Configuration Values
default_toml = f"""
['default']
save_dir = "{str(Path('~/data').expand())}"
priority = ['aws', 'nomads', 'google', 'azure', 'pando', 'pando2']
"""

########################################################################
# If a config file isn't found, make one
if not _config_path.exists():
    with open(_config_path, 'w') as f:
        toml_string = toml.dump(toml.loads(default_toml), f)
    print(f'⚙ Created config file [{_config_path}] with default values.')

########################################################################
# Read the config file
config = toml.load(_config_path)

config['default']['save_dir'] = Path(config['default']['save_dir']).expand()
