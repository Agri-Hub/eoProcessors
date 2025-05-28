from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json


class SearchViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("search")

    @patch("requests.post")
    def test_search_with_sentinel_2(self, mock_post):

        mock_response = MagicMock()

        mock_response.json.return_value = {"message": "success", "data": []}

        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        data = {
            "data_source": "Sentinel-2",
            "start_date": "2024-12-01",
            "end_date": "2024-12-13",
            "bbox": "10,20,30,40",
            "cloud_coverage": "20",
        }

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 200)

        response_data = response.json()

        self.assertIn("data", response_data)
        self.assertEqual(response_data["message"], "success")

        expected_payload = {
            "provider": 2,
            "startDate": "2024-12-01T00:00:00.000",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [10.0, 20.0],
                        [30.0, 20.0],
                        [30.0, 40.0],
                        [10.0, 40.0],
                        [10.0, 20.0],
                    ]
                ],
            },
            "properties": {"cloudCoverage": "20"},
        }

        mock_post.assert_called_once_with(
            "http://10.201.40.192:30080/api/SatelliteProduct/GetAll/SatelliteProduct",
            json=expected_payload,
            verify=False,
        )

    @patch("requests.post")
    def test_search_with_invalid_data_source(self, mock_post):
        data = {
            "data_source": "UnknownSource",
            "start_date": "2024-12-01",
            "bbox": "10,20,30,40",
        }

        response = self.client.post(self.url, data=data)

        self.assertEqual(response.status_code, 400)

        response_data = response.json()

        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"], "Invalid data source")

        mock_post.assert_not_called()
