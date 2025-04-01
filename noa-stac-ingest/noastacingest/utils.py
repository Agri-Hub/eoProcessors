"""Utility functions"""
from __future__ import annotations

import logging
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


def get_additional_providers(collection: str) -> list[Provider]:
    """
    Appending additional providers in STAC Item depending on the type
    of collection or item to be created
    """

    provider_roles = [ProviderRole.HOST]
    if collection == "wrf":
        provider_roles.append(ProviderRole.PRODUCER)

    noa_provider = Provider(
        name="NOA-Beyond",
        description="National Observatory of Athens - 'Beyond' center of EO Research",
        roles=provider_roles,
        url="https://beyond-eocenter.eu/",
    )
    return [noa_provider]
