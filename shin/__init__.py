"""SHIN: explicit effects, bounded execution, checked AI output."""
from .compiler import ShinError, compile_source
from .runtime import VM, Untrusted

__version__ = '0.2.0a2'
__all__ = ['ShinError', 'compile_source', 'VM', 'Untrusted']
