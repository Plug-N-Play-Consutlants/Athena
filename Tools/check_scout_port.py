"""Check which local Scout ports are occupied."""
from __future__ import annotations

import socket

HOST = "localhost"
PORTS = [8765, 8766, 8767, 8768]


def in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, port)) == 0


def main():
    print("Scout Port Check")
    print("================")
    for port in PORTS:
        print(f"{port}: {'BUSY' if in_use(port) else 'free'}")


if __name__ == "__main__":
    main()
