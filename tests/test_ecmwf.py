## Brian Blaylock
## October 13, 2021

"""
Tests for downloading ECMWF model
"""
from datetime import datetime

from herbie.archive import Herbie

now = datetime.now()
yesterday = datetime(now.year, now.month, now.day-1)
today_str = yesterday.strftime("%Y-%m-%d %H:%M")




def test_ecmwf():
    H = Herbie(yesterday, model="ecmwf", product="oper", save_dir="$TMPDIR")

    # Test full file download
    H.download()
    assert H.get_localFilePath().exists()

    # Test partial file download
    # temperature at all levels
    H.download(":t:")
    assert H.get_localFilePath(":t:").exists()

    # Test partial file xarray
    H.xarray(":10(?:u|v):", remove_grib=False)
    assert H.get_localFilePath(":10(?:u|v):").exists()
