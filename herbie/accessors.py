## Brian Blaylock
## April 23, 2021

"""
==================================
Herbie Extension: xarray accessors
==================================

Extend the xarray capabilities with a custom accessor.
http://xarray.pydata.org/en/stable/internals.html#extending-xarray

To use the herbie xarray accessor, do this...

.. code-block:: python

    H = Herbie('2021-01-01', model='hrrr')
    ds = H.xarray('TMP:2 m')
    ds.herbie.crs
    ds.herbie.plot()

"""
import functools
import cartopy.crs as ccrs
import metpy  # * Needed for metpy accessor
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import Polygon


_level_units = dict(
    adiabaticCondensation="adiabatic condensation",
    atmosphere="atmosphere",
    atmosphereSingleLayer="atmosphere single layer",
    boundaryLayerCloudLayer="boundary layer cloud layer",
    cloudBase="cloud base",
    cloudCeiling="cloud ceiling",
    cloudTop="cloud top",
    depthBelowLand="m",
    equilibrium="equilibrium",
    heightAboveGround="m",
    heightAboveGroundLayer="m",
    highCloudLayer="high cloud layer",
    highestTroposphericFreezing="highest tropospheric freezing",
    isobaricInhPa="hPa",
    isobaricLayer="hPa",
    isothermZero="0 C",
    isothermal="K",
    level="m",
    lowCloudLayer="low cloud layer",
    meanSea="MSLP",
    middleCloudLayer="middle cloud layer",
    nominalTop="nominal top",
    pressureFromGroundLayer="Pa",
    sigma="sigma",
    sigmaLayer="sigmaLayer",
    surface="surface",
)


