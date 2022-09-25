# ArcGIS API for Python Map ipywidget

This directory contains all information needed to build the ipywidgets shipped with the `arcgis` package. At the moment, this just is the arcgis-map-ipywidget "map widget". There are some future planned widgets (charts, etc.).

# Setting up the environment

### npm/node/yarn
    - Make sure you have `nodejs`, `npm`, and `yarn` installed on your computer
    - run `npm install -g webpack webpack-cli`, or `npm install --save-dev webpack-cli`, or any command that makes `webpack` calleable from your terminal/cmd
    - in `geosaurus/src/arcgis/widgets/js`, run `yarn` to install all JS dependencies in the parent npm package space
    - in `geosaurus/src/arcgis/widgets/js/arcgis-map-ipywidget/`, run `yarn` to install all JS dependencies in the `arcgis-map-ipywidget` npm package space
    - If you are running into issues setting this up, contact David Vitale or Rhea Jackson

### jupyter

- Create a new blank conda environment, add all dependencies to the `arcgis` package to it (but not the `arcgis` package itself)
    - This can be accomplished by `conda env create -f /path/to/geosaurus/environment.yml`
- Activate the above environment
- Assert that `jupyter nbextension list` doesn't output any arcgis extension
    - Lines similar to `jupyter-js-widgets/extension  enabled` are OK 
- run `pip install -e /path/to/geosaurus/src --no-deps`
- run `jupyter nbextension install --py --sys-prefix --symlink arcgis`
- run `jupyter nbextension enable --py --sys-prefix arcgis`

# Modifying the source code and seeing your changes

## Jupyter notebook
- For any changes to the python source code, or javascript source code, do the following steps:
   - change directories to `./js/`
   - run `yarn build`, assert that there are no build errors
   - run `pip install -e /path/to/geosaurus/src --no-deps` again
   - Press the menu button that 'Restarts kernel and clears all output'
   - Refresh the page
 
## Jupyterlab extension

- If you are modifying the javascript source code in ./js/ and want to see the map widget in a jupyterlab setting:
    - change directories into `./js/arcgis-map-ipywidget/`
    - run this command: `jupyter labextension install @jupyter-widgets/jupyterlab-manager`
    - run `jupyter labextension install /path/to/geosaurus/src/arcgis/widgets/js/arcgis-map-ipywidget/`
    - Launch jupyter lab, and wait a minute or so (may take longer). You should see this message:
        - JupyterLab build is suggested: arcgis-map-ipywidget content changed
    - Press "BUILD", and wait a few minutes for the build to complete
        - You can look at the console output of the jupyterlab server instance to see any compile errors
    - If the build succeeds, the page should alert you to refresh the page.
        - If the build fails, __it won't say anything on the browser page__. You need to monitor the console output of the jupyterlab server for any errors 
    - The Jupyterlab server instance will auto-detect any changes to source code, and you will follow the same prompts as from above
- If you are modiyfing python source code, you may have to rerun  `pip install -e /path/to/geosaurus/src --no-deps` and restart the jupyter kernel

## When you're ready to merge into master

- run `yarn build`, run through all tests in geosaurus/tests/widget and assert full functionality
- Make sure all the files in `geosaurus/src/arcgis/widgets/js/dist/*` are included in your commit and gets included into master -- this is actually what the Python references when a map widget is made in a Jupyter Notebook

## Misc

- npm version >8 might be required if the installation keeps hanging
- For the `arcgis-map-ipywidget`, the default `npm install` will only build the jupyterlab extension (it does not build the notebook extension)
    - An auto-building of the lab extension is needed for how jupuyterlab handles it's extensions
