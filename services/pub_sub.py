import asyncio


class PubSub:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, fn):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(fn)

    def unsubscribe(self, event_type, fn):
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(fn)

    async def publish(self, event_type, data=None):
        if event_type in self.subscribers:
            for fn in self.subscribers[event_type]:
                if asyncio.iscoroutinefunction(fn):
                    if data is None:
                        await fn()
                    else:
                        await fn(data)
                else:
                    if data is None:
                        fn()
                    else:
                        fn(data)