@xr.register_dataset_accessor("herbie")
class HerbieAccessor:
    """
    Accessor for xarray Datasets opened with Herbie

    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj
        self._center = None

    @property
    def center(self):
        """Return the geographic center point of this dataset."""
        if self._center is None:
            # we can use a cache on our accessor objects, because accessors
            # themselves are cached on instances that access them.
            lon = self._obj.latitude
            lat = self._obj.longitude
            self._center = (float(lon.mean()), float(lat.mean()))
        return self._center

    @functools.cached_property
    def crs(self):
        """
        Cartopy coordinate reference system (crs) from a cfgrib Dataset.

        Projection information is from the grib2 message for each variable.

        Parameters
        ----------
        ds : xarray.Dataset
            An xarray.Dataset from a GRIB2 file opened by the cfgrib engine.
        """

        ds = self._obj

        # Get variables that have dimensions
        # (this filters out the gribfile_projection variable)
        variables = [i for i in list(ds) if len(ds[i].dims) > 0]

        ds = ds.metpy.parse_cf(varname=variables)
        crs = ds.metpy_crs.item().to_cartopy()
        return crs

    @functools.cached_property
    def polygon(self):
        """
        Get a polygon of the domain boundary.
        """
        ds = self._obj

        LON = ds.longitude.data
        LAT = ds.latitude.data

        # Path of array outside border starting from the lower left corner
        # and going around the array counter-clockwise.
        outside = (
            list(zip(LON[0, :], LAT[0, :]))
            + list(zip(LON[:, -1], LAT[:, -1]))
            + list(zip(LON[-1, ::-1], LAT[-1, ::-1]))
            + list(zip(LON[::-1, 0], LAT[::-1, 0]))
        )
        outside = np.array(outside)

        ###############################
        # Polygon in Lat/Lon coordinates
        x = outside[:, 0]
        y = outside[:, 1]
        domain_polygon_latlon = Polygon(zip(x, y))

        ###################################
        # Polygon in projection coordinates
        transform = self.crs.transform_points(ccrs.PlateCarree(), x, y)

        # Remove any points that run off the projection map (i.e., point's value is `inf`).
        transform = transform[~np.isinf(transform).any(axis=1)]
        x = transform[:, 0]
        y = transform[:, 1]
        domain_polygon = Polygon(zip(x, y))

        return domain_polygon, domain_polygon_latlon

    def nearest_points(self, points, names=None, verbose=True):
        """
        Get the nearest latitude/longitude points from a xarray Dataset.

        Info
        ----
        - Stack Overflow: https://stackoverflow.com/questions/58758480/xarray-select-nearest-lat-lon-with-multi-dimension-coordinates
        - MetPy Details: https://unidata.github.io/MetPy/latest/tutorials/xarray_tutorial.html?highlight=assign_y_x

        Parameters
        ----------
        ds : xr.Dataset
            A Herbie-friendly xarray Dataset
        points : tuple (lon, lat) or list of tuples
            The longitude and latitude (lon, lat) coordinate pair (as a tuple)
            for the points you want to pluck from the gridded Dataset.
            A list of tuples may be given to return the values from multiple points.
        names : list
            A list of names for each point location (i.e., station name).
            None will not append any names. names should be the same
            length as points.

        Benchmark
        ---------
            This is **much** faster than my old "pluck_points" method.
            For matchign 1,948 points:
            - `nearest_points` completed in 7.5 seconds.
            - `pluck_points` completed in 2 minutes.
        """
        ds = self._obj

        # Check if MetPy has already parsed the CF metadata grid projection.
        # Do that if it hasn't been done yet.
        if "metpy_crs" not in ds:
            ds = ds.metpy.parse_cf()

        # Apply the MetPy method `assign_y_x` to the dataset
        # https://unidata.github.io/MetPy/latest/api/generated/metpy.xarray.html?highlight=assign_y_x#metpy.xarray.MetPyDataArrayAccessor.assign_y_x
        ds = ds.metpy.assign_y_x()

        # Convert the requested [(lon,lat), (lon,lat)] points to map projection.
        # Accept a list of point tuples, or Shapely Points object.
        # We want to index the dataset at a single point.
        # We can do this by transforming a lat/lon point to the grid location
        crs = ds.metpy_crs.item().to_cartopy()
        # lat/lon input must be a numpy array, not a list or polygon
        if isinstance(points, tuple):
            # If a tuple is give, turn into a one-item list.
            points = np.array([points])
        if not isinstance(points, np.ndarray):
            # Points must be a 2D numpy array
            points = np.array(points)
        lons = points[:, 0]
        lats = points[:, 1]
        transformed_data = crs.transform_points(ccrs.PlateCarree(), lons, lats)
        xs = transformed_data[:, 0]
        ys = transformed_data[:, 1]

        # Select the nearest points from the projection coordinates.
        # TODO: Is there a better way?
        # There doesn't seem to be a way to get just the points like this
        # ds = ds.sel(x=xs, y=ys, method='nearest')
        # because it gives a 2D array, and not a point-by-point index.
        # Instead, I have too loop the ds.sel method
        new_ds = xr.concat(
            [ds.sel(x=xi, y=yi, method="nearest") for xi, yi in zip(xs, ys)],
            dim="point",
        )

        # Add list of names as a coordinate
        if names is not None:
            # Assign the point dimension as the names.
            assert len(points) == len(
                names
            ), "`points` and `names` must be same length."
            new_ds["point"] = names

        return new_ds

    def plot(self, ax=None, common_features_kw={}, **kwargs):
        """Plot data on a map."""
        # From Carpenter_Workshop:
        # https://github.com/blaylockbk/Carpenter_Workshop
        import matplotlib.pyplot as plt

        try:
            from toolbox.cartopy_tools import common_features, pc
            from paint.radar import cm_reflectivity
            from paint.radar2 import cm_reflectivity
            from paint.standard2 import cm_dpt, cm_pcp, cm_rh, cm_tmp, cm_wind
        except:
            print("The plotting accessor requires my Carpenter Workshop. Try:")
            print(
                "`pip install git+https://github.com/blaylockbk/Carpenter_Workshop.git`"
            )

        ds = self._obj

        for var in ds.data_vars:
            if "longitude" not in ds[var].coords:
                # This is the case for the gribfile_projection variable
                continue

            print("cfgrib variable:", var)
            print("GRIB_cfName", ds[var].attrs.get("GRIB_cfName"))
            print("GRIB_cfVarName", ds[var].attrs.get("GRIB_cfVarName"))
            print("GRIB_name", ds[var].attrs.get("GRIB_name"))
            print("GRIB_units", ds[var].attrs.get("GRIB_units"))
            print("GRIB_typeOfLevel", ds[var].attrs.get("GRIB_typeOfLevel"))
            print()

            ds[var].attrs["units"] = (
                ds[var]
                .attrs["units"]
                .replace("**-1", "$^{-1}$")
                .replace("**-2", "$^{-2}$")
            )

            defaults = dict(
                scale="50m",
                dpi=150,
                figsize=(10, 5),
                crs=ds.herbie.crs,
                ax=ax,
            )

            common_features_kw = {**defaults, **common_features_kw}

            ax = common_features(**common_features_kw).STATES().ax

            title = ""
            kwargs.setdefault("shading", "auto")
            cbar_kwargs = dict(pad=0.01)

            if ds[var].GRIB_cfVarName in ["d2m", "dpt"]:
                ds[var].attrs["GRIB_cfName"] = "dew_point_temperature"

            ## Wind
            wind_pair = {"u10": "v10", "u80": "v80", "u": "v"}

            if ds[var].GRIB_cfName == "air_temperature":
                kwargs = {**cm_tmp().cmap_kwargs, **kwargs}
                cbar_kwargs = {**cm_tmp().cbar_kwargs, **cbar_kwargs}
                if ds[var].GRIB_units == "K":
                    ds[var] -= 273.15
                    ds[var].attrs["GRIB_units"] = "C"
                    ds[var].attrs["units"] = "C"

            elif ds[var].GRIB_cfName == "dew_point_temperature":
                kwargs = {**cm_dpt().cmap_kwargs, **kwargs}
                cbar_kwargs = {**cm_dpt().cbar_kwargs, **cbar_kwargs}
                if ds[var].GRIB_units == "K":
                    ds[var] -= 273.15
                    ds[var].attrs["GRIB_units"] = "C"
                    ds[var].attrs["units"] = "C"

            elif ds[var].GRIB_name == "Total Precipitation":
                title = "-".join(
                    [f"F{int(i):02d}" for i in ds[var].GRIB_stepRange.split("-")]
                )
                ds[var] = ds[var].where(ds[var] != 0)
                kwargs = {**cm_pcp().cmap_kwargs, **kwargs}
                cbar_kwargs = {**cm_pcp().cbar_kwargs, **cbar_kwargs}

            elif ds[var].GRIB_name == "Maximum/Composite radar reflectivity":
                ds[var] = ds[var].where(ds[var] >= 0)
                cbar_kwargs = {**cm_reflectivity().cbar_kwargs, **cbar_kwargs}
                kwargs = {**cm_reflectivity().cmap_kwargs, **kwargs}

            elif ds[var].GRIB_cfName == "relative_humidity":
                cbar_kwargs = {**cm_rh().cbar_kwargs, **cbar_kwargs}
                kwargs = {**cm_rh().cmap_kwargs, **kwargs}

            elif "wind" in ds[var].GRIB_cfName or "wind" in ds[var].GRIB_name:
                cbar_kwargs = {**cm_wind().cbar_kwargs, **cbar_kwargs}
                kwargs = {**cm_wind().cmap_kwargs, **kwargs}
                if ds[var].GRIB_cfName == "eastward_wind":
                    cbar_kwargs["label"] = "U " + cbar_kwargs["label"]
                elif ds[var].GRIB_cfName == "northward_wind":
                    cbar_kwargs["label"] = "V " + cbar_kwargs["label"]
            else:
                cbar_kwargs = {
                    **dict(
                        label=f"{ds[var].GRIB_parameterName.strip().title()} ({ds[var].units})"
                    ),
                    **cbar_kwargs,
                }

            p = ax.pcolormesh(
                ds.longitude, ds.latitude, ds[var], transform=pc, **kwargs
            )
            plt.colorbar(p, ax=ax, **cbar_kwargs)

            VALID = pd.to_datetime(ds.valid_time.data).strftime("%H:%M UTC %d %b %Y")
            RUN = pd.to_datetime(ds.time.data).strftime("%H:%M UTC %d %b %Y")
            FXX = f"F{pd.to_timedelta(ds.step.data).total_seconds()/3600:02.0f}"

            level_type = ds[var].GRIB_typeOfLevel
            if level_type in _level_units:
                level_units = _level_units[level_type]
            else:
                level_units = "unknown"

            if level_units.lower() in ["surface", "atmosphere"]:
                level = f"{title} {level_units}"
            else:
                level = f"{ds[var][level_type].data:g} {level_units}"

            ax.set_title(
                f"Run: {RUN} {FXX}",
                loc="left",
                fontfamily="monospace",
                fontsize="x-small",
            )
            ax.set_title(
                f"{ds.model.upper()} {level}\n", loc="center", fontweight="semibold"
            )
            ax.set_title(
                f"Valid: {VALID}",
                loc="right",
                fontfamily="monospace",
                fontsize="x-small",
            )

            # Set extent so no whitespace shows around pcolormesh area
            # TODO: Any better way to do this? With metpy.assign_y_x
            # !!!!: The `metpy.assign_y_x` method could be used for pluck_point :)
            try:
                if "x" in ds.dims:
                    ds = ds.metpy.parse_cf()
                    ds = ds.metpy.assign_y_x()

                    ax.set_extent(
                        [
                            ds.x.min().item(),
                            ds.x.max().item(),
                            ds.y.min().item(),
                            ds.y.max().item(),
                        ],
                        crs=ds.herbie.crs,
                    )
            except:
                pass

        return ax
