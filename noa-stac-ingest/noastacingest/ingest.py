"""Main Ingest module."""

from __future__ import annotations
import os

from pathlib import Path
import json
import logging

from pystac import Catalog

from noastacingest import utils
from noastacingest.db import utils as db_utils
from noastacingest.create_item_copernicus import create_copernicus_item
from noastacingest.create_item_beyond import (
    create_wrf_item,
    create_sentinel_2_monthly_median_items
)


logger = logging.getLogger(__name__)


class Ingest:
    """
    A class
    """

    def __init__(self, config: str | None) -> Ingest:
        """
        Ingest main class implementing single and batch item creation.
        """
        self._config = {}
        with open(config, encoding="utf8") as f:
            self._config = json.load(f)
        print(self._config)

        self._catalog = Catalog.from_file(
            Path(self._config["catalog_path"], self._config["catalog_filename"])
        )

    @property
    def config(self):
        """Get config"""
        return self._config

    def ingest_directory(
        self,
        input_path: Path,
        collection: str | None,
        update_db: bool
    ) -> bool:
        # TODO create noa-product-id
        """
        Create a new Beyond STAC Item.
        Catalog and Collection must be present (paths defined in config)
        """
        # Additional provider for the item. Beyond host some Copernicus
        # data but also produces new products.
        additional_providers = utils.get_additional_providers(collection=collection)

        # TODO add parameters month, year or parse filenames?
        if collection == "s2_monthly_median":
            # TODO to be called in other place. Single item makes sense for
            # SAFE or in general Copernicus directories.
            # In Beyond, for now we do not have "manifests"
            # So, refactor following function, to crawl directory, as the internals
            # of the function actually do
            created_items = create_sentinel_2_monthly_median_items(
                path=input_path,
                additional_providers=additional_providers
            )
        print("Created Item ids:")
        for item in created_items:
            print(item.id)
        for item in created_items:
            item_path = (
                self._config.get("collection_path") + collection + "/items/" + item.id
            )
            # TODO throw error if collection or catalog are not in path
            json_file_path = str(Path(item_path, item.id + ".json"))
            print(json_file_path)
            # Catalog and Collections must exist
            item.set_root(self._catalog)
            collection_instance = self._catalog.get_child(collection)
            item.set_collection(collection_instance)
            # TODO most providers do not have a direct collection/items relation
            # Rather, they provide an items link, where all items are present
            # e.g. https://earth-search.aws.element84.com/v1/
            # collections/sentinel-2-l2a/items
            # Like so, I do not know if an "extent" property is needed.
            # If it is, update it:
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
            logger.error("Could not create STAC Item")
            return False
        item.properties["noa_product_id"] = noa_product_id
        item_path = (
            self._config.get("collection_path") + collection + "/items/" + item.id
        )
        # TODO throw error if collection or catalog are not in path
        json_file_path = str(Path(item_path, item.id + ".json"))
        print(json_file_path)

        # TODO?? add to item??:
        # feature_collection = {
        #     "type": "FeatureCollection",
        #     "features": [
        #          item.to_dict() for item in collection_instance.get_all_items()
        #     ]
        # }

        # Catalog and Collections must exist
        item.set_root(self._catalog)
        collection_instance = self._catalog.get_child(collection)
        item.set_collection(collection_instance)
        # TODO most providers do not have a direct collection/items relation
        # Rather, they provide an items link, where all items are present
        # e.g. https://earth-search.aws.element84.com/v1/
        # collections/sentinel-2-l2a/items
        # Like so, I do not know if an "extent" property is needed.
        # If it is, update it:
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

    def from_uuid_db_list(self, uuid_list, collection, db_ingest):
        """Get from products table the paths to ingest"""
        ingested_items = []
        failed_items = []
        # TODO: correct the algorithm: unite config retrieval
        db_config = db_utils.get_env_config()
        if not db_config:
            logger.warning(
                "Not db configuration found in env vars. Trying local file"
            )
            db_config = db_utils.get_local_config()
            if not db_config:
                logger.error(
                    "Not db configuration in env vars nor local database.ini file."
                )
                failed_items.append(uuid_list)
                return ingested_items, failed_items

        for single_uuid in uuid_list:
            logger.debug("Trying to ingest single uuid %s", single_uuid)
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
                    logger.debug("Ingested item from %s", item_path)
                else:
                    raise RuntimeError(
                        "Could not create the STAC Item",
                        single_uuid
                    )
            except RuntimeError as e:
                logger.error(
                    "Item could not be ingested to pgSTAC: %s", str(single_uuid)
                )
                logger.error("Could not create STAC Item: %s", e)
                failed_items.append(str(single_uuid))
                continue

        kafka_topic = self.config.get(
            "topic_producer",
            os.environ.get("KAFKA_OUTPUT_TOPIC", "stacingest.order.completed"),
        )
        logger.debug("Sending message to topic %s", kafka_topic)
        try:
            bootstrap_servers = self.config.get(
                "kafka_bootstrap_servers",
                os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            )
            utils.send_kafka_message(
                bootstrap_servers, kafka_topic, ingested_items, failed_items
            )
            logger.info(
                "Ingested %d items (%d failed). Sending message to Kafka consumer",
                len(ingested_items),
                len(failed_items)
            )
        except BrokenPipeError as e:
            logger.error("Error sending kafka message: %s", e)

        return ingested_items, failed_items
