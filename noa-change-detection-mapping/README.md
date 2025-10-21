# NOA Change Detection Mapping (NOAChDM) processor

This processor lorem ipsum

## Using the processor

The NOAChDM processor can be executed as:
- Standalone [**Cli application**](#standalone-cli-execution) or
- Inside a [**Container**](#docker-execution)
- As a container, inside a Kubernetes environment with kafka, with a postgres database. This is a Beyond specific setup, where a user can instantiate NOAChDM and request the production of a single product.
- As a microservice inside a Kubernetes environment with kafka, with a postgres database. Same as above, but now it can be deployed as a service: Product Generation as a Service (PGaaS). The output is stored in an (envvar) s3 bucket. Please find info for that in section [PGaaS](#pgaas)

## Standalone CLI execution

1. Use your favorite flavor of virtual environment, e.g. conda:
    - Create/activate the environment:
        - Execute `conda create -n noa-chdm python==3.11.14`
        - Execute `conda activate noa-chdm`
2. Then:

```
    cd eoProcessors/noa-change-detection-mapping
```
and install necessary requirements inside your virtual environment:
```
pip install -r requirements.txt
```

3. You are ready to execute the cli script:

```
python noachdm/cli.py [command] [config/config_service.json] (config valid for PGaaS only)
```

Available commands are:

 - `produce` - Local execution
 - `noa_pgaas_chdm` - Product Generation as a Service (PGaaS)

### Config file for PGaaS
The config file *should* be placed inside `eoProcessors/noa-change-detection-mapping/config`, but of course you could use any path.
Please check the [Config](#Config-file-parameters) section regarding config file specification.

## Docker execution

1. Install Docker: https://docs.docker.com/get-docker/
2. Navigate to the folder 
```
    cd eoProcessors/noa-change-detection-mapping
```
3. Then:

```
docker build -t noa-chdm .
```

4. (PGaaS only) Edit `config/config_service.json` (or create a new one)

5. Execute:

5.1

    ```
    docker run -it \
    -v [./data]:/app/data \
    --entrypoint /bin/bash \
    noa-chdm
    ```

to enter into the container and execute the cli application from there:
`python noachdm/cli.py produce -v [from_path] [to_path]`


5.2 Execute the command leaving the container when the command is completed:

```
docker run -it \
-v [./data]:/app/data \
noa-chdm produce -v [from_path] [to_path]
```

### PGaaS
This is a microservice which reads kafka messages for eoPaths containing the input items, and outputs the result in an s3 bucket.
**5.3 Run service:**
**5.3.1 Env vars**
You need to provide the following ENV variables:

```
CREODIAS_S3_ACCESS_KEY=NONE
CREODIAS_S3_SECRET_KEY=NONE
CREODIAS_REGION=WAW4-1
CREODIAS_ENDPOINT=https://s3.waw4-1.cloudferro.com
CREODIAS_S3_BUCKET_PRODUCT_OUTPUT=noa
```

As you can see there are some default vars for endpoints and bucket.
Please setup accordingly

---

**5.3.2 Execute**

```
docker run -it \
-v [./data]:/app/data \
-v [./config/config_service.json]:/app/config/config_service.json \
noa-chdm noa-pgaas-chdm -v config/config_service.json
```

Also note that the PGaaS listens on the `noa.chdm.request` kafka topic and replies to the `noa.chdm.response` kafka topic.

Please note that in the aforementioned commands you can replace:
    * `[./data]` with the folder where the downloaded data will be stored. The default location is "./data"
    * `[./config/config_service.json]` with the local location of your configuration file. In that way you will use the local edited file instead of the container one. If you have edited the already present config file before building the container, leave it as is is.

## Config file parameters

Take a look at the sample config.json. 
```
[
    {
        ...
    }
]
```

## Cli options

Cli can be executed with the following:

- Commands
    * `produce` - Produce change detection mapping from `[from_path]` rasters to `[to_path]` rasters.
    * `noa-pgaas-chdm` - PGaaS. Listen to kafka topics for orders.
- Options
    * `--output_path` Custom download location. Default is `.data`
    * `-v`, `--verbose` Shows the verbose output
    * `--log LEVEL (INFO, DEBUG, WARNING, ERROR)` Shows the logs depending on the selected `LEVEL`
- Arguments
    * `from_path` - Necessary argument for the produce command, indicating "from" date
    * `to_path` - Necessary argument for the produce command, indicating "to" date
    * `config_file` - Necessary argument for PGaaS, indicating which config file will be used.

## Examples

## Tests

Execute 
```
pytest .
```
on  `eoProcessors/noa-change-detection-mapping`  folder

or

```
docker run -it --entrypoint pytest noa-chdm
```

for the container
