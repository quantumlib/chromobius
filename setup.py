import os
import pathlib
import shutil
import subprocess
import sys

import setuptools
import setuptools.command.build_ext


class CMakeExtension(setuptools.Extension):
    def __init__(self, name, sourcedir=""):
        setuptools.Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(setuptools.command.build_ext.build_ext):
    def build_extension(self, ext):
        import ninja

        build_temp = os.path.join(self.build_temp, ext.name)
        os.makedirs(build_temp, exist_ok=True)
        build_env = {
            **os.environ,
            'CMAKE_LIBRARY_OUTPUT_DIRECTORY': '',
            'CMAKE_FORCE_PYBIND_CHROMOBIUS': '1',
        }

        subprocess.check_call([
            "cmake",
            ext.sourcedir,
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={pathlib.Path(self.get_ext_fullpath(ext.name)).parent.absolute()}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            *[
                env_arg_item
                for env_arg_item in os.environ.get("CMAKE_ARGS", "").split(" ")
                if env_arg_item
            ],
            "-GNinja",
            f"-DCMAKE_MAKE_PROGRAM:FILEPATH={os.path.join(ninja.BIN_DIR, 'ninja')}",
        ], cwd=build_temp, env=build_env)

        subprocess.check_call([
            "cmake",
            "--build",
            ".",
            "--target",
            "chromobius_pybind",
        ], cwd=build_temp, env=build_env)


__version__ = '0.0.dev0'

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# HACK: Workaround difficulties collecting data files for the package by just making a directory.
package_data_dir = pathlib.Path(__file__).parent / 'package_data'
package_data_dir.mkdir(exist_ok=True)
shutil.copyfile(
    pathlib.Path(__file__).parent / 'doc' / 'chromobius.pyi',
    package_data_dir / 'chromobius.pyi',
)

setuptools.setup(
    name="chromobius",
    version=__version__,
    author="Craig Gidney",
    url="https://github.com/quantumlib/chromobius",
    description="A fast implementation of the mobius color code decoder.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    ext_modules=[CMakeExtension("chromobius")],
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.10",
    setup_requires=['ninja', 'pybind11~=2.11.1'],
    requires=['numpy', 'stim'],

    # Needed on Windows to avoid the default `build` colliding with Bazel's `BUILD`.
    options={'build': {'build_base': 'python_build_chromobius'}},

    # Add files in package_data_dir to the wheel.
    # I don't know why it has to be so esoteric, but I tried for hours.
    # This is the best I could come up with.
    packages=[''],
    package_dir={'': package_data_dir.name},
    package_data={'': [str(e) for e in package_data_dir.iterdir()]},
    include_package_data=True,
)
