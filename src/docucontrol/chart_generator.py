#!/usr/bin/env python3
"""
DocuPi-3000 - Chart Generator v2
Trend chart with RTC time on X-axis.
"""

import os
import logging
import tempfile

logger = logging.getLogger("docupi.chart")


def generate_trend_chart(phases, output_path=None, width=11, height=4, start_time=None, t3_label="T3 Luftnachweis"):
    """Generate trend chart with Uhrzeit on X-axis."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        import matplotlib.dates as mdates
        from datetime import datetime, timedelta
    except ImportError:
        logger.warning("matplotlib nicht installiert")
        return None

    if not phases or len(phases) < 2:
        return None

    # Extract data
    times_min = []
    rtc_times = []
    p2_vals = []
    t2_vals = []
    t3_vals = []
    labels = []

    for p in phases:
        parts = p["time_offset"].split(":")
        t_min = int(parts[0]) + int(parts[1]) / 60.0
        times_min.append(t_min)

        # Calculate RTC datetime
        if start_time:
            offset_sec = int(parts[0]) * 60 + int(parts[1])
            rtc = start_time + timedelta(seconds=offset_sec)
            rtc_times.append(rtc)
        elif p.get("rtc_time"):
            try:
                rtc_times.append(datetime.strptime(p["rtc_time"], "%H:%M:%S"))
            except:
                rtc_times.append(None)

        p2_vals.append(p.get("p2_mbar", p.get("pressure_mbar", 0)))
        t2_vals.append(p.get("t2_c", p.get("temp_c", 0)))
        t3_vals.append(p.get("t3_c") or 0)
        labels.append(p.get("phase", ""))

    has_t3 = any(v > 0 for v in t3_vals)
    use_rtc = len(rtc_times) == len(times_min) and all(t is not None for t in rtc_times)

    # X-axis data
    if use_rtc:
        x_data = mdates.date2num(rtc_times)
    else:
        x_data = times_min

    # Create figure
    fig, ax1 = plt.subplots(1, 1, figsize=(width, height), dpi=150)
    fig.patch.set_facecolor("white")

    # Pressure (left axis)
    color_p2 = "#1f4e79"
    ax1.set_ylabel("Druck P2 (mbar)", fontsize=8, color=color_p2)
    line_p2, = ax1.plot(x_data, p2_vals, color=color_p2, linewidth=1.5, label="P2 Kammerdruck", alpha=0.9)
    ax1.tick_params(axis="y", labelcolor=color_p2, labelsize=7)
    ax1.tick_params(axis="x", labelsize=6)
    ax1.grid(True, alpha=0.15)
    ax1.set_xlim(min(x_data), max(x_data))

    # X-axis formatting
    if use_rtc:
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax1.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        ax1.set_xlabel("Uhrzeit", fontsize=8, color="#666")
        # Add secondary x-axis for process time
        ax_top = ax1.twiny()
        ax_top.set_xlim(min(times_min), max(times_min))
        ax_top.set_xlabel("Prozesszeit (min)", fontsize=7, color="#999")
        ax_top.tick_params(labelsize=6, colors="#999")
    else:
        ax1.set_xlabel("Prozesszeit (min)", fontsize=8, color="#666")

    # Temperature (right axis)
    ax2 = ax1.twinx()
    color_t2 = "#dc3545"
    color_t3 = "#fd7e14"
    ax2.set_ylabel("Temperatur (\u00b0C)", fontsize=8, color=color_t2)
    line_t2, = ax2.plot(x_data, t2_vals, color=color_t2, linewidth=1.5, label="T2 Kammer", alpha=0.9)
    if has_t3:
        line_t3, = ax2.plot(x_data, t3_vals, color=color_t3, linewidth=1.2,
                            linestyle="--", label=t3_label, alpha=0.8)
    ax2.tick_params(axis="y", labelcolor=color_t2, labelsize=7)

    # Phase annotations
    last_label = ""
    for i, lbl in enumerate(labels):
        if lbl != last_label and lbl:
            ax1.axvline(x=x_data[i], color="#ddd", linewidth=0.5, linestyle=":")
            if i == 0 or (times_min[i] - times_min[max(0, i - 1)]) > 1:
                ax1.text(x_data[i], ax1.get_ylim()[1] * 0.97, lbl,
                         fontsize=4, rotation=45, ha="left", va="top",
                         color="#888", alpha=0.7)
            last_label = lbl

    # Legend
    handles = [line_p2, line_t2]
    if has_t3:
        handles.append(line_t3)
    ax1.legend(handles=handles, loc="upper left", fontsize=6, framealpha=0.9)

    fig.suptitle("Prozessverlauf", fontsize=10, fontweight="bold", color="#1f4e79", y=0.98)
    plt.tight_layout()

    if not output_path:
        output_path = tempfile.mktemp(suffix=".png", prefix="docupi_chart_")

    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info(f"Chart erzeugt: {output_path}")
    return output_path
