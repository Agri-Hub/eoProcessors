# NOA STAC Ingest processor

Ingest geospatial data, by creating STAC Items according to the STAC 1.0.0 and 1.1.0 Specifications
https://github.com/radiantearth/stac-spec


## Initial steps

Please make sure that for the service and full functionality, you have a working pgSTAC instance and a valid Catalog STAC path. If in dev mode or a static STAC Catalog, use the helper scripts.
This processor initially creates a STAC json for every Item and then populates the pgSTAC instance if available. In order to do so, the Items are related to a parent Collection which is also a child of a Catalog.

As noted before, in case you are starting fresh, there are two helper files in order to create an initial
Catalog and an initial Collection under that Catalog:

```
noa-stac-ingest/noastacingest/_create_catalog.py
noa-stac-ingest/noastacingest/_create_collection.py
```

Regarding the pgSTAC db, the processor will try to retrieve connection credentials from
these environmental variables:

```
STACDB_ADMIN_USERNAME
STACDB_ADMIN_PASSWORD
STACDB_URI (ip:port)
STACDB_DBNAME
```

## How to use as a service, consuming/producing from/to kafka, and ingesting to pgSTAC

- Build docker image (Dockerfile or compose)  
- Execute the following snippet, and please mind the config file. If no changes are needed, **do not mount** the config. However,
- **Do** include the config file as a cli argument.
- Also, check the fs mounts (mount the _root_ folder of products and STAC files)
- Please note that this service works for ingesting Sentinel 1,2 and 3 SAFE (or SEN3) directories, and also for some Beyond products: ChDM and CFM (ask infrastructure.beyond at noa dot gr for more info)

**NOTES FOR S3 (Items and STAC Collections)**
- Service is the same. Ingestion is decided based on the incoming kafka message **path**
- Please note to use **config_service_s3.json** if you are using an s3 instead of cluster mounts.
- Processor needs the following env vars (aside from STAC_DB creds as noted before):
CREODIAS_S3_ACCESS_KEY=***
CREODIAS_S3_SECRET_KEY=***
CREODIAS_REGION=WAW4-1
CREODIAS_ENDPOINT=https://s3.waw4-1.cloudferro.com
CREODIAS_S3_BUCKET_PRODUCT_OUTPUT=noa
CREODIAS_S3_BUCKET_STAC=stac

```
docker run -it \
-v ./config/config_service**_s3**.json:/app/config/config_service**_s3**.json \
-v /mnt/data/poc/:/mnt/data/poc/ \
noastacingest noa-stac-ingest-service -db config/config_service**_s3**.json
```

Also mind any port forwarding needed for kafka or pgSTAC.
Please note that you can use the -t flag instead of -db in order to check kafka communication,
and have in mind that by using -db, pgSTAC will be populated (production mode)

## DB Considerations for uuid list download

Please note that for uuid path extraction, for now, a postgres db is required.
You can provide credentials either by having set up env vars or by filling up the `database.ini` file under db folder.
The necessary env vars are:
`DB_USER`
`DB_PASSWORD`
`DB_HOST`
`DB_PORT`
`DB_NAME`
