"""
Simple kafka producer schema
"""

import json
import logging
from kafka import KafkaConsumer as k_KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic

from noastacingest import messaging as noa_messaging


class KafkaConsumer(noa_messaging.AbstractConsumer):
    """
    Kafka Consumer using https://kafka-python.readthedocs.io/ with JSON deserialization.
    """

    def __init__(
        self, bootstrap_servers: list, group_id: str, topics: list, schema: dict
    ) -> k_KafkaConsumer:
        """
        Create the Consumer instance.
        """
        super(KafkaConsumer, self).__init__(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            topics=topics,
            schema=schema,
        )
        self.consumer = k_KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            # auto_offset_reset="earliest",
            max_poll_interval_ms=1200000,
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )

    def subscribe_to_topics(self, topics: list):
        self.consumer.subscribe(topics=topics)

    def create_topics(
        self, topics: list, num_partitions: int = 2, replication_factor: int = 1
    ):
        """
        Create the specified list of Topics.
        """
        admin_client = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
        topic_list = []

        new_topics = set(topics) - set(self.consumer.topics())
        for topic in new_topics:
            try:
                t = NewTopic(
                    name=topic,
                    num_partitions=num_partitions,
                    replication_factor=replication_factor,
                )
                admin_client.create_topics(new_topics=[t], validate_only=False)
                topic_list.append(t)
            # Ignore the error when the Topic already exists.
            except RuntimeWarning:
                logging.warning("Topic %s exists. Just a warning", topic)
                continue

        return topic_list

    def read(self):
        """
        Read messages from the configured Kafka Topics.
        """
        yield from self.consumer
