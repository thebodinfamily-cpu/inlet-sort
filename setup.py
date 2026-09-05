"""Build the optional native samplesort extension.

Project metadata lives in pyproject.toml. This file only declares the C
extension, which is marked optional so `pip install` still succeeds (falling
back to the pure-Python implementation) when no C compiler is available.
"""

from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension(
            "inlet_sort._inletsort",
            sources=["src/inlet_sort/_inletsort.c"],
            optional=True,
        )
    ],
)
