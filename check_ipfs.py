import ipfshttpclient

_client = None

def check_ipfs():
    global _client
    if _client is None:
        _client = ipfshttpclient.connect()
    return _client
