from typing import List
from ecu_settings import ECUSettings
import random
from ecu_settings import OBD_PROTOCOLS  

class ModeHandler:
    def handle(self, pid: str) -> str | None:
        raise NotImplementedError("Must implement handle method")

class Mode01Handler(ModeHandler):
    def handle(self, pid: str) -> str | None:
        match pid:
            case "00":
                return "BE 3F A8 13"
            case "0C":  # RPM
                rpm = random.randint(800, 3000)
                val = rpm * 4
                return f"{(val >> 8):02X} {val & 0xFF:02X}"
            case "0D":  # Speed
                spd = random.randint(0, 120)
                return f"{spd:02X}"
            case "05":  # Coolant Temp
                temp = random.randint(70, 100) + 40
                return f"{temp:02X}"
            case "20":  
                return "90 07 E0 11"
            case "40":  
                return "FA DC 80 00"
            case _:
                return None

class Mode09Handler(ModeHandler):
    def handle(self, pid: str) -> str | None:
        match pid:
            case "00":  # Supported PIDs [01-20]
                return "01 23 45 67 89 AB CD EF"
            case "02":  # VIN
                vin_ascii = "1N4AL3AP7DC199583"
                return " ".join(f"{ord(c):02X}" for c in vin_ascii)
            case "03":  # CVN
                return "01 23 45 67"
            case _:
                return None

class OBDCommandProcessor:
    def __init__(self, ecu_settings: ECUSettings):
        self.ecu = ecu_settings
        self.handlers: dict[str, ModeHandler] = {
            "01": Mode01Handler(),
            # "06": Mode06Handler(),
            "09": Mode09Handler(),
        }

    def handle_command(self, command: str) -> str:
        command = command.strip().upper()
        if command.startswith("AT"):
            res =  [self._handle_at(command)]
        elif command[:2] in ("01", "09", "06"):
            res = self._handle_pid(command)
        else:
            res = [self._format_single(command, "NO DATA")]

        if self.ecu.echo:
                    res.insert(0, command)

        return "\r\n".join(res) + "\r\n\r\n>"

    def _handle_at(self, command: str) -> str:
        at_commands = {
            "ATI": "ELM327 v1.5",
            "ATZ": self._reset_and_return("ELM327 v1.5"),
            "ATH1": self._set_attr("header_on", True),
            "ATH0": self._set_attr("header_on", False),
            "ATE1": self._set_attr("echo", True),
            "ATE0": self._set_attr("echo", False),
            "ATL1": self._set_attr("linefeed", True),
            "ATL0": self._set_attr("linefeed", False),
            "ATDP": f"Protocol {self.ecu.protocol} ({OBD_PROTOCOLS[self.ecu.protocol]['name']})",
            "ATDPN": f"{self.ecu.protocol:02X}",
            "ATSP0": "OK",
            "ATSP1": "OK",  # Set to Protocol 1 (ISO 9141-2)
        }
        if command in at_commands:
            return at_commands[command]
        return "NO DATA"
    
    def _reset_and_return(self, response: str) -> str:
        self.ecu.reset()
        return response
    
    def _set_attr(self, attr: str, value: bool) -> str:
        setattr(self.ecu, attr, value)
        return "OK"

    def _handle_pid(self, command: str) -> list[str]:
        prefix = command[:2]
        handler = self.handlers.get(prefix)
        if not handler:
            return ["NO DATA"]

        responses = []
        for i in range(2, len(command), 2):
            pid = command[i:i+2]
            response = handler.handle(pid)
            if not response:
                return ["NO DATA"]
            
            parts = response.split()
            responses += [pid] + parts

        return self._package_multi_frame(command, prefix, responses)
    
    def _package_multi_frame(self, command: str, prefix: str, payload: list[str]) -> list[str]:
        header = f"{self.ecu.header} " if self.ecu.header_on else ""
        mode = f"{(int(prefix) + 0x40):02X}"

        # Single-frame case
        if len(payload) <= 6:
            return [self._format_single(command, " ".join(payload))]

        total_len = len(payload) + 2  # +2 for mode and length
        pci = f"10 {total_len:02X}"
        # 7E8 10 14 49 02 01 31 4E 34
        # │   │  │  │  │  │  │  │  └─ '4' of 'N'
        # │   │  │  │  │  │  │  └──── 'N'
        # │   │  │  │  │  │  └─────── '1'
        # │   │  │  │  │  └────────── Frame Index = 01
        # │   │  │  │  └───────────── PID = 02
        # │   │  │  └──────────────── Mode + 0x40 = 49
        # │   │  └─────────────────── Length of entire payload (20 bytes)
        # │   └────────────────────── PCI type = First Frame (0x10)
        # └────────────────────────── CAN ID (header)

       # First Frame contains: [PCI] [Mode] [PID] [Frame Index] + up to 3 data bytes

        ff_payload = payload[:4]
        frame_index = "01"

        ff_payload = [payload[0], frame_index] + payload[1:4]  # PID, Index, then data

        ff = f"{header}{pci} {mode} " + " ".join(ff_payload)
        while len(ff.split()) < 8:
            ff += " 00"
        frames = [ff.strip()]

        # Consecutive Frames (7 bytes each)
        idx = 4
        frame_seq = 1
        while idx < total_len - 2:
            chunk = payload[idx:idx + 7]
            cf = f"{header}{0x20 + frame_seq:02X} " + " ".join(chunk)
            while len(cf.split()) < 8:
                cf += " 00"
            frames.append(cf.strip())
            idx += 7
            frame_seq += 1
        return frames

    def _format_single(self, command: str, payload: str) -> str:
        header = f"{self.ecu.header} " if self.ecu.header_on else ""
        mode = int(command[:2], 16) + 0x40
        payload_bytes = payload.split()
        length = len(payload_bytes) + 1  # +1 for mode

        frame = [f"{length:02X}", f"{mode:02X}"] + payload_bytes
        
        while len(frame) < 8:
            frame.append("00")
        
        if header:
            frame.insert(0, header)
        
        result = " ".join(frame)

        if self.ecu.echo:
            result = f"{command} {result}"
        return result

if __name__ == "__main__":  
    ecu = ECUSettings()
    processor = OBDCommandProcessor(ecu)
    # print(processor.handle_command("ATH1"))
    print(processor.handle_command("0100"))  
    print(processor.handle_command("0902")) 
    # print(processor.handle_command("010C"))  # RPM

    # ["7E8 10 14 49 02 01 31 4E 34", "7E8 21 41 4C 33 41 50 37 44", "7E8 22 43 31 39 39 35 38 33"]
