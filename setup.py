import glob
import os
import pathlib
import re
import shutil
import subprocess
import sys

import setuptools
import setuptools.command.build_ext


CC_FILES = glob.glob("src/**/*.cc", recursive=True)
H_FILES = glob.glob("src/**/*.h", recursive=True) + glob.glob("src/**/*.inl", recursive=True)
CMAKE_FILES = ['CMakeLists.txt', *glob.glob("file_lists/*", recursive=True)]
RELEVANT_SOURCE_FILES = sorted(CMAKE_FILES + CC_FILES + H_FILES)


class CMakeExtension(setuptools.Extension):
    def __init__(self, name, sourcedir, sources):
        setuptools.Extension.__init__(self, name, sources=sources)
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

        osx_cmake_flags = []
        if sys.platform.startswith("darwin"):
            # Cross-compile support for macOS - respect ARCHFLAGS if set
            archs = re.findall(r"-arch (\S+)", os.environ.get("ARCHFLAGS", ""))
            if archs:
                osx_cmake_flags = ["-DCMAKE_OSX_ARCHITECTURES={}".format(";".join(archs))]
            else:
                import platform
                arch = platform.machine()
                if arch:
                    osx_cmake_flags = [f"-DCMAKE_OSX_ARCHITECTURES={arch}"]

        subprocess.check_call([
            "cmake",
            ext.sourcedir,
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={pathlib.Path(self.get_ext_fullpath(ext.name)).parent.absolute()}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DVERSION_INFO={__version__}",
            *osx_cmake_flags,
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


__version__ = '1.0.dev0'

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# HACK: Workaround difficulties collecting data files for the package by just making a directory.
package_data_dir = pathlib.Path(__file__).parent / 'package_data'
package_data_dir.mkdir(exist_ok=True)
doc_chromobius = pathlib.Path(__file__).parent / 'doc' / 'chromobius.pyi'
if doc_chromobius.exists():
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
    ext_modules=[CMakeExtension("chromobius", sourcedir=".", sources=RELEVANT_SOURCE_FILES)],
    cmdclass={"build_ext": CMakeBuild},
    python_requires=">=3.10",
    setup_requires=['ninja', 'pybind11~=2.11.1'],
    install_requires=['numpy', 'stim'],

    # Needed on Windows to avoid the default `build` colliding with Bazel's `BUILD`.
    # Also, the replacement name is short to avoid blowing the 256 character path limit on windows.
    options={'build': {'build_base': 'b'}},

    # Add files in package_data_dir to the wheel.
    # I don't know why it has to be so esoteric, but I tried for hours.
    # This is the best I could come up with.
    packages=['chromobius'],
    package_dir={'chromobius': package_data_dir.name},
    package_data={'chromobius': [str(e) for e in package_data_dir.iterdir()]},
    include_package_data=True,
)
