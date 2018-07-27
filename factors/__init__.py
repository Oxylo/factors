from .models import LifeTable  # NOQA
from .models import get_available_tablenames

__version__ = "0.1.0"

__all__ = [
    'LifeTable', __version__
]

tables = get_available_tablenames
