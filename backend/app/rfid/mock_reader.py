from datetime import datetime, timezone


class MockRFIDReader:
    """Software-only RFID reader. No hardware connected."""

    reader_id = "MOCK-STAFF-01"

    def scan(self, epc: str) -> dict:
        if not epc.startswith("MOCK-EPC-"):
            raise ValueError(
                "Only synthetic MOCK-EPC tags are supported"
            )

        return {
            "reader_id": self.reader_id,
            "epc": epc,
            "source": "MOCK",
            "hardware_connected": False,
            "scanned_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
