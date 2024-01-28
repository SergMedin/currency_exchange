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

    def __init__(self, credentials_filepath, table_key, sheet_title: str = None):
        # assert sheet_title is not None  # Andrey asked to remove this assert
        with self.__class__._gapi_lock:
            self.__class__._gapi_credentials_filepath = credentials_filepath
            self.table = self._get_table(table_key)
            self.sheet = self.table.sheet1 if sheet_title is None else self.table.worksheet(sheet_title)

    def update_cell(self, row: int, col: int, val: str):
        with self.__class__._gapi_lock:
            self.sheet.update_cell(row, col, val)

    def update(self, range_name: str, values: List[List[Any]]):
        with self.__class__._gapi_lock:
            self.sheet.update(range_name=range_name, values=values)

    def cell(self, row: int, col: int) -> str:
        with self.__class__._gapi_lock:
            return self.sheet.cell(row, col).value

    def find(self, query, in_row=None, in_column=None, case_sensitive=True):
        with self.__class__._gapi_lock:
            return self.sheet.find(query, in_row, in_column, case_sensitive)

    def next_available_row(self):
        with self.__class__._gapi_lock:
            str_list = list(self.sheet.col_values(1))
            return len(str_list) + 1

    def freeze(self, rows=None, cols=None):
        with self.__class__._gapi_lock:
            self.sheet.freeze(rows, cols)

    def col_values(self, col: int):
        return self.sheet.col_values(col)

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
    row: int
    col: int
    value: Any
    format: Dict = dataclasses.field(default_factory=dict)


class GSpreadsTableMock:
    def __init__(self):
        self._d: Dict[Tuple[int, int], _Cell] = {}
        self._sheets: List[str] = ['Sheet1']

    def update_cell(self, row: int, col: int, val: str):
        assert isinstance(row, int)
        assert isinstance(col, int)
        p = (row, col)
        self._d[p] = _Cell(row, col, val)

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

    def next_available_row(self):
        return self.find("", None, 1).row

    def find(self, query, in_row=None, in_column=None, case_sensitive=True):
        cells = self._d.values()
        if in_column:
            cells = [c for c in cells if c.col == in_column]
        if in_row:
            cells = [c for c in cells if c.row == in_row]

        if query == "" and in_column:
            max_row = max(c.row for c in cells) if cells else 0
            row = max_row + 1
            return _Cell(row, in_column, "")

        if query == "" and in_row:
            raise NotImplementedError()

        cells = [c for c in cells if c.value == query]
        return cells[0] if cells else None

    def freeze(self, rows=None, cols=None):
        pass

    def col_values(self, col: int):
        rows = [c.row for c in self._d.values() if c.col == col]
        if not rows:
            return []
        mrow = max(rows)
        res = []
        for row in range(1, mrow+2):
            res.append(self.cell(row, col))
        return res


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
