"""Novel to screenplay YAML conversion toolkit."""

from importlib.metadata import PackageNotFoundError, version

from novel2script.converter import convert_text_to_script

try:
    __version__ = version("novel2script")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"


__all__ = ["__version__", "convert_text_to_script"]
