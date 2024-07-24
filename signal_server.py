import asyncio


class SignalingServerProtocol(asyncio.Protocol):
    def __init__(self, clients):
        self.clients = clients

    def connection_made(self, transport):
        self.transport = transport
        self.clients.append(self)

    def connection_lost(self, exc):
        self.clients.remove(self)

    def data_received(self, data):
        for client in self.clients:
            if client is not self:
                client.transport.write(data)


async def main():
    clients = []
    server = await asyncio.get_event_loop().create_server(
        lambda: SignalingServerProtocol(clients), '127.0.0.1', 5678
    )
    async with server:
        print("Signaling server running on tcp://127.0.0.1:5678")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
