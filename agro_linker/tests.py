# # tests/test_api.py
# from ninja.testing import TestClient
# from agro_linker.api.api import api

# client = TestClient(api, urls_namespace="test_api")

# def test_product_list():
#     response = client.get("/market/products")
#     assert response.status_code == 200
#     assert len(response.json()) > 0