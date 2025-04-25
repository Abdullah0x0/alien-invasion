from setuptools import setup, Extension

process_utils_module = Extension(
    'process_utils',
    sources=['src/process_utils.c'],
    include_dirs=['/usr/include', '/usr/local/include'],
)

setup(
    name='process_utils',
    version='0.1',
    description='Process creation and management utilities using system calls',
    ext_modules=[process_utils_module],
) 