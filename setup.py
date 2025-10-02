"""Setup configuration for the LLM Benchmarking Tool."""

from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Read README for long description
try:
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Universal LLM Engine Benchmarking Tool"

setup(
    name="llm-benchmark-tool",
    version="0.1.0",
    author="Gabriel Sampaio",
    author_email="gab@redhat.com",
    description="Universal LLM Engine Benchmarking Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gsampaio/llm-benchmark-tool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Benchmark",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "llm-benchmark=src.cli.main:app",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
)

