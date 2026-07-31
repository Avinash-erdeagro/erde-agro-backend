
"""
Render a satellite GeoTIFF's bands into map-overlay PNGs + legends, stored as
SatelliteMapLayer rows.

Heavy geo deps (rasterio / matplotlib / numpy / PIL) are imported lazily inside
the functions so this module — and the Celery task that imports it — stays
importable in environments without GDAL (e.g. the local dev venv).
"""

import io
import logging
from urllib.parse import urlparse

import numpy as np
import rasterio
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap, Normalize
from rasterio.warp import transform_bounds

from django.conf import settings

from satelliteapp.models import SatelliteMapLayer
from satelliteapp.services.irriwatch import _get_s3_client

logger = logging.getLogger(__name__)

NUMBER_OF_INTERVALS = 5

BAND_SETTINGS = {
    2: {"name": "Vegetation cover %", "legend_decimals": 1, "rounding_decimals": 1},
    3: {"name": "Soil moisture root zone m3/m3", "legend_decimals": 3, "rounding_decimals": 2},
    4: {"name": "Leaf Nitrogen %", "legend_decimals": 2, "rounding_decimals": 1},
    5: {"name": "NDVI", "legend_decimals": 3, "rounding_decimals": 2},
    6: {"name": "Actual ET mm", "legend_decimals": 2, "rounding_decimals": 1},
    7: {"name": "Total Crop Growth kg/ha", "legend_decimals": 1, "rounding_decimals": 1},
    8: {"name": "Crop Growth kg/ha/day", "legend_decimals": 1, "rounding_decimals": 1},
    9: {"name": "Soil Water Potential log10(hPa)", "legend_decimals": 3, "rounding_decimals": 3,
        "log_transform": True, "reverse_colors": True},
    10: {"name": "Moisture Status", "categorical": True},
    11: {"name": "Variable Rate Irrigation mm", "legend_decimals": 2, "rounding_decimals": 1},
    12: {"name": "Soil Temperature C", "legend_decimals": 2, "rounding_decimals": 1, "reverse_colors": True},
    13: {"name": "Leaf Temperature C", "legend_decimals": 2, "rounding_decimals": 1, "reverse_colors": True},
}

CONTINUOUS_COLORS = ["#9e0142", "#f46e43", "#fee08c", "#e5f498", "#64c0a6", "#5e4fa2"]

MOISTURE_STATUS = {
    1: {"color": "#D33722", "label": "Stressed"},
    2: {"color": "#E67A29", "label": "Limited"},
    3: {"color": "#448124", "label": "Adequate"},
    4: {"color": "#5600F3", "label": "Wet"},
    5: {"color": "#AC9A23", "label": "Sparse vegetation"},
}


def _rgb_hex(rgba):
    r, g, b = (int(round(c * 255)) for c in rgba[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _rgba_to_png(rgba_uint8):
    buf = io.BytesIO()
    Image.fromarray(rgba_uint8, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()


def _latlon_bounds(src):
    west, south, east, north = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
    return {"north": north, "south": south, "east": east, "west": west}


def _render_continuous(data, valid, conf):
    import numpy as np

    rounding = conf["rounding_decimals"]
    factor = 10 ** rounding
    vmin = np.floor(np.nanpercentile(valid, 1) * factor) / factor
    vmax = np.ceil(np.nanpercentile(valid, 99) * factor) / factor
    if vmin >= vmax:
        vmax = vmin + (10 ** -rounding)

    break_values = np.linspace(vmin, vmax, NUMBER_OF_INTERVALS + 1)

    colors = CONTINUOUS_COLORS.copy()
    if conf.get("reverse_colors", False):
        colors.reverse()
    cmap = LinearSegmentedColormap.from_list("ramp", colors, N=256)
    norm = Normalize(vmin=vmin, vmax=vmax, clip=True)

    rgba = cmap(norm(data))                 # H x W x 4 float, 0..1
    rgba[~np.isfinite(data)] = 0.0          # NoData -> fully transparent
    rgba_uint8 = (rgba * 255).astype(np.uint8)

    legend = [
        {"value": round(float(v), conf["legend_decimals"]), "color": _rgb_hex(cmap(norm(v)))}
        for v in break_values
    ]
    return rgba_uint8, legend


def _render_categorical(data):
    h, w = data.shape
    rgba_uint8 = np.zeros((h, w, 4), dtype=np.uint8)
    for value, meta in sorted(MOISTURE_STATUS.items()):
        r, g, b = _hex_to_rgb(meta["color"])
        rgba_uint8[data == value] = (r, g, b, 255)
    legend = [{"label": meta["label"], "color": meta["color"]} for _, meta in sorted(MOISTURE_STATUS.items())]
    return rgba_uint8, legend


def _download_tif(tiff_url):
    key = urlparse(tiff_url).path.lstrip("/")
    obj = _get_s3_client().get_object(Bucket=settings.SATELLITE_DATA_S3_BUCKET, Key=key)
    return obj["Body"].read()


def _upload_png(png_bytes, field_uuid, observation_date, band_number):
    key = f"png/{observation_date}/{field_uuid}/band_{band_number:02d}.png"
    _get_s3_client().put_object(
        Bucket=settings.SATELLITE_DATA_S3_BUCKET,
        Key=key,
        Body=png_bytes,
        ContentType="image/png",
    )
    return (
        f"https://{settings.SATELLITE_DATA_S3_BUCKET}.s3."
        f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
    )


def process_result_map_layers(satellite_result):
    """Render every configured band of a result's tif into SatelliteMapLayer rows."""
    import numpy as np
    import rasterio

    if not satellite_result.tiff_url:
        logger.warning("Result %s has no tiff_url; skipping map layers", satellite_result.id)
        return 0

    order_farm = satellite_result.order_farm
    field_uuid = order_farm.irriwatch_field_uuid
    obs_date = satellite_result.observation_date

    tif_bytes = _download_tif(satellite_result.tiff_url)

    created = 0
    with rasterio.open(io.BytesIO(tif_bytes)) as src:
        bounds = _latlon_bounds(src)
        for band_number, conf in BAND_SETTINGS.items():
            if band_number > src.count:
                continue

            data = src.read(band_number, masked=True).astype(np.float64).filled(np.nan)
            if conf.get("log_transform", False):
                data = np.where(data < 0, np.log10(np.abs(data)), np.nan)

            valid = data[np.isfinite(data)]
            if valid.size == 0:
                continue

            if conf.get("categorical", False):
                rgba, legend = _render_categorical(data)
                is_categorical = True
            else:
                rgba, legend = _render_continuous(data, valid, conf)
                is_categorical = False

            png_url = _upload_png(_rgba_to_png(rgba), field_uuid, obs_date, band_number)

            SatelliteMapLayer.objects.update_or_create(
                order_farm=order_farm,
                observation_date=obs_date,
                band_number=band_number,
                defaults={
                    "layer_name": conf["name"],
                    "unit": "",
                    "png_url": png_url,
                    "bounds": bounds,
                    "legend": legend,
                    "is_categorical": is_categorical,
                },
            )
            created += 1

    logger.info(
        "Rendered %s map layers for result %s (field %s, %s)",
        created, satellite_result.id, field_uuid, obs_date,
    )
    return created