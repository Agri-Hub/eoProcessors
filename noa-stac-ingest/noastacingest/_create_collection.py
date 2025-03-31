"""
Warning! This might be a destructive action, if a Catalog/Collection
with the same name exists
"""

import os
import sys
import json
import datetime
from pathlib import Path

from pystac import (
    Catalog,
    Collection,
    Extent,
    Link,
    RelType,
    MediaType,
    Provider,
    ProviderRole,
    # CatalogType,
    SpatialExtent,
    TemporalExtent,
)
from pystac.layout import AsIsLayoutStrategy


def main(config_file):

    config = {}

    with open(config_file, encoding="utf8") as f:
        config = json.load(f)

    # Load Catalog:
    catalog = Catalog.from_file(config["catalog_path"] + config["catalog_filename"])

    # For Collection:
    now = datetime.datetime.now(datetime.timezone.utc)
    DEFAULT_EXTENT = Extent(
        SpatialExtent([[-180, -90, 180, 90]]),
        TemporalExtent([[now, now]]),
    )
    # TODO complete rest of fields like license etc
    for collection_id, collection_details in config["collections"].items():
        collection_description = collection_details["description"]

        roles = [ProviderRole.HOST]

        # TODO this is hardcoded. Can be extended through a cli command
        if collection_id == "wrf":
            roles.append(ProviderRole.PRODUCER)
        noa_provider = Provider(
            name="NOA-Beyond",
            description="National Observatory of Athens - 'Beyond' center of EO Research",
            roles=roles,
            url="https://beyond-eocenter.eu/",
        )
        # TODO for collection and items also: upgrade stac version to 1.1
        new_collection = Collection(
            id=collection_id,
            href=str(config["collection_path"] + collection_id + "/collection.json"),
            description=collection_description,
            providers=[noa_provider],
            extent=DEFAULT_EXTENT,
        )

        items_path = Path(config["collection_path"], collection_id, "items")
        if not os.path.exists(str(items_path)):
            items_path.mkdir(parents=True, exist_ok=True)
        new_collection.add_link(
            Link(
                rel=RelType.ITEMS,
                target=str(config["collection_path"] + collection_id + "/items/"),
                media_type=MediaType.JSON,
            )
        )

        new_collection.normalize_hrefs(
            str(config["collection_path"] + collection_id + "/")
        )
        new_collection.make_all_asset_hrefs_absolute()

        if not os.path.exists(
            str(config["collection_path"] + collection_id + "/collection.json")
        ):
            new_collection.save(
                dest_href=str(config["collection_path"] + collection_id)
            )

        catalog.add_link(
            Link(rel="data", target=config["collection_path"], media_type=MediaType.JSON)
        )
        catalog.add_child(
            new_collection,
            collection_description,
            AsIsLayoutStrategy(),
        )
        catalog.save()


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) != 2:
        print("Usage: python _create_collection.py <config_file_path>")
    else:
        collection_config_file = sys.argv[1]
        main(collection_config_file)
