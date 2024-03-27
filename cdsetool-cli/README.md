# Using the CDSETOOL cli processor
The cdsetool processor can be executed as a standalone cli application or inside a container. The following instructions are container specific. If you want to execute the cli in your local environment, skip all docker commands and just execute `python cli.py -d -v config.json`. Please note that in that case, the Copernicus credentials must be present in the environment variables (`login`, `password`) or in the `~/.netrc` file in Linux.


## Prerequisites
### Common for all platforms

* Required hub registrations:
  * **Copernicus, Sentinel data (Sentinel 1,2 ...)**
    Users must be registered with the Copernicus Dataspace Eco System to access and download the data. Registration is free and can be completed on the Copernicus Dataspace Eco System (https://dataspace.copernicus.eu/).

* Install
    * Docker: https://docs.docker.com/get-docker/
    * Git:  https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

## Next steps

* Open a terminal window and navigate to your prefered working directory and download the source code:

```
git clone https://github.com/Agri-Hub/eoProcessors.git
```

* Navigate to the folder and build the image:

```
cd eoProcessors/cdsetool-cli
docker build -t cdsetool-cli .
```

* Edit `.env.list` file, and introduce the `login` and `password` of your Copernicus registration from the first step

* Edit `config.json` found in the config folder (or create a new one), to introduce the query parameters for downloading the data. Please note that you can include more than one satellites.

* Execute:

```
docker run -it \
-v [./data]:/app/data \
-v [./config/config.json]:/app/config/config.json \
--env-file .env.list \
cdsetool-cli -d -v config.json
```

Please note that in the aforementioned command you can replace:
    * `[./data]` with the folder where the downloaded data will be stored
    * `[./config/config.json]` with the location of your configuration file. If you have edited the already present config file, leave it as is is.

E.g. you can also execute: 
```
docker run -it \
-v ./data/this_date:/app/data \
-v ./config/config_for_december.json:/app/config/config.json \
--env-file .env.list \
cdsetool-cli -d -v config.json
```

## Config file parameters
Take a look at the sample config.json. 
```
{
    "Sentinel1": {
        "maxRecords": "100",
        "startDate": "2024-01-06",
        "completionDate": "2024-01-30",
        "box": "24.15943,38.50005,24.24733,38.55608"
    },
    "Sentinel2": {
        ....
    }        
}
```
As a top level key, you have to introduce the Satellite name. Copernicus can be queried for the following Satellites: 

    Sentinel1 
    Sentinel2 
    Sentinel3 
    Sentinel5P
    Sentinel6
    Sentinel1RTC (Sentinel-1 Radiometric Terrain Corrected)

and also for these complementary data:


    GLOBAL-MOSAICS (Sentinel-1 and Sentinel-2 Global Mosaics)
    SMOS (Soil Moisture and Ocean Salinity)
    ENVISAT (ENVISAT- Medium Resolution Imaging Spectrometer - MERIS)
    LANDSAT-5
    LANDSAT-7
    LANDSAT-8
    COP-DEM (Copernicus DEM)
    TERRAAQUA (Terra MODIS and Aqua MODIS)
    S2GLC (S2GLC 2017)

You can check the available query fields per Satellite from the cli option `-p`, as described in the following section.  

## Cli options
Cli can be executed with the following flags:
* `-d`, `--download` The main option. Downloads according with the config file parameters
* `-p`, `--parameters` Returns the available query parameters, for the Satellites present in the config file top level keys
* `-v`, `--verbose` Shows the progress indicator when downloading

Examples:
* Show available query parameters for Satellites as defined in the config file:

```
docker run -it \
-v ./config/config.json:/app/config/config.json \
--env-file .env.list \
cdsetool-cli -p config.json
```


## Tests

**TODO:**

```
docker run --env-file .env.list cdsetool sh -c "python -m unittest -v ./tests/test*"
```