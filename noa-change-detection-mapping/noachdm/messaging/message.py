class Message:
    """
    Defines the message.
    """

    _schema_request_def = {
        "namespace": "noa.chdm.order",
        "type": "object",
        "properties": {
            "ids_date_from": {
                "type": "array",
                "items": {
                    "type": "string",
                    "uniqueItems": True,
                }
            },
            "ids_date_to": {
                "type": "array",
                "items": {
                    "type": "string",
                    "uniqueItems": True,
                }
            },
            "bbox": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["ids_date_from", "ids_date_to", "bbox"]
    }

    _schema_response_def = {
        "namespace": "noa.chdm.response",
        "type": "object",
        "properties": {
            "chdm_product_path": {
                "type": "string",
            }
        },
        "required": ["chdm_product_path"]
    }

    @staticmethod
    def schema_request() -> dict:
        """
        Returns the Schema definition of this type.
        """
        return Message._schema_request_def

    @staticmethod
    def schema_response() -> dict:
        """
        Returns the Schema definition of this type.
        """
        return Message._schema_response_def
