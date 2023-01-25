'''
Job tasks providing core functionality
'''

from .job_base import __all__ as job_base
from .job_config import __all__ as job_config
from .job_export import __all__ as job_export
from .job_fetch import __all__ as job_fetch
from .job_initialize import __all__ as job_initialize
from .job_show import __all__ as job_show
from .job_tag import __all__ as job_tag

_modules = [
    job_base,
    job_config,
    job_export,
    job_fetch,
    job_initialize,
    job_show,
    job_tag,
]

__all__ = []
for module in _modules:
    if hasattr(module, '__all__'):
        __all__ += getattr(module, '__all__')
