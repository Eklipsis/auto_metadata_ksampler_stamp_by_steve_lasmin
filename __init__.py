"""
Auto_Metadata_Ksampler_Stamp by Steve Lasmin
============================================
A ComfyUI custom node that automatically extracts KSampler metadata
from the workflow JSON and stamps it onto the bottom of generated images.

Author: Steve Lasmin (Eklipsis)
GitHub: https://github.com/Eklipsis
Support: https://boosty.to/stevelasmin
Email: real.eclipse@gmail.com
"""

from .auto_metadata_ksampler_stamp import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
