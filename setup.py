from setuptools import setup, find_packages

setup(
    name="nfc-offer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyscard",  # Used for NFC operations
        "chia_rs",  # Used for Decoding/Encoding operations
        "ndef",     # Used for NFC writing in ndef format
    ],
    python_requires=">=3.7",
) 
