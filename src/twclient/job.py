'''
Job tasks providing core functionality
'''

# The idea is that we define what the jobs are via __all__ in each job file,
# then import whatever is so defined into this file

# pylint: disable=wildcard-import,unused-wildcard-import

from . import _job_base
from ._job_base import *

from . import _job_config
from ._job_config import *

from . import _job_export
from ._job_export import *

from . import _job_fetch
from ._job_fetch import *

from . import _job_initialize
from ._job_initialize import *

from . import _job_show
from ._job_show import *

from . import _job_tag
from ._job_tag import *

_modules = [
    _job_base,
    _job_config,
    _job_export,
    _job_fetch,
    _job_initialize,
    _job_show,
    _job_tag,
]

__all__ = []
for mod in _modules:
    __all__ += getattr(mod, '__all__')
