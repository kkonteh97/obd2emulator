OBD_PROTOCOLS = {
    0: {"name": "AUTO"},
    1: {
        "name": "SAE J1850 PWM",
        "header": "41 6B 10",
        "frame_type": "J1850_SINGLE",
    },
    3: {
        "name": "ISO 9141-2",
        "header": "48 6B 11",
        "frame_type": "SERIAL",
    },
    4: {
        "name": "ISO 14230-4 KWP (fast init)",
        "header": "48 6B 11",
        "frame_type": "SERIAL",
    },
    5: {
        "name": "ISO 14230-4 KWP (slow init)",
        "header": "48 6B 11",
        "frame_type": "SERIAL",
    },
    6: {
        "name": "ISO 15765-4 CAN (11 bit ID, 500 kbaud)",
        "header": "7E8",
        "frame_type": "CAN_ISO_TP",
    },
    7: {
        "name": "ISO 15765-4 CAN (29 bit ID, 500 kbaud)",
        "header": "18DAF110",
        "frame_type": "CAN_ISO_TP",
    },
    8: {
        "name": "ISO 15765-4 CAN (11 bit ID, 250 kbaud)",
        "header": "7E0",
        "frame_type": "CAN_ISO_TP",
    },
    9: {
        "name": "ISO 15765-4 CAN (29 bit ID, 250 kbaud)",
        "header": "18DAF110",
        "frame_type": "CAN_ISO_TP",
    },
    10: {
        "name": "SAE J1939 CAN (29 bit ID, 250 kbaud)",
        "header": "18DAF110",
        "frame_type": "CAN_J1939",
    },
}

class ECUSettings:
    def __init__(self):
        self.header_on = True
        self.echo = True
        self.linefeed = False
        self.protocol = 6  # e.g., ISO 15765-4 (CAN 11/500)
        self.header = OBD_PROTOCOLS[self.protocol]["header"]

    def set_protocol(self, num: int):
        self.protocol = num
        self.header = OBD_PROTOCOLS.get(num, {}).get("header", "7E8")

    def reset(self):
        self.__init__()

    def __repr__(self):
        return (
            f"<ECUSettings header={self.header_on} "
            f"echo={self.echo} linefeed={self.linefeed}>"
        )
