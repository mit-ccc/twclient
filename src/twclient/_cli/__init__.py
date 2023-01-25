'''
The command-line interface, including the entrypoint script and supporting
classes.
'''

from . import command
from . import config
from . import entrypoint
from . import export
from . import fetch
from . import initialize
from . import show
from . import tag

_modules = [command, config, entrypoint, export, fetch, initialize, show, tag]

__all__ = []
for module in _modules:
    if hasattr(module, '__all__'):
        __all__ += getattr(module, '__all__')
