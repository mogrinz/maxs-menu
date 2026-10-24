"""Unprivileged client for the fixed local network-control protocol."""
import json
import socket

SOCKET = '/run/maxs-menu-network/control.sock'


def request_network(body):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(45)
            connection.connect(SOCKET)
            connection.sendall(json.dumps(body).encode()+b'\n')
            response = b''
            while not response.endswith(b'\n'):
                chunk = connection.recv(4096)
                if not chunk or len(response) > 65536:
                    raise OSError('Incomplete network-service response.')
                response += chunk
        result = json.loads(response)
        if 'error' in result:
            raise ValueError(result['error'])
        return result
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError('Network service is unavailable. Check maxs-menu-network.service on the Pi.') from error
