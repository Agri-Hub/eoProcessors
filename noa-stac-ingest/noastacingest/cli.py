"""Cli for NOA-Beyond STAC Ingest processor.

This interface and processor are used to create STAC Items
from various data sources.
"""

from __future__ import annotations
import os
import sys
from time import sleep
from datetime import datetime
import json
import logging
from pathlib import Path

import click
from click import Argument, Option
from kafka import KafkaConsumer as k_KafkaConsumer
from kafka.errors import (
    NoBrokersAvailable,
    TopicAuthorizationFailedError,
    InvalidTopicError,
    UnknownTopicOrPartitionError,
    UnsupportedForMessageFormatError,
    InvalidMessageError,
)

# Appending the module path in order to have a kind of cli "dry execution"
sys.path.append(str(Path(__file__).parent / ".."))

from noastacingest import ingest  # noqa:402 pylint:disable=wrong-import-position
from noastacingest import utils  # noqa:402 pylint:disable=wrong-import-position
from noastacingest.messaging.message import (  # noqa:402 pylint:disable=wrong-import-position
    Message,
)
from noastacingest.messaging import (  # noqa:402 pylint:disable=wrong-import-position
    AbstractConsumer,
)
from noastacingest.messaging.kafka_consumer import (  # noqa:402 pylint:disable=wrong-import-position
    KafkaConsumer,
)

PROCESSOR = "[NOA-STACIngest]"


