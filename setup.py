"""
setup.py – MirAI_OS package configuration.

Kept minimal; all package metadata lives in pyproject.toml (added as a
companion file).  This file exists so `pip install -e .` works out of the
box in older pip versions.
"""

from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", encoding="utf-8") as f:
    install_requires = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="MirAI_OS",
    version="1.0.0",
    author="MirAI_OS contributors",
    description="Autonomous AI agent for Kali Linux / WSL2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/andreygorban1582-dev/MirAI_OS",
    packages=find_packages(exclude=["tests*", "installer*", "scripts*"]),
    install_requires=install_requires,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "mirai=main:app",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
)
