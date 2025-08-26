# updated_test_obs_connect.py

import asyncio
import json
import os

import pytest

websockets = pytest.importorskip("websockets")

pytest.skip("OBS WebSocket integration test requires running server", allow_module_level=True)


async def connect_and_start_recording():
    uri = os.getenv("OBS_WS_URL", "ws://localhost:4455")

    async with websockets.connect(uri) as ws:
        print("🔌 Connected to OBS WebSocket")

        # Step 1: Expect HELLO from OBS
        hello = await ws.recv()
        hello_data = json.loads(hello)
        print("🟢 Received HELLO:", hello_data)

        # Step 2: IDENTIFY
        identify_payload = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "eventSubscriptions": 1,
                # omit "authentication" if password is disabled
            },
        }
        await ws.send(json.dumps(identify_payload))
        print("📤 Sent IDENTIFY")

        # Step 3: Wait for IDENTIFIED
        identified = await ws.recv()
        print("🟢 IDENTIFIED:", identified)

        # Step 4: Start recording
        start_record_payload = {"op": 6, "d": {"requestType": "StartRecord", "requestId": "rec_001"}}
        await ws.send(json.dumps(start_record_payload))
        print("🎬 StartRecord sent")

        # Step 5: Await response
        response = await ws.recv()
        print("✅ Response:", response)


asyncio.run(connect_and_start_recording())
