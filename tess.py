import requests

from settings import settings

response = requests.get(f"{settings.HOST}/api/v1/products/").json()

print(response)
