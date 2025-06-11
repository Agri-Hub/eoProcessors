"""Utility functions"""
from __future__ import annotations

import logging
from pathlib import Path
from kafka.errors import NoBrokersAvailable

from pystac import Provider, ProviderRole

from noastacingest.messaging.kafka_producer import KafkaProducer
from noastacingest.messaging.message import Message

logger = logging.getLogger(__name__)


def send_kafka_message(bootstrap_servers, topic, succeeded, failed):
    schema_def = Message.schema_response()

    try:
        producer = KafkaProducer(bootstrap_servers=bootstrap_servers, schema=schema_def)
        kafka_message = {"succeeded": succeeded, "failed": failed}
        producer.send(topic=topic, value=kafka_message)
    except NoBrokersAvailable as e:
        logger.warning("No brokers available. Continuing without Kafka. Error: %s", e)
        producer = None


def send_kafka_message_chdm(bootstrap_servers, topic, orderId, result):
    schema_def = Message.schema_response_chdm()

    try:
        producer = KafkaProducer(bootstrap_servers=bootstrap_servers, schema=schema_def)
        kafka_message = {"orderId": orderId, "result": result}
        producer.send(topic=topic, key=None, value=kafka_message)
    except NoBrokersAvailable as e:
        logger.warning("No brokers available. Continuing without Kafka. Error: %s", e)
        producer = None


def get_additional_providers(collection: str) -> list[Provider]:
    """
    Appending additional providers in STAC Item depending on the type
    of collection or item to be created
    """

    provider_roles = [ProviderRole.HOST]
    if collection == "wrf" or collection == "s2_monthly_median":
        provider_roles.append(ProviderRole.PRODUCER)

    noa_provider = Provider(
        name="NOA-Beyond",
        description="National Observatory of Athens - 'Beyond' center of EO Research",
        roles=provider_roles,
        url="https://beyond-eocenter.eu/",
    )
    return [noa_provider]


def get_collection_from_path(pathname: Path | str) -> str:
    """
    Infer the STAC Collection name from a file in pathname.
    This is Beyond specific: a contract and a name convention
    """
    collection = None
    if type(pathname) is str and "s3://" in pathname:
        if "ChDM_S2" in pathname:
            collection = "chdm_s2"
        elif "CFM" in pathname:
            collection = "s2_monthly_median"
        return collection
    else:
        for filename in pathname.iterdir():
            if not filename.is_file():
                continue
            if "ChDM_S2" in filename.name:
                collection = "chdm_s2"
                break
            if "CFM" in filename.name:
                collection = "s2_monthly_median"
                break
        return collection
