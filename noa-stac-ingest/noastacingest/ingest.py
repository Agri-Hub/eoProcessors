"""Main Ingest module."""

from __future__ import annotations
import os

from pathlib import Path
import json
import logging
import tempfile

import boto3

from pystac import Catalog, Item

from noastacingest import utils
from noastacingest.db import utils as db_utils
from noastacingest.create_item_copernicus import create_copernicus_item
from noastacingest.create_item_beyond import (
    create_wrf_item,
    create_sentinel_2_monthly_median_items,
    create_chdm_items
)


class Ingest:
    """
    A class
    """

    def __init__(
        self,
        config: str | None,
        logger=logging.getLogger(__name__)
    ) -> Ingest:
        """
        Ingest main class implementing single and batch item creation.
        """
        self.logger = logger
        self._config = {}
        with open(config, encoding="utf8") as f:
            self._config = json.load(f)
        print(self._config)
        if "https://s3" in self._config["catalog_path"]:
            s3 = boto3.resource(
                "s3",
                aws_access_key_id=os.getenv("CREODIAS_S3_ACCESS_KEY"),
                aws_secret_access_key=os.getenv("CREODIAS_S3_SECRET_KEY"),
                endpoint_url=os.getenv("CREODIAS_ENDPOINT", None),
                region_name=os.getenv("CREODIAS_REGION", None)
            )
            with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
                bucket = s3.Bucket(os.getenv("CREODIAS_S3_BUCKET_PRODUCT_OUTPUT", None))
                bucket.download_file("stac/catalog/catalog.json", tmp.name)
                self._catalog = Catalog.from_file(tmp.name)
        else:
            self._catalog = Catalog.from_file(
                Path(self._config["catalog_path"], self._config["catalog_filename"])
            )

    @property
    def config(self):
        """Get config"""
        return self._config

    def _save_item_add_to_collection(
        self,
        item: Item,
        collection: str,
        update_db: bool,
        s3=False
    ):
        item_path = (
            self._config.get("collection_path") + collection + "/items/" + item.id
        )
        # TODO throw error if collection or catalog are not in path
        json_file_path = str(Path(item_path, item.id + ".json"))
        # Catalog and Collections must exist
        item.set_root(self._catalog)

        if s3:
            s3 = boto3.client(
                's3',
                endpoint_url=os.getenv("CREODIAS_ENDPOINT", None),
                aws_access_key_id=os.getenv("CREODIAS_S3_ACCESS_KEY", None),
                aws_secret_access_key=os.getenv("CREODIAS_S3_SECRET_KEY", None)
            )

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
        if update_db:
            db_utils.load_stac_items_to_pgstac(
                [collection_instance.to_dict()], collection=True
            )

        item.set_self_href(json_file_path)
        item.save_object(include_self_link=True)
        if update_db:
            db_utils.load_stac_items_to_pgstac(
                [collection_instance.to_dict()], True
            )
            db_utils.load_stac_items_to_pgstac([item.to_dict()])
        return True

    def ingest_directory(
        self,
        input_path: Path | str,
        collection: str | None,
        update_db: bool
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
                path=input_path,
                additional_providers=additional_providers
            )
        elif collection == "chdm_s2":
            created_items = create_chdm_items(
                path=input_path,
                additional_providers=additional_providers
            )
        print("Created Item ids:")
        for item in created_items:
            result = self._save_item_add_to_collection(
                item=item,
                collection=collection,
                update_db=update_db,
                s3=True
            )
            if result:
                print(item.id)
                # append to return list??

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
            item = create_wrf_item(
                path=path,
                additional_providers=additional_providers
            )
        else:
            item = create_copernicus_item(
                path=path,
                collection=collection,
                additional_providers=additional_providers
            )
        if not item:
            self.logger.error("Could not create STAC Item")
            return False
        item.properties["noa_product_id"] = noa_product_id
        result = self._save_item_add_to_collection(
            item=item,
            collection=collection,
            update_db=update_db
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
                    raise RuntimeError(
                        "Could not create the STAC Item",
                        single_uuid
                    )
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
                len(failed_items)
            )
        except BrokenPipeError as e:
            self.logger.error("Error sending kafka message: %s", e)

        return ingested_items, failed_items