@click.group(
    help=(
        "Creates STAC Items from filename, "
        "according to parameters as defined in the [CONFIG_FILE]."
    )
)
@click.option(
    "--log",
    default="INFO",
    help="Log level (optional, e.g. DEBUG. Default is INFO)",
)
def cli(log):
    """Click cli group for query, download, describe cli commands"""
    numeric_level = getattr(logging, log.upper(), "DEBUG")
    logging.basicConfig(
        format=f"[%(asctime)s.%(msecs)03d] [%(levelname)s] {PROCESSOR} %(message)s",
        level=numeric_level,
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


# TODO refactor so function name and command to show that it is
# CDSE specific
@cli.command(help="Create STAC Item from S1-S2 SAFE paths")
@click.argument("input_path", required=True)
@click.argument("config", required=True)
@click.option("--collection", "-c", help="Collection for item(s) to be child of")
@click.option(
    "--recursive", "-r", is_flag=True, help="Ingest all (SAFE) directories under path"
)
@click.option(
    "--update_db",
    "-udb",
    is_flag=True,
    help="Update STAC db, ingesting(upsert) new items",
)
def create_item_from_path(
    input_path: Argument | str,
    config: Argument | str,
    collection: Option | str | None,
    recursive: Option | bool,
    update_db: Option | bool,
) -> None:
    """
    Instantiate Ingest Class and call "create_item"

    Parameters:
        input (click.Argument | str): Input filename path
        config_file (click.Argument | str) - optional: config json file
            selecting file types etc
        collection (click.Option | str | None): Collection id of which the new Item will be an Item of
        recursive (click.Option | bool): To ingest all (SAFE) directories under input (for multiple item creation)
        update_db (click.Option | bool): Update pgstac for new items, using upsert. It also updates the collections
    """
    # TODO This is Sentinel specific. It searches for directories (SAFE or otherwise)
    # For Beyond items, we need a generalization or a different function
    # TODO needs refactor. Updating/creating items can be done in batches, (e.g in db)
    logger = logging.getLogger(__name__)
    logger.info("Cli STAC ingest using config file: %s", config)
    ingestor = ingest.Ingest(config=config, service=False, logger=logger)

    if recursive:
        click.echo(f"Ingesting items recursively from path {input_path}\n")
        for single_item in os.listdir(input_path):
            item = Path(input_path, single_item)
            if item.is_dir():
                ingestor.single_item(item, collection, update_db)
    else:
        click.echo(f"Ingesting single item from {input_path}\n")
        ingestor.single_item(Path(input_path), collection, update_db)


@cli.command(help="Create STAC Item(s) from a directory. Only supports Beyond products")
@click.argument("input_path", required=True)
@click.argument("config", required=True)
@click.option("--collection", "-c", help="Collection for item(s) to be child of")
@click.option(
    "--recursive", "-r", is_flag=True, help="Ingest all directories under path"
)
@click.option(
    "--update_db",
    "-udb",
    is_flag=True,
    help="Update STAC db, ingesting(upsert) new items",
)
def ingest_from_path(
    input_path: Argument | str,
    config: Argument | str,
    collection: Option | str | None,
    recursive: Option | bool,
    update_db: Option | bool,
) -> None:
    """
    Instantiate Ingest Class and call parse directory for items

    Parameters:
        input (click.Argument | str): Input path
        config_file (click.Argument | str) - optional: config json file
            selecting file types etc
        collection (click.Option | str | None): Collection id of which the new Item(s) will be an Item of
        recursive (click.Option | bool): Walk path to ingest all items from subdirs
        update_db (click.Option | bool): Update pgstac for new items, using upsert. It also updates the collections
    """
    # TODO Beyond items specific. We need a generalization for all (if possible)
    # TODO needs refactor. Updating/creating items can be done in batches, (e.g in db)
    logger = logging.getLogger(__name__)
    logger.info("Cli STAC ingest using config file: %s", config)
    ingestor = ingest.Ingest(config=config, service=False, logger=logger)

    if recursive:
        click.echo(f"Ingesting items recursively from path {input_path}\n")
        for single_directory in [f.path for f in os.scandir(input_path) if f.is_dir()]:
            ingest_from_path(
                input_path=single_directory,
                config=config,
                collection=collection,
                recursive=True,
                update_db=update_db,
            )
    ingestor.ingest_directory(Path(input_path), collection, update_db)


@cli.command(
    help=(
        """
        Microservice facilitating EO data STAC db ingestion.
        Implemented using a kafka producer/consumer pattern.
        """
    )
)
@click.option(
    "--test",
    "-t",
    is_flag=True,
    help="Testing kafka receiving requests. No other functionality",
)
@click.option(
    "--db_ingest",
    "-db",
    is_flag=True,
    help="Ingesting to pgSTAC, not only creating STAC Items. Should be enabled",
)
@click.option(
    "--collection",
    "-col",
    help="""
        Explicit collection name to ingest to.
        If not set, ingestor will try to derive it from path name
    """,
)
@click.argument("config_file", required=True)
def noa_stac_ingest_service(
    config_file: Argument | str,
    collection: Option | str,
    test: Option | bool,
    db_ingest: Option | bool,
) -> None:
    """
    Instantiate Ingest class, activating service, listening to kafka topic.
    When triggered, it creates, stores and populates pgstac with Items,
    looking for input paths from ids from Products table,
    based on the list argument from kafka message.

    Parameters:
        config_file (click.Argument | str): config file with necessary parameters
        collection (click.Option | str): Ingest to specific collection
        test (click.Option | bool): for kafka testing purposes
        db_ingest (click.Option | bool): Ingest Item to db. Set to true for production
    """
    # if config_file:
    logger = logging.getLogger(__name__)
    logger.debug("Starting NOA-STAC-Ingest service...")

    ingestor = ingest.Ingest(config=config_file, service=True, logger=logger)

    # test: product_path = "https://s3.waw4-1.cloudferro.com/noa/products/20250611/"
    # ingestor.ingest_directory(product_path, None, db_ingest)

    # Consumer
    consumer: AbstractConsumer | k_KafkaConsumer = None
    # Warning: topics is a list, even if there is only one topic
    # So it should be defined as a list in the config json file
    consumer_topics = ingestor.config.get(
        "topics_consumer",
        os.environ.get("KAFKA_INPUT_TOPICS", ["noa.stacingest.request"]),
    )
    schema_def = Message.schema_request()
    consumer_bootstrap_servers = ingestor.config.get(
        "kafka_bootstrap_servers",
        (os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")),
    )
    kafka_group_id = ingestor.config.get(
        "kafka_request_group_id",
        (os.getenv("KAFKA_REQUEST_GROUP_ID", "stacingest-group-request")),
    )

    # Producer
    producer_bootstrap_servers = ingestor.config.get(
        "kafka_bootstrap_servers",
        os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    )

    producer_topic = ingestor.config.get(
        "topic_producer", os.environ.get("KAFKA_OUTPUT_TOPIC", "noa.stacingest.response")
    )

    retries = 0
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=consumer_bootstrap_servers,
                group_id=kafka_group_id,
                topics=consumer_topics,
                schema=schema_def,
            )
            consumer.subscribe_to_topics(consumer_topics)
        except NoBrokersAvailable as e:
            logger.error(
                "Kafka configuration error, no brokers available for (%s) : %s ",
                consumer_bootstrap_servers,
                e,
            )
            raise
        except (
            UnknownTopicOrPartitionError,
            TopicAuthorizationFailedError,
            InvalidTopicError,
        ) as e:
            if retries < 5:
                logger.warning("Could not subscribe to Topic(s): %s", consumer_topics)
                if consumer is None:
                    sleep(5)
                    retries += 1
                    continue
            else:
                logger.error(
                    "Kafka Error on Topic subscription after %i retries: %s", retries, e
                )

    logger.info("Service started, subscribed to topics %s", consumer_topics)

    while True:
        try:
            for message in consumer.read():
                result = 0
                item = message.value
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"Digesting Item from Topic {message.topic} ({now_time})..."
                msg += "\n> Item: " + json.dumps(item)
                logger.debug("Kafka message: %s", msg)
                logger.info("Received list to ingest: %s", item)
                if test:
                    ingested = "Some ingested ids"
                    failed = "Some failed to ingest ids"
                else:
                    # TODO priority refactor: need to connect to db
                    # to check paths. This is only for S2 and that's an
                    # ugly way to do it. Messages should have the same
                    # structure and ingestion should be agnostic of
                    # underlying infra dbs (except pgSTAC of course)
                    if "Ids" in item:
                        uuid_list = item["Ids"]
                        ingested, failed = ingestor.from_uuid_db_list(
                            uuid_list, collection, db_ingest
                        )
                        logger.debug("Ingested items: %s", ingested)
                        if failed:
                            logger.error("Failed uuids: %s", failed)
                    elif "noaS3Path" in item:
                        # NOTE this s3 path is mounted. We run on Cloudferro
                        # Run either as mounted or s3 directly
                        # TODO pass through NOAId and return orderId
                        # TODO refactor: kafka response sent at cli level
                        product_paths = item["noaS3Path"]
                        order_id = item["orderId"]
                        for product_path in product_paths:
                            ingestor.ingest_directory(product_path, None, db_ingest)
                        try:
                            result = 0
                            # TODO, also this: we should have one message schema
                            # for response
                            utils.send_kafka_message_chdm(
                                producer_bootstrap_servers,
                                producer_topic,
                                order_id,
                                result
                            )
                            logger.info(
                                "Sending message to Kafka consumer. %s %s",
                                order_id,
                                result,
                            )
                        except BrokenPipeError as e:
                            logger.error("Error sending kafka message: %s", e)
            sleep(1)
        except (UnsupportedForMessageFormatError, InvalidMessageError) as e:
            logger.error("Error in STAC ingestion: %s", e)
            continue


if __name__ == "__main__":  # pragma: no cover
    cli()
