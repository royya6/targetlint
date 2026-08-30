from setuptools import setup, find_packages

setup(
    name="targetlint",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "jinja2>=3.1",
    ],
    entry_points={
        "console_scripts": [
            "targetlint=targetlint.cli:main",
        ],
    },
    python_requires=">=3.9",
)
