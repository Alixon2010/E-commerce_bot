import requests
from requests import Response


async def request_post(url, auth_token=None, **kwargs) -> Response:
    headers = {
        "Content-Type": "application/json",
    }
    if auth_token is not None:
        headers["Authorization"] = f"Bearer {auth_token}"

    data = {**kwargs}

    return requests.post(url, json=data, headers=headers)


async def request_get(url, auth_token=None) -> Response:
    if auth_token is not None:
        headers = {
            "Authorization": f"Bearer {auth_token}",
        }
        return requests.get(url, headers=headers)

    return requests.get(url)


async def request_delete(url: str, auth_token: str | None = None) -> Response:
    if auth_token is not None:
        headers = {
            "Authorization": f"Bearer {auth_token}",
        }
        return requests.delete(url, headers=headers)

    return requests.delete(url)
