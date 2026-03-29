import websocket
NUM_LEDS = 180
WS_URL = "ws://192.168.50.229/ws" 

CODE = websocket.ABNF.OPCODE_BINARY

def create_websocket_client():
    ws = websocket.create_connection(WS_URL)
    return ws

def build_frame_packet(colors: list[tuple[int, int, int]]) -> bytes:
    if len(colors) != NUM_LEDS:
        raise ValueError(f"Expected {NUM_LEDS} LEDs, got {len(colors)}")

    payload = bytearray()
    payload.append(0x01)  # FULL_FRAME

    data_length = NUM_LEDS * 3
    payload.append(data_length & 0xFF)
    payload.append((data_length >> 8) & 0xFF)

    for r, g, b in colors:
        payload.extend((
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b))),
        ))

    return bytes(payload)

def build_brightness_packet(value: int) -> bytes:
    value = max(0, min(255, int(value)))
    return bytes([0x02, value])