#!/usr/bin/env python3
"""
DocuPi-3000 — WD/RDG Chart Generator

Erzeugt Temperatur-Stufendiagramm fuer Waschdesinfektoren.
X-Achse: Uhrzeit der Schritte, Y-Achse: Temperatur (Ist min/max als Band, Soll gestrichelt).
"""

import logging
import tempfile
from typing import Optional

logger = logging.getLogger("docupi.wd_chart")

# Farben konsistent mit MST-Chart
DARK_BLUE = "#1f4e79"
MID_BLUE = "#2e75b6"
RED = "#dc3545"
GREEN = "#27ae60"
ORANGE = "#fd7e14"
LIGHT_GREEN = "#d4efdf"
LIGHT_RED = "#fadbd8"


def generate_wd_chart(steps: list, output_path: Optional[str] = None, width: float = 11, height: float = 4.5) -> Optional[str]:
    """Erzeugt Temperaturverlauf-Chart fuer WD-Prozessschritte.

    Args:
        steps: Liste der Prozessschritte (aus parse_wd_protocol)
        output_path: Ziel-PNG-Pfad (None = temporaere Datei)
        width: Bildbreite in Zoll
        height: Bildhoehe in Zoll

    Returns:
        Pfad zur PNG-Datei oder None bei Fehler.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from datetime import datetime
    except ImportError:
        logger.warning("matplotlib nicht installiert")
        return None

    if not steps or len(steps) < 2:
        logger.warning("Weniger als 2 Schritte — kein Chart moeglich")
        return None

    # Daten vorbereiten
    x_labels = []
    x_times = []
    temp_act_min = []
    temp_act_max = []
    temp_nom_min = []
    temp_nom_max = []
    step_names = []
    has_a0 = []

    for step in steps:
        params = step.get("params", {})
        if "temp_actual" not in params:
            continue

        x_labels.append(step["time"][:5])  # HH:MM
        try:
            x_times.append(datetime.strptime(step["time"], "%H:%M:%S"))
        except ValueError:
            x_times.append(None)

        t_act = params["temp_actual"]
        temp_act_min.append(t_act["min"])
        temp_act_max.append(t_act["max"])

        t_nom = params.get("temp_nominal", {})
        temp_nom_min.append(t_nom.get("min", 0))
        temp_nom_max.append(t_nom.get("max", 0))

        step_names.append(step.get("name_display", step["id"]))
        has_a0.append("a0_value" in params)

    if len(temp_act_min) < 2:
        return None

    x_pos = list(range(len(temp_act_min)))

    # Figure erstellen
    fig, ax = plt.subplots(1, 1, figsize=(width, height), dpi=150)
    fig.patch.set_facecolor("white")

    # Soll-Temperaturband (gruen, halbtransparent)
    has_nom = any(v > 0 for v in temp_nom_max)
    if has_nom:
        ax.fill_between(
            x_pos, temp_nom_min, temp_nom_max,
            alpha=0.15, color=GREEN, step="mid",
            label="Sollbereich",
        )
        ax.step(x_pos, temp_nom_min, where="mid", color=GREEN, linewidth=0.8, linestyle="--", alpha=0.5)
        ax.step(x_pos, temp_nom_max, where="mid", color=GREEN, linewidth=0.8, linestyle="--", alpha=0.5)

    # Ist-Temperaturband (blau)
    ax.fill_between(
        x_pos, temp_act_min, temp_act_max,
        alpha=0.3, color=MID_BLUE, step="mid",
        label="Ist-Bereich (min/max)",
    )
    ax.step(x_pos, temp_act_min, where="mid", color=DARK_BLUE, linewidth=1.5, alpha=0.9)
    ax.step(x_pos, temp_act_max, where="mid", color=DARK_BLUE, linewidth=1.5, alpha=0.9)

    # Ist-Mittelwert als Linie
    temp_act_mid = [(lo + hi) / 2 for lo, hi in zip(temp_act_min, temp_act_max)]
    ax.plot(x_pos, temp_act_mid, color=DARK_BLUE, linewidth=1.0, linestyle="-", alpha=0.4, marker="o", markersize=3)

    # Schritt-Trennlinien und Labels
    for i, name in enumerate(step_names):
        ax.axvline(x=i, color="#ddd", linewidth=0.5, linestyle=":")

        # Name rotiert oben anzeigen
        y_top = ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else max(temp_act_max) * 1.1
        short_name = name[:18]
        ax.text(
            i, max(temp_act_max) * 1.08, short_name,
            fontsize=5.5, rotation=35, ha="left", va="bottom",
            color="#666", alpha=0.8,
        )

        # A0-Wert hervorheben
        if has_a0[i]:
            a0_step = steps[[s.get("name_display", "") for s in steps].index(name)]
            a0_val = a0_step["params"]["a0_value"]["act"]
            ax.annotate(
                f"A0 = {a0_val}",
                xy=(i, temp_act_max[i]),
                xytext=(i + 0.3, temp_act_max[i] + 5),
                fontsize=7, fontweight="bold", color=RED,
                arrowprops=dict(arrowstyle="->", color=RED, lw=0.8),
            )

    # Achsen
    ax.set_xticks(x_pos)
    ax.set_xticklabels(x_labels, fontsize=7, rotation=0)
    ax.set_xlabel("Uhrzeit", fontsize=8, color="#666")
    ax.set_ylabel("Temperatur (\u00b0C)", fontsize=9, color=DARK_BLUE)
    ax.tick_params(axis="y", labelsize=7, labelcolor=DARK_BLUE)
    ax.grid(True, alpha=0.15, axis="y")
    ax.set_xlim(-0.5, len(x_pos) - 0.5)

    # Y-Achse: etwas Luft nach oben fuer Labels
    y_max = max(temp_act_max) * 1.25
    ax.set_ylim(0, max(y_max, 10))

    # Legende
    ax.legend(loc="upper left", fontsize=7, framealpha=0.9)

    # Titel
    fig.suptitle("Temperaturverlauf WD-Prozess", fontsize=11, fontweight="bold", color=DARK_BLUE, y=0.98)
    plt.tight_layout()

    if not output_path:
        output_path = tempfile.mktemp(suffix=".png", prefix="docupi_wd_chart_")

    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("WD-Chart erzeugt: %s", output_path)
    return output_path
