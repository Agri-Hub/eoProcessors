"""Main Ingest module."""

from __future__ import annotations
import os

from pathlib import Path
import json
import logging

from stactools.sentinel1.grd.stac import create_item as create_item_s1_grd
from stactools.sentinel1.rtc.stac import create_item as create_item_s1_rtc
from stactools.sentinel1.slc.stac import create_item as create_item_s1_slc
from stactools.sentinel2.commands import create_item as create_item_s2
from stactools.sentinel3.commands import create_item as create_item_s3

from pystac import Catalog, Provider, ProviderRole

from noastacingest import utils
from noastacingest.db import utils as db_utils


FILETYPES = ("SAFE", "SEN3")
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

    def single_item(
        self,
        path: Path,
        collection: str | None,
        update_db: bool,
        noa_product_id: str | None = None,
    ):
        """
        Just an item
        """
        # TODO: provide more provider roles when "processor"
        noa_provider = Provider(
            name="NOA-Beyond",
            description="""
                National Observatory of Athens - 'Beyond' center of EO Research
            """,
            roles=ProviderRole.HOST,
            url="https://beyond-eocenter.eu/",
        )
        additional_providers = [noa_provider]

        if path.name.endswith(FILETYPES):
            platform = str(path.name).split("_", maxsplit=1)[0]
            satellite = platform[:2]
            item = {}
            match satellite:
                case "S1":
                    sensor = str(path.name).split("_")[:3]
                    match sensor:
                        case "GRD":
                            item = create_item_s1_grd(str(path))
                            if not collection:
                                collection = "sentinel1-grd"
                        case "RTC":
                            item = create_item_s1_rtc(
                                granule_href=str(path),
                                additional_providers=additional_providers,
                            )
                            if not collection:
                                collection = "sentinel1-rtc"
                        case "SLC":
                            item = create_item_s1_slc(str(path))
                            if not collection:
                                collection = "sentinel1-slc"
                case "S2":
                    item = create_item_s2(
                        granule_href=str(path),
                        additional_providers=additional_providers,
                    )
                    if not collection:
                        collection = "sentinel2-l2a"
                case "S3":
                    item = create_item_s3(str(path))
                    if not collection:
                        collection = "sentinel3"
            item.properties["noa_product_id"] = noa_product_id
            item_path = (
                self._config.get("collection_path") + collection + "/items/" + item.id
            )
            json_file_path = str(Path(item_path, item.id + ".json"))
            print(json_file_path)

            # TODO add to item:
            # feature_collection = {
            #     "type": "FeatureCollection",
            #     "features": [
            #          item.to_dict() for item in collection_instance.get_all_items()
            #     ]
            # }
            if collection:
                item.set_root(self._catalog)
                collection_instance = self._catalog.get_child(collection)
                item.set_collection(collection_instance)
                # TODO most providers do not have a direct collection/items relation
                # Rather, they provide an items link, where all items are present
                # e.g. https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items
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

    def from_uuid_db_list(self, uuid_list, collection, db_ingest):
        """Get from products table the paths to ingest"""
        ingested_items = []
        failed_items = []
        # TODO: this looks at S2 table config
        # TODO: correct the algorithm: unite config retrieval
        db_config = db_utils.get_env_config()
        if not db_config:
            logger.warning(
                "Not db configuration found in env vars. Trying local file"
            )
            db_config = db_utils.get_local_config()
            if not db_config:
                print("[NOA-STACIngest] ERROR - no db config")
                logger.error(
                    "[NOA-STACIngest] Not db configuration found, in env vars nor local database.ini file."
                )
                failed_items.append(uuid_list)
                return ingested_items, failed_items

        for single_uuid in uuid_list:
            logger.warning("[NOA-STACIngest | WARNING] Trying to ingest single uuid %s", single_uuid)
            item = db_utils.query_all_from_table_column_value(
                db_config, "products", "id", single_uuid
            )
            item_path = item.get("path")
            # For production the two options should be "None, True"
            try:
                self.single_item(
                    Path(item_path), collection, db_ingest, single_uuid
                )
                ingested_items.append(str(single_uuid))
                print(f"Ingested from {item_path}")
            except RuntimeWarning:
                logger.warning(
                    "Item could not be ingested to pgSTAC: %s", str(single_uuid)
                )
                failed_items.append(str(single_uuid))
                continue

        kafka_topic = self.config.get(
            "topic_producer",
            os.environ.get("KAFKA_OUTPUT_TOPIC", "stacingest.order.completed"),
        )
        logger.warning("[NOA-STACIngest | WARNING] Sending message to topic %s", kafka_topic)
        try:
            bootstrap_servers = self.config.get(
                "kafka_bootstrap_servers",
                os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            )
            utils.send_kafka_message(
                bootstrap_servers, kafka_topic, ingested_items, failed_items
            )
            logger.info("Kafka message sent")
        except BrokenPipeError as e:
            logger.error("Error sending kafka message: %s", e)

        return ingested_items, failed_items
