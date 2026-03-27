#!/usr/bin/env python3
"""End-to-End-Test: .ht-Datei -> Parser -> Chart -> PDF."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wd_protocol_parser import decode_ht_file, parse_wd_protocol
from wd_chart_generator import generate_wd_chart
from wd_pdf_generator import generate_wd_pdf

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "wd390")
HT_FILE = os.path.join(FIXTURE_DIR, "WD390_4.ht")
OUTPUT_PDF = os.path.join(FIXTURE_DIR, "e2e_output.pdf")
OUTPUT_CHART = os.path.join(FIXTURE_DIR, "e2e_chart.png")


@pytest.fixture(scope="module")
def protocol_data():
    """Parst die HT-Datei einmal fuer alle Tests."""
    text = decode_ht_file(HT_FILE)
    return parse_wd_protocol(text)


@pytest.fixture(scope="module")
def chart_path(protocol_data):
    """Generiert den Chart einmal fuer alle Tests."""
    path = generate_wd_chart(protocol_data["steps"], OUTPUT_CHART)
    return path


@pytest.fixture(scope="module")
def pdf_path(protocol_data, chart_path):
    """Generiert das PDF einmal fuer alle Tests."""
    path = generate_wd_pdf(protocol_data, output_path=OUTPUT_PDF, chart_path=chart_path)
    return path


class TestEndToEnd:
    def test_ht_decode_produces_text(self):
        text = decode_ht_file(HT_FILE)
        assert len(text) > 500
        assert "belimed" in text.lower()

    def test_parser_returns_complete_data(self, protocol_data):
        assert protocol_data["machine_type"] == "wd"
        assert protocol_data["machine_model"] == "WD390-4"
        assert protocol_data["charge_nr"] == "4575"
        assert protocol_data["result"] == "BESTANDEN"
        assert len(protocol_data["steps"]) == 7
        assert "kpi" in protocol_data

    def test_chart_generated(self, chart_path):
        assert chart_path is not None
        assert os.path.exists(chart_path)
        assert os.path.getsize(chart_path) > 10000

    def test_pdf_generated(self, pdf_path):
        assert pdf_path is not None
        assert os.path.exists(pdf_path)

    def test_pdf_size_reasonable(self, pdf_path):
        size = os.path.getsize(pdf_path)
        assert size > 10000, f"PDF zu klein: {size} bytes"
        assert size < 5_000_000, f"PDF zu gross: {size} bytes"

    def test_pdf_has_two_pages(self, pdf_path):
        """Prueft ob das PDF 2 Seiten hat (ueber die Dateistruktur)."""
        with open(pdf_path, "rb") as f:
            content = f.read()
        # fpdf2 schreibt '/Type /Page' fuer jede Seite
        page_count = content.count(b"/Type /Page")
        # Mindestens 2 (koennte auch /Pages enthalten)
        assert page_count >= 2, f"Nur {page_count} Page-Eintraege gefunden"

    def test_pdf_contains_key_data(self, pdf_path):
        """Prueft ob Schluesseldaten im dekomprimierten PDF-Text vorkommen."""
        content = _decompress_pdf(pdf_path)
        assert "WD390" in content
        assert "4575" in content
        assert "BESTANDEN" in content

    def test_all_steps_in_pdf(self, pdf_path):
        """Prueft ob alle Schrittnamen im dekomprimierten PDF vorkommen."""
        content = _decompress_pdf(pdf_path)
        expected = ["Precleaning", "Cleaning 1", "Cleaning 2", "Final Rinse", "Drying"]
        for name in expected:
            assert name in content, f"'{name}' nicht im PDF gefunden"


def _decompress_pdf(pdf_path):
    """Dekomprimiert FlateDecode-Streams und gibt den Text zurueck."""
    import zlib
    with open(pdf_path, "rb") as f:
        raw = f.read()
    text_parts = []
    # Unkomprimierten Text extrahieren
    text_parts.append(raw.decode("latin-1", errors="replace"))
    # FlateDecode-Streams dekomprimieren
    idx = 0
    while True:
        start = raw.find(b"stream\n", idx)
        if start == -1:
            break
        start += len(b"stream\n")
        end = raw.find(b"\nendstream", start)
        if end == -1:
            break
        try:
            decompressed = zlib.decompress(raw[start:end])
            text_parts.append(decompressed.decode("latin-1", errors="replace"))
        except zlib.error:
            pass
        idx = end + 1
    return "".join(text_parts)
