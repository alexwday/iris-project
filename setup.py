from setuptools import setup, find_packages

setup(
    name="iris",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "openai",
        "requests",
        "cryptography",
        "psycopg2-binary",
        "jupyter",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "mypy",
        ],
    },
)
