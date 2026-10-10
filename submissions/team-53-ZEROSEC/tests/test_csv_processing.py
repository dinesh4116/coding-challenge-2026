import pytest
import io
from csv_processor import CSVProcessor

def test_column_auto_mapping():
    raw_cols = ["Search term", "Campaign name", "Spend", "Orders"]
    analysis = CSVProcessor.detect_and_map_columns(raw_cols)
    mapping = analysis["canonical_mapping"]
    
    assert mapping["query_text"] == "Search term"
    assert mapping["campaign"] == "Campaign name"
    assert mapping["cost"] == "Spend"
    assert mapping["conversions"] == "Orders"

def test_load_and_standardize_csv_temp_file(tmp_path):
    p = tmp_path / "test_data.csv"
    p.write_text("search_term,clicks,cost,conversions\ncheap laptop,10,15.5,1\n")

    records, summary = CSVProcessor.load_and_standardize_csv(str(p))

    assert len(records) == 1
    assert "source_row_id" in records[0]
    assert records[0]["query_text"] == "cheap laptop"
    assert records[0]["clicks"] == 10
    assert summary["valid_rows"] == 1


def test_missing_required_column_raises_error(tmp_path):
    p = tmp_path / "invalid.csv"
    p.write_text("clicks,cost,conversions\n10,15.5,1\n")

    with pytest.raises(ValueError) as exc_info:
        CSVProcessor.load_and_standardize_csv(str(p))
    assert "Missing required columns" in str(exc_info.value)

def test_load_and_standardize_xlsx(tmp_path):
    import openpyxl
    p = tmp_path / "test_data.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Search Terms Report"
    ws.append(["Search term", "Clicks", "Spend", "Orders"])
    ws.append(["refurbished laptop", 12, 25.0, 1])
    wb.save(p)

    with open(p, "rb") as f:
        file_bytes = f.read()

    records, summary = CSVProcessor.load_and_standardize_file(file_bytes, "test_data.xlsx")
    assert len(records) == 1
    assert records[0]["query_text"] == "refurbished laptop"
    assert records[0]["clicks"] == 12
    assert summary["selected_sheet"] == "Search Terms Report"

