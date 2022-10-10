#!/usr/bin/env python3

"""
Iterates over modules and classes, listing their attributes and methods in markdown.
"""

import chromobius

import sys

from util_gen_stub_file import generate_documentation


def main():
    version = chromobius.__version__
    if "dev" in version or version == "VERSION_INFO" or "-dev" in sys.argv:
        version = "(Development Version)"
        is_dev = True
    else:
        version = "v" + version
        is_dev = False
    objects = [
        obj
        for obj in generate_documentation(obj=chromobius, full_name="chromobius", level=0)
        if all('[DEPRECATED]' not in line for line in obj.lines)
    ]
    global_methods = [obj for obj in objects if obj.full_name.islower()]
    not_global_methods = [obj for obj in objects if not obj.full_name.islower()]

    print(f"# Chromobius {version} API Reference")
    print()
    print("## Index")
    print("- `<top level methods>`")
    for obj in global_methods:
        level = obj.level + 1
        print((level - 1) * "    " + f"- [`{obj.full_name}`](#{obj.full_name})")
    for obj in not_global_methods:
        level = obj.level
        print((level - 1) * "    " + f"- [`{obj.full_name}`](#{obj.full_name})")

    print(f'''
```python
# Types used by the method definitions.
from typing import overload, TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Tuple, Union
import io
import pathlib
import numpy as np
```
'''.strip())

    for obj in global_methods + not_global_methods:
        print()
        print(f'<a name="{obj.full_name}"></a>')
        print("```python")
        print(f'# {obj.full_name}')
        print()
        if len(obj.full_name.split('.')) > 2:
            print(f'# (in class {".".join(obj.full_name.split(".")[:-1])})')
        else:
            print(f'# (at top-level in the chromobius module)')
        print('\n'.join(obj.lines))
        print("```")


if __name__ == '__main__':
    main()
