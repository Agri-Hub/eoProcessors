"""Main Ingest module."""

from __future__ import annotations
import os

from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
import json
import logging

import boto3

from pystac import Catalog, Item
from pystac.layout import AsIsLayoutStrategy
from psycopg.errors import ConnectionFailure

from noastacingest import utils
from noastacingest.db import utils as db_utils
from noastacingest.create_item_copernicus import create_copernicus_item
from noastacingest.create_item_beyond import (
    create_wrf_item,
    create_sentinel_2_monthly_median_items,
    create_chdm_items,
)


class Ingest:
    """
    A class
    """

    def __init__(
        self,
        config: str | None,
        service: bool = False,
        logger=logging.getLogger(__name__),
    ) -> Ingest:
        """
        Ingest main class implementing single and batch item creation.
        """
        self.logger = logger
        self._config = {}
        self._is_service = service

        with open(config, encoding="utf8") as f:
            self._config = json.load(f)

        logger.info(" Starting service with config: %s ", self._config)

        # TODO check if is necessary to copy or just keep reference
        if "https://s3" in self._config["catalog_path"]:
            s3_client = boto3.client(
                "s3",
                endpoint_url=os.getenv("CREODIAS_ENDPOINT", None),
                aws_access_key_id=os.getenv("CREODIAS_S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("CREODIAS_S3_SECRET_KEY"),
            )
            response = s3_client.get_object(
                Bucket=os.getenv("CREODIAS_S3_BUCKET_STAC"), Key="catalog.json"
            )
            catalog_dict = json.loads(response["Body"].read())
            self._catalog = Catalog.from_dict(catalog_dict)
            self._catalog.set_self_href(
                f"{os.getenv('CREODIAS_ENDPOINT')}/{os.getenv('CREODIAS_S3_BUCKET_STAC')}/catalog.json"
            )
            self._catalog.normalize_hrefs(
                f"{os.getenv('CREODIAS_ENDPOINT')}/{os.getenv('CREODIAS_S3_BUCKET_STAC')}/catalog.json"
            )
            self._catalog.resolve_links()
        else:
            self._catalog = Catalog.from_file(
                Path(self._config["catalog_path"], self._config["catalog_filename"])
            )

    @property
    def config(self):
        """Get config"""
        return self._config

    def _save_item_add_to_collection(
        self, item: Item, collection: str, update_db: bool, s3=False
    ):
        item_path = (
            self._config.get("collection_path") + collection + "/items/" + item.id
        )
        # TODO throw error if collection or catalog are not in path
        json_file_path = item_path + "/" + item.id + ".json"
        # Catalog and Collections must exist
        item.set_root(self._catalog)

        if s3:
            collection_key = f"collections/{collection}/collection.json"
            stac_collection = utils.s3_collection_to_local(
                collection_key, self._catalog
            )
            collection_path = urlparse(stac_collection.get_self_href()).path

            item_path = PurePosixPath(collection_path).parent / "items" / item.id
            item.set_self_href(
                f"{os.getenv('CREODIAS_ENDPOINT')}"
                + str(item_path)
                + "/"
                + f"{item.id}.json"
            )
            item.set_parent(stac_collection)

            stac_collection.add_item(item, strategy=AsIsLayoutStrategy())
            stac_collection.update_extent_from_items()

            s3_client = boto3.client(
                "s3",
                endpoint_url=os.getenv("CREODIAS_ENDPOINT", None),
                aws_access_key_id=os.getenv("CREODIAS_S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("CREODIAS_S3_SECRET_KEY"),
            )
            s3_client.put_object(
                Bucket=os.getenv("CREODIAS_S3_BUCKET_STAC"),
                Key=f"collections/{collection}/items/{item.id}/{item.id}.json",
                Body=json.dumps(item.to_dict(), indent=2),
                ContentType="application/json",
            )
            s3_client.put_object(
                Bucket=os.getenv("CREODIAS_S3_BUCKET_STAC"),
                Key=f"collections/{collection}/collection.json",
                Body=json.dumps(stac_collection.to_dict(), indent=2),
                ContentType="application/json",
            )
            self.logger.info("Uploaded STAC Item: %s", item.get_self_href())
            collection_instance = stac_collection

        else:
            collection_instance = self._catalog.get_child(collection)
            item.set_collection(collection_instance)

            # TODO most providers do not have a direct collection/items relation
            # Rather, they provide an items link, where all items are present
            # e.g. https://earth-search.aws.element84.com/v1/
            # collections/sentinel-2-l2a/items
            # Like so, I do not know if an "extent" property is needed.
            # If it is, update it:
            # TODO fix spatial and temporal extent when new item is added
            collection_instance.update_extent_from_items()
            collection_instance.normalize_and_save(
                self._config.get("collection_path") + collection + "/"
            )

        if not s3:
            item.set_self_href(json_file_path)
            item.save_object(include_self_link=True)
        if update_db:
            try:
                db_utils.load_stac_items_to_pgstac(
                    [collection_instance.to_dict()], collection=True
                )
                db_utils.load_stac_items_to_pgstac([item.to_dict()])
            except ConnectionFailure:
                self.logger.error("Could not update pgSTAC")
                pass
        return True

    def ingest_directory(
        self, input_path: Path | str, collection: str | None, update_db: bool
    ) -> bool:
        # TODO create noa-product-id
        """
        Create a new Beyond STAC Item.
        Catalog and Collection must be present (paths defined in config)
        """

        if not collection:
            try:
                collection = utils.get_collection_from_path(input_path)
            except RuntimeError:
                message = """
                STAC Collection not defined or could not infer it
                from filenames in path
                """
                self.logger.error(message)
        # Additional provider for the item. Beyond host some Copernicus
        # data but also produces new products.
        additional_providers = utils.get_additional_providers(collection=collection)

        # TODO add parameters month, year or parse filenames?
        # TODO refactor so to build with factory instead of
        # multiple ifs
        created_items = set()
        if collection == "s2_monthly_median":
            created_items = create_sentinel_2_monthly_median_items(
                path=input_path, additional_providers=additional_providers
            )
        elif collection == "chdm_s2":
            created_items = create_chdm_items(
                path=input_path, additional_providers=additional_providers
            )
        print("Created Item ids:")
        # TODO is s3 true correct?
        # TODO take care of logs
        for item in created_items:
            result = self._save_item_add_to_collection(
                item=item, collection=collection, update_db=update_db, s3=True
            )
            if result:
                print(item.id)
                # append to return list??
        # TODO if s3, need to re-upload the updated collection with the new extent

    # TODO to be refactored somehow, so that name has a meaning:
    # "single item" makes sense mostly for CDSE products, where
    # a complex structure of directories makes a product.
    # In Beyond, up to now, we have some info in the filename
    # (like from-to dates), and the rest resides as logic inside
    # this processor.
    def single_item(
        self,
        path: Path,
        collection: str | None,
        update_db: bool,
        noa_product_id: str | None = None,
    ) -> bool:
        """
        Create a new STAC Item, either by ingestion of existing data or new ones.
        Copernicus products come in directories (with either SAFE or SEN3 extensions)
        Catalog and Collection must be present (paths defined in config)
        """
        # Additional provider for the item. Beyond host some Copernicus
        # data but also produces new products.
        item = {}
        additional_providers = utils.get_additional_providers(collection=collection)

        if collection == "wrf":
            item = create_wrf_item(path=path, additional_providers=additional_providers)
        else:
            item = create_copernicus_item(
                path=path,
                collection=collection,
                additional_providers=additional_providers,
            )
        if not item:
            self.logger.error("Could not create STAC Item")
            return False
        item.properties["noa_product_id"] = noa_product_id
        result = self._save_item_add_to_collection(
            item=item, collection=collection, update_db=update_db
        )
        if result:
            print(f"Created: {item.id}")
            return result
            # append to return list??

    def from_uuid_db_list(self, uuid_list, collection, db_ingest):
        """Get from products table the paths to ingest"""
        ingested_items = []
        failed_items = []
        # TODO: correct the algorithm: unite config retrieval
        db_config = db_utils.get_env_config()
        if not db_config:
            self.logger.warning(
                "Not db configuration found in env vars. Trying local file"
            )
            db_config = db_utils.get_local_config()
            if not db_config:
                self.logger.error(
                    "Not db configuration in env vars nor local database.ini file."
                )
                failed_items.append(uuid_list)
                return ingested_items, failed_items

        for single_uuid in uuid_list:
            self.logger.debug("Trying to ingest single uuid %s", single_uuid)
            item = db_utils.query_all_from_table_column_value(
                db_config, "products", "id", single_uuid
            )
            item_path = item.get("path")
            # For production the two options should be "None, True"
            try:
                result = self.single_item(
                    Path(item_path), collection, db_ingest, single_uuid
                )
                if result:
                    ingested_items.append(str(single_uuid))
                    self.logger.debug("Ingested item from %s", item_path)
                else:
                    raise RuntimeError("Could not create the STAC Item", single_uuid)
            except RuntimeError as e:
                self.logger.error(
                    "Item could not be ingested to pgSTAC: %s", str(single_uuid)
                )
                self.logger.error("Could not create STAC Item: %s", e)
                failed_items.append(str(single_uuid))
                continue

        kafka_topic = self.config.get(
            "topic_producer",
            os.environ.get("KAFKA_OUTPUT_TOPIC", "stacingest.order.completed"),
        )
        self.logger.debug("Sending message to topic %s", kafka_topic)
        try:
            bootstrap_servers = self.config.get(
                "kafka_bootstrap_servers",
                os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            )
            utils.send_kafka_message(
                bootstrap_servers, kafka_topic, ingested_items, failed_items
            )
            self.logger.info(
                "Ingested %d items (%d failed). Sending message to Kafka consumer",
                len(ingested_items),
                len(failed_items),
            )
        except BrokenPipeError as e:
            self.logger.error("Error sending kafka message: %s", e)

        return ingested_items, failed_items
