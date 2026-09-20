"""SHIN: explicit effects, bounded execution, checked AI output."""
from .compiler import ShinError, compile_source
from .runtime import VM, Untrusted

__version__ = '0.1.0a1'
__all__ = ['ShinError', 'compile_source', 'VM', 'Untrusted']
