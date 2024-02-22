from setuptools import setup, find_packages

setup(
    name="Automations plugin",
    version="v1.0",
    license_files = ('LICENSE',),
    description="Initiate new automations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author_email="eliel.dzik@weizmann.ac.il",
    author="Eliel DZIL",
    url="https://github.com/eloulili/automation-examples",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[], # PROVIDE OTHER PYTHON REQUIREMENTS, ex: "pioreactor>=23.6.0", "numpy>=1.0"
    entry_points={
        "pioreactor.plugins": "<PLUGIN_NAME> = Automation_plugin"
    },
)