"""cogra (Cognitive Revolution Aesthetic): the look of 1950s-60s psychology
journals for matplotlib figures.

    import cogra                         # registers the fonts and styles
    plt.style.use("cogra")               # or cogra.use(); stack cogra-serif/-column/-page
    ...                                  # plot as usual, or with cogra.geoms
    cogra.restyle(fig)                   # or restyle a finished figure
    cogra.save_vintage(fig, "fig.png")   # 1-bit archival-scan copy
"""

from importlib.metadata import PackageNotFoundError, version

from . import geoms, wear
from .halftone import halftone
from .restyle import cogra, restyle
from .style import (
    HATCHES,
    bars,
    cache_dir,
    clear_cache,
    density_topo,
    format_p,
    raincloud,
    register_fonts,
    register_styles,
    save_vintage,
    signif,
    stars,
    topoplot,
    use,
    violin,
)

try:
    __version__ = version("cogra")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0+unknown"

# like SciencePlots: importing the package registers its fonts and makes the
# styles available as plt.style.use("cogra"), "cogra-serif", "cogra-column", "cogra-page"
register_fonts()
register_styles()

__all__ = [
    "HATCHES",
    "bars",
    "cache_dir",
    "clear_cache",
    "cogra",
    "density_topo",
    "format_p",
    "geoms",
    "halftone",
    "raincloud",
    "register_fonts",
    "register_styles",
    "restyle",
    "save_vintage",
    "signif",
    "stars",
    "topoplot",
    "use",
    "violin",
    "wear",
]
