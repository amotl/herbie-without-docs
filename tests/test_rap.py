## Brian Blaylock
## October 13, 2021

"""
Tests for downloading RAP model
"""
from herbie.archive import Herbie
from datetime import datetime
import pandas as pd


today = pd.to_datetime("today").floor("1D")
save_dir = "$TMPDIR/Herbie-Tests/"


def test_rap_aws():
    # Test
    H = Herbie(
        today,
        model="rap",
        save_dir=save_dir,
    )
    assert H.grib is not None

    # Test downloading the file
    H = Herbie(
        today,
        model="rap",
        save_dir=save_dir,
    )
    H.download()
    assert H.get_localFilePath().exists()

    H.xarray("TMP:2 m", remove_grib=False)
    assert H.get_localFilePath("TMP:2 m").exists()


def test_rap_historical():
    """Search for RAP urls on NCEI that I know exist"""

    H = Herbie(
        "2019-11-23",
        model="rap_historical",
        product="analysis",
        save_dir=save_dir,
    )
    assert H.grib is not None

    H = Herbie(
        "2005-01-01",
        model="rap_historical",
        product="analysis",
        save_dir=save_dir,
    )
    assert H.grib is not None


def test_rap_ncei():
    H = Herbie(
        "2020-03-15",
        model="rap_ncei",
        product="rap-130-13km",
        save_dir=save_dir,
    )
    assert H.grib is not None
