import os
import shutil

import setuptools

import card_extractor


def setup() -> None:
    with open('requirements.txt') as text_file:
        requirements = text_file.read().splitlines()
        requirements = [r for r in requirements if r and not r.startswith('#')]

    version = card_extractor.__version__

    setuptools.setup(
        packages=setuptools.find_packages(),
        install_requires=requirements,
        python_requires='>=3.10.0',
        include_package_data=True,
        version=version,
        name='card_extractor',
    )

    build_path = 'build/'
    if os.path.exists(build_path):
        shutil.rmtree(build_path)

    egg_info_path = 'card_extractor.egg-info'
    if os.path.exists(egg_info_path):
        shutil.rmtree(egg_info_path)


if __name__ == '__main__':
    setup()
