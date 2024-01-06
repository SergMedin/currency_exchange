import threading
import unittest
from typing import Any, Tuple, Dict, List
import dataclasses
import gspread
from oauth2client.service_account import ServiceAccountCredentials


class GSpreadsTable:
    _gapi_lock = threading.RLock()
    _gapi_client = None
    _gapi_tables: dict[str, Any] = {}
    _gapi_credentials_filepath: str = None

    def __init__(self, credentials_filepath, table_key):
        self._gapi_credentials_filepath = credentials_filepath
        self.table = self._get_table(table_key)
        self.sheet1 = self.table.sheet1

    def update_cell(self, row: int, col: int, val: str):
        self.sheet1.update_cell(row, col, val)

    def cell(self, row: int, col: int) -> str:
        return self.sheet1.update_cell(row, col).value

    @classmethod
    def _get_table(cls, table_key):
        with cls._gapi_lock:
            if not cls._gapi_client:
                scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
                creds = ServiceAccountCredentials.from_json_keyfile_name(cls._gapi_credentials_filepath, scope)
                cls._gapi_client = gspread.authorize(creds)
            if table_key not in cls._gapi_tables:
                cls._gapi_tables[table_key] = cls._gapi_client.open_by_key(table_key)
            return cls._gapi_tables[table_key]


@dataclasses.dataclass
class _Cell:
    value: Any
    format: Dict = dataclasses.field(default_factory=dict)


class GSpreadsTableMock:
    def __init__(self):
        self._d: Dict[Tuple[int, int], _Cell] = {}

    def update_cell(self, row: int, col: int, val: str):
        assert isinstance(row, int)
        assert isinstance(col, int)
        p = (row, col)
        self._d[p] = _Cell(val)

    def update(self, range_name: str, values: List[List[Any]]):
        assert range_name[0] >= "A" and range_name[0] <= "Z"
        col = ord(range_name[0]) - 64  # 'A' -> 1, 'B' -> 2
        row = int(range_name[1:])
        for ridx, row_values in enumerate(values):
            for cidx, value in enumerate(row_values):
                self.update_cell(row + ridx, col + cidx, value)

    def cell(self, row: int, col: int) -> Any:
        p = (row, col)
        if p in self._d:
            return self._d[p].value
        else:
            return None


class TestGspreadMock(unittest.TestCase):

    def test_simple(self):
        m = GSpreadsTableMock()
        m.update("A1", [["sell", "cow", "2"]])
        self.assertEqual(m.cell(1, 1), "sell")
        self.assertEqual(m.cell(1, 2), "cow")
        m.update("A4", [["sell", "cow", "2"]])
        self.assertEqual(m.cell(4, 1), "sell")
        self.assertEqual(m.cell(4, 2), "cow")
        self.assertEqual(m.cell(4, 3), "2")
        self.assertEqual(m.cell(4, 4), None)
