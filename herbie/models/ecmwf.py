## Added by Brian Blaylock
## January 26, 2022

"""
A Herbie template for the ECMWF opendata GRIB2 files.

See the `media release <https://www.ecmwf.int/en/about/media-centre/news/2022/ecmwf-makes-wide-range-data-openly-available>`_.

- Copyright statement: Copyright "© 2022 European Centre for Medium-Range Weather Forecasts (ECMWF)".
- Source www.ecmwf.int
- Licence Statement: This data is published under a Creative Commons Attribution 4.0 International (CC BY 4.0). https://creativecommons.org/licenses/by/4.0/
- Disclaimer: ECMWF does not accept any liability whatsoever for any error or omission in the data, their availability, or for any loss or damage arising from their use.

"""
from datetime import datetime


class ecmwf:
    def template(self):

        # TODO: This will need to be updated someday
        version = '0p4-beta'
        #version = '0p4'

        self.DESCRIPTION = "ECMWF open data"
        self.DETAILS = {
            "ECMWF": "https://confluence.ecmwf.int/display/UDOC/ECMWF+Open+Data+-+Real+Time",
        }
        self.PRODUCTS = {
            "oper": "operational high-resolution forecast, atmospheric fields",
            "enfo": "ensemble forecast, atmospheric fields",
            "wave": "wave forecasts",
            "waef": "ensemble forecast, ocean wave fields,",
            #"scda": "short cut-off high-resolution forecast, atmospheric fields (also known as high-frequency products)",
            #"scwv": "short cut-off high-resolution forecast, ocean wave fields (also known as high-frequency products)",
            #"mmsf": "multi-model seasonal forecasts fields from the ECMWF model only.",
        }

        # example file
        # https://data.ecmwf.int/forecasts/20220126/00z/0p4-beta/oper/20220126000000-0h-oper-fc.grib2

        # product suffix
        if self.product in ['enfo', 'waef']:
            product_suffix = 'ef'
        else:
            product_suffix = 'fc'

        post_root = f'{self.date:%Y%m%d/%Hz}/{version}/{self.product}/{self.date:%Y%m%d%H%M%S}-{self.fxx}h-{self.product}-{product_suffix}.grib2'

        self.SOURCES = {
            "azure": f"https://ai4edataeuwest.blob.core.windows.net/ecmwf/{post_root}",
            "ecmwf": f"https://data.ecmwf.int/forecasts/{post_root}",

        }
        self.IDX_SUFFIX = [".index"]
        self.IDX_STYLE = 'eccodes'  # 'wgrib2' or 'eccodes'
        self.LOCALFILE = f"{self.get_remoteFileName}"
