import ipfshttpclient

def check_ipfs():
    client = ipfshttpclient.connect()
    return client
