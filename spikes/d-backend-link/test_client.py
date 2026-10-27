"""
Spike D: Test Client
Connects to WebSocket, sends a generation request, streams tokens, issues chat.cancel,
and rigorously measures cancellation latency to ensure it halts within 1 second.
"""

import asyncio
import json
import time
import websockets

WS_URI = "ws://127.0.0.1:8000/ws"

async def test_streaming_and_cancellation():
    print("=== SPIKE D: WEBSOCKET STREAMING & CANCELLATION ===")
    results = {}
    
    async with websockets.connect(WS_URI) as ws:
        # Step 1: Normal Streaming Test
        print("[1] Testing normal token streaming...")
        req_id = "test-stream-1"
        send_payload = {
            "id": req_id,
            "type": "chat.send",
            "payload": {
                "prompt": "Write a short haiku about an intelligent robotic orb.",
                "model": "llama3:latest"
            }
        }
        
        start_time = time.perf_counter()
        first_token_time = None
        tokens = []
        state_changes = []
        
        await ws.send(json.dumps(send_payload))
        
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            mtype = msg.get("type")
            
            if mtype == "state.change":
                state_changes.append(msg["payload"]["state"])
            elif mtype == "chat.token":
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                tokens.append(msg["payload"]["token"])
            elif mtype == "chat.done":
                done_payload = msg["payload"]
                break
            elif mtype == "error":
                raise RuntimeError(f"Server error: {msg['payload']}")
                
        stream_end_time = time.perf_counter()
        first_token_lat = ((first_token_time or stream_end_time) - start_time) * 1000.0
        print(f"    Stream completed: {len(tokens)} tokens in {stream_end_time - start_time:.2f}s")
        print(f"    First token latency: {first_token_lat:.2f} ms")
        print(f"    States transitioned: {' -> '.join(state_changes)}")
        print(f"    Full output: {''.join(tokens).strip()}")
        
        results["streaming_works"] = True
        results["first_token_ms"] = round(first_token_lat, 2)
        results["tps"] = done_payload.get("tps")
        
        # Step 2: Cancellation Test (< 1 second)
        print("\n[2] Testing cancellation (< 1 second threshold)...")
        cancel_req_id = "test-cancel-2"
        long_prompt = "Generate a very long exhaustive 2000-word historical essay detailing the evolution of digital computing architectures from 1940 to 2026."
        
        await ws.send(json.dumps({
            "id": cancel_req_id,
            "type": "chat.send",
            "payload": {
                "prompt": long_prompt,
                "model": "llama3:latest"
            }
        }))
        
        tokens_before_cancel = 0
        cancel_sent_time = None
        cancel_confirmed_time = None
        post_cancel_tokens = 0
        
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            mtype = msg.get("type")
            
            if mtype == "chat.token":
                tokens_before_cancel += 1
                # When we have received at least 8 tokens, trigger cancel!
                if tokens_before_cancel == 8 and cancel_sent_time is None:
                    print(f"    Received 8 tokens. Sending chat.cancel now...")
                    cancel_sent_time = time.perf_counter()
                    await ws.send(json.dumps({
                        "id": cancel_req_id,
                        "type": "chat.cancel",
                        "payload": {}
                    }))
                elif cancel_sent_time is not None:
                    post_cancel_tokens += 1
            elif mtype == "chat.cancelled":
                cancel_confirmed_time = time.perf_counter()
                server_cancel_ms = msg["payload"].get("cancel_duration_ms", 0)
                print(f"    Server confirmed cancellation! (reported server ms: {server_cancel_ms}ms)")
                break
                
        roundtrip_cancel_ms = (cancel_confirmed_time - cancel_sent_time) * 1000.0
        print(f"    Measured client roundtrip cancel latency: {roundtrip_cancel_ms:.2f} ms")
        print(f"    Tokens received after cancel sent: {post_cancel_tokens}")
        
        assert roundtrip_cancel_ms < 1000.0, f"Cancel took too long: {roundtrip_cancel_ms} ms (exceeds 1000 ms)"
        print(f"    [PASS] Cancellation halted generation in < 1 second! ({roundtrip_cancel_ms:.1f} ms)")
        
        results["cancel_ms"] = round(roundtrip_cancel_ms, 2)
        results["cancellation_under_1s"] = True
        results["status"] = "works"
        
    return results

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(test_streaming_and_cancellation())
    with open("spikes/d-backend-link/results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("\nResults saved to spikes/d-backend-link/results.json")
