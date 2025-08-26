import asyncio
from bleak import BleakClient
MAC  = "A0:9E:1A:EB:A2:36"
UUID = "00002A37-0000-1000-8000-00805f9b34fb"
def cb(_, data: bytearray):
    f=data[0]; bpm = int.from_bytes(data[1:3],"little") if (f&1) else data[1]
    print("BPM:", int(bpm))
async def main():
    print("Connecting to", MAC)
    async with BleakClient(MAC) as c:
        print("Connected. Listening 10s?")
        await c.start_notify(UUID, cb)
        await asyncio.sleep(10)
        await c.stop_notify(UUID)
asyncio.run(main())
