#!/usr/bin/env python3
"""Tests fuer den WD/RDG-Protokoll-Parser."""

import sys
import os
import pytest

# src/ zum Pfad hinzufuegen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wd_protocol_parser import decode_ht_file, parse_wd_protocol, parse_ht_file

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "wd390", "WD390_4.ht")


@pytest.fixture
def decoded_text():
    """Dekodierter Klartext aus der HT-Datei."""
    return decode_ht_file(FIXTURE_PATH)


@pytest.fixture
def parsed_data(decoded_text):
    """Vollstaendig geparstes Protokoll."""
    return parse_wd_protocol(decoded_text)


# --- HT-Dekodierung ---

class TestDecodeHtFile:
    def test_returns_string(self):
        text = decode_ht_file(FIXTURE_PATH)
        assert isinstance(text, str)
        assert len(text) > 100

    def test_starts_with_belimed(self):
        text = decode_ht_file(FIXTURE_PATH)
        assert text.strip().startswith("belimed")

    def test_contains_key_fields(self):
        text = decode_ht_file(FIXTURE_PATH)
        assert "operation company" in text
        assert "machine type" in text
        assert "program cycle" in text

    def test_invalid_file_raises(self, tmp_path):
        fake = tmp_path / "fake.ht"
        fake.write_bytes(b"This is not a HyperTerminal file")
        with pytest.raises(ValueError, match="Marker.*fehlt"):
            decode_ht_file(str(fake))


# --- Kopfdaten ---

class TestParseHeader:
    def test_operator(self, parsed_data):
        # "ü" geht bei UTF-16LE-Dekodierung verloren -> "Mnchen"
        assert "Klinik" in parsed_data["operator"]

    def test_machine_model(self, parsed_data):
        assert parsed_data["machine_model"] == "WD390-4"

    def test_user(self, parsed_data):
        assert parsed_data["user"] == "User"

    def test_machine_nr(self, parsed_data):
        assert parsed_data["machine_nr"] == "2015488"

    def test_charge_nr(self, parsed_data):
        assert parsed_data["charge_nr"] == "4575"

    def test_program_name(self, parsed_data):
        assert parsed_data["program_name"] == "OP-Universal"

    def test_program_version(self, parsed_data):
        assert parsed_data["program_nr"] == "01"
        assert parsed_data["program_version"] == "1.00"

    def test_cycle_start(self, parsed_data):
        assert parsed_data["cycle_start"] == "2026-03-27T11:08:39"

    def test_cycle_end(self, parsed_data):
        assert parsed_data["cycle_end"] == "2026-03-27T12:10:56"

    def test_rack(self, parsed_data):
        assert parsed_data["rack"] == "0087003601"

    def test_cycle_duration(self, parsed_data):
        assert parsed_data["cycle_duration_sec"] == 3737
        assert "62 min" in parsed_data["cycle_duration_display"]

    def test_machine_type_flag(self, parsed_data):
        assert parsed_data["machine_type"] == "wd"


# --- Ergebnis ---

class TestResultDetection:
    def test_result_bestanden(self, parsed_data):
        assert parsed_data["result"] == "BESTANDEN"

    def test_result_detail(self, parsed_data):
        assert "without failure" in parsed_data["result_detail"]


# --- Prozessschritte ---

class TestParseSteps:
    def test_step_count(self, parsed_data):
        assert len(parsed_data["steps"]) == 7

    def test_step_ids(self, parsed_data):
        ids = [s["id"] for s in parsed_data["steps"]]
        assert ids == ["1.1", "1.2", "2.1", "3.1", "3.1", "3.2", "4.1"]

    def test_step_names(self, parsed_data):
        names = [s["name"] for s in parsed_data["steps"]]
        assert "precleaning" in names
        assert "thermal_disinfection" in names
        assert "drying" in names

    def test_step_times(self, parsed_data):
        times = [s["time"] for s in parsed_data["steps"]]
        assert times[0] == "11:08:58"
        assert times[-1] == "11:57:25"

    def test_precleaning_params(self, parsed_data):
        step = parsed_data["steps"][0]
        assert step["name"] == "precleaning"
        p = step["params"]
        assert p["step_time"]["nom"] == 180
        assert p["step_time"]["act"] == 181
        assert p["temp_actual"]["min"] == 15.6
        assert p["temp_actual"]["max"] == 26.3


# --- Schritt-Parameter im Detail ---

class TestStepParameters:
    def test_thermal_disinfection(self, parsed_data):
        td = [s for s in parsed_data["steps"] if s["name"] == "thermal_disinfection"][0]
        p = td["params"]

        # A0-Wert
        assert p["a0_value"]["nom"] == 3200
        assert p["a0_value"]["act"] == 3408

        # Temperatur
        assert p["temp_actual"]["min"] == 90.6
        assert p["temp_actual"]["max"] == 93.6
        assert p["temp_nominal"]["min"] == 90.0
        assert p["temp_nominal"]["max"] == 95.0

        # Leitwert
        assert p["conductivity"]["max"] == 50.0
        assert p["conductivity"]["act"] == 1.8

    def test_cleaning_1_dosing(self, parsed_data):
        c1 = parsed_data["steps"][1]
        assert c1["name"] == "cleaning_1"
        assert c1["params"]["dosing"]["nom"] == 162
        assert c1["params"]["dosing"]["act"] == 162

    def test_cleaning_2_dosing(self, parsed_data):
        c2 = parsed_data["steps"][2]
        assert c2["name"] == "cleaning_2"
        assert c2["params"]["dosing"]["nom"] == 287
        assert c2["params"]["dosing"]["act"] == 288

    def test_drying_temps(self, parsed_data):
        dry = parsed_data["steps"][-1]
        assert dry["name"] == "drying"
        assert dry["params"]["temp_actual"]["min"] == 98.3
        assert dry["params"]["temp_actual"]["max"] == 115.3


# --- KPIs ---

class TestKPIs:
    def test_a0_passed(self, parsed_data):
        a0 = parsed_data["kpi"]["a0_value"]
        assert a0["nom"] == 3200
        assert a0["act"] == 3408
        assert a0["passed"] is True

    def test_conductivity_passed(self, parsed_data):
        cond = parsed_data["kpi"]["conductivity"]
        assert cond["max_allowed"] == 50.0
        assert cond["act"] == 1.8
        assert cond["passed"] is True

    def test_thermal_temp_passed(self, parsed_data):
        temp = parsed_data["kpi"]["thermal_disinfection_temp"]
        assert temp["min"] == 90.6
        assert temp["max"] == 93.6
        assert temp["passed"] is True

    def test_total_duration(self, parsed_data):
        assert parsed_data["kpi"]["total_duration_sec"] == 3737

    def test_dosing_kpis(self, parsed_data):
        dosing = parsed_data["kpi"]["dosing"]
        assert len(dosing) == 2
        assert dosing[0]["step"] == "Cleaning 1"
        assert dosing[1]["act"] == 288


# --- Klartext-Input (ohne HT-Wrapper) ---

class TestPlainTextInput:
    def test_parse_from_decoded_text(self, decoded_text):
        """Parser funktioniert mit bereits dekodiertem Klartext."""
        result = parse_wd_protocol(decoded_text)
        assert result["machine_model"] == "WD390-4"
        assert len(result["steps"]) == 7

    def test_parse_ht_file_convenience(self):
        """Convenience-Funktion parse_ht_file() liefert vollstaendiges Ergebnis."""
        result = parse_ht_file(FIXTURE_PATH)
        assert result["charge_nr"] == "4575"
        assert result["kpi"]["a0_value"]["passed"] is True
