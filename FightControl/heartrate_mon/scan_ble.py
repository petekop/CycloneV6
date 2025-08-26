import asyncio
from bleak import BleakScanner, BleakClient

HR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

async def scan():
    print("🔍 Scanning for BLE HR monitors (8s)...")
    devices = await BleakScanner.discover(timeout=8.0)
    for d in devices:
        name = d.name or "?"
        if "Polar" in name or "H10" in name or "H9" in name:
            print(f"📡 Found: {name} | {d.address}")
            # Lightly probe services so we know notify char exists
            try:
                async with BleakClient(d.address) as c:
                    print("  ✅ Connected. Reading services...")
                    for svc in (await c.get_services()):
                        print(f"    [Service] {svc.uuid}")
                        for ch in svc.characteristics:
                            props = ", ".join(ch.properties)
                            print(f"      └── [Characteristic] {ch.uuid} | {props}")
            except Exception as e:
                print(f"  ⚠️ Could not connect: {e}")

if __name__ == "__main__":
    asyncio.run(scan())
