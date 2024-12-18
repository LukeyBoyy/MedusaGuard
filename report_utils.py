import os
import io
import time
import re
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba
from matplotlib.patches import Patch
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from pandas.api.types import CategoricalDtype
from datetime import datetime, timedelta
from pathlib import Path
from termcolor import colored
from logger import logger


# -------------------- #
#  Header & Footer     #
# -------------------- #

def add_first_page_header(canvas, doc):
    """
    Add a header image and page number to the first page.

    This function is used as a callback by the ReportLab library to add a header
    and page numbers to the first page of the PDF document during generation.

    Args:
        canvas (Canvas): The canvas object representing the current page.
        doc (DocumentTemplate): The document template being used.
    """
    # Add the header image
    header_image_path = "assets/pdf_header.png"  # Path to your header image

    if os.path.exists(header_image_path):
        canvas.drawImage(header_image_path, 30, doc.pagesize[1] - 80, width=550, height=50)
    else:
        print(colored(f"[WARNING] Header image not found at path: {header_image_path}", "red"))

    # Add the page number at the footer
    page_num = canvas.getPageNumber()
    text = f"{page_num} | Page"

    # Draw a line above the page number (horizontally across the width of the page)
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setLineWidth(0.5)
    canvas.line(10 * mm, 20 * mm, 200 * mm, 20 * mm)

    # Set font and draw the page number text
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(200 * mm, 15 * mm, text)


def add_later_page_number(canvas, doc):
    """
    Add a page number to the canvas footer for later pages.

    This function is used as a callback by the ReportLab library to add page numbers
    to the PDF document during generation for all pages except the first one.

    Args:
        canvas (Canvas): The canvas object representing the current page.
        doc (DocumentTemplate): The document template being used.
    """
    # Get the current page number
    page_num = canvas.getPageNumber()
    text = f"{page_num} | Page"

    # Draw a line above the page number (horizontally across the width of the page)
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setLineWidth(0.5)
    canvas.line(10 * mm, 20 * mm, 200 * mm, 20 * mm)

    # Set font and draw the page number text
    canvas.setFont("Helvetica", 10)
    canvas.drawRightString(200 * mm, 15 * mm, text)


# -------------------- #
#   Helper Functions   #
# -------------------- #

def load_asset_criticality_scores(acs_file_path):
    """
    Load Asset Criticality Scores from a CSV file.

    Args:
        acs_file_path (str): Path to the ACS CSV file.

    Returns:
        dict: A dictionary mapping IP addresses to ACS scores.
    """
    if not os.path.exists(acs_file_path):
        logger.info("ACS file not found. All ACS values will default to 1.")
        return {}
    try:
        acs_df = pd.read_csv(acs_file_path, comment='#')
        # Ensure ACS is an integer between 1 and 5
        acs_df['ACS'] = pd.to_numeric(acs_df['ACS'], errors='coerce').fillna(1).astype(int)
        acs_df['ACS'] = acs_df['ACS'].clip(lower=1, upper=5)
        acs_dict = pd.Series(acs_df.ACS.values, index=acs_df.IP).to_dict()
        logger.info(f"Loaded ACS for {len(acs_dict)} hosts.")
        return acs_dict
    except Exception as e:
        logger.error(f"Failed to load ACS file: {e}")
        return {}


def parse_metasploit_report(report_path):
    """
    Parse the Metasploit TXT report and extract exploitation data.

    Args:
        report_path (str): Path to the Metasploit TXT report.

    Returns:
        dict: A dictionary containing exploited CVEs, exploit details, payload statistics, and CVEs without exploits.
    """
    exploited_cves = []
    cves_without_exploits = []
    total_cves_examined = 0
    total_exploited = 0
    incompatible_cves = 0

    # Regular expressions to match relevant lines
    cve_found_re = re.compile(r"\[(.*?)\] Exploitable CVE Found: (CVE-\d{4}-\d+)")
    exploit_identified_re = re.compile(r"\[(.*?)\] Identified Exploit: (.+)")
    target_ip_re = re.compile(r"Target IP: (\d+\.\d+\.\d+\.\d+)")
    target_port_re = re.compile(r"Target Port: (\d+)")
    payload_stats_re = re.compile(r"Payload Statistics:")
    summary_re = re.compile(r"Total CVEs examined: (\d+)\s+Total exploited CVEs: (\d+)\s+Incompatible CVEs: (\d+)")

    current_exploit = {}
    payload_total = payload_successful = payload_failed = None
    capturing_payload_stats = False
    in_cve_without_exploits_section = False

    with open(report_path, 'r') as file:
        for line in file:
            line = line.strip()

            # Detect the section listing CVEs without exploits
            if "The following CVEs were detected, but Metasploit does not have an exploit to target these." in line:
                in_cve_without_exploits_section = True
                # Skip the next line (the one that says "Search results from ExploitDB...")
                next(file, None)
                continue

            if in_cve_without_exploits_section:
                # Detect end of the CVEs section
                if line.startswith("End of Report Summary"):
                    in_cve_without_exploits_section = False
                    continue
                # Check if the line starts with 'CVE-'
                if line.startswith("CVE-"):
                    cves_without_exploits.append(line)
                continue

            # Check for Exploitable CVE Found
            cve_found_match = cve_found_re.search(line)
            if cve_found_match:
                current_exploit['cve'] = cve_found_match.group(2)
                continue

            # Check for Identified Exploit
            exploit_identified_match = exploit_identified_re.search(line)
            if exploit_identified_match:
                current_exploit['exploit'] = exploit_identified_match.group(2)
                continue

            # Check for Target IP
            target_ip_match = target_ip_re.search(line)
            if target_ip_match:
                current_exploit['target_ip'] = target_ip_match.group(1)
                continue

            # Check for Target Port
            target_port_match = target_port_re.search(line)
            if target_port_match:
                current_exploit['target_port'] = target_port_match.group(1)
                continue

            # Check for Payload Statistics
            if payload_stats_re.search(line):
                capturing_payload_stats = True
                continue

            if capturing_payload_stats:
                if line.startswith("Total:"):
                    payload_total = int(line.split("Total:")[1].strip())
                elif line.startswith("Successful:"):
                    payload_successful = int(line.split("Successful:")[1].strip())
                elif line.startswith("Failed:"):
                    payload_failed = int(line.split("Failed:")[1].strip())
                    # After capturing all payload stats, append the exploit
                    if current_exploit:
                        current_exploit['payload_total'] = payload_total
                        current_exploit['payload_successful'] = payload_successful
                        current_exploit['payload_failed'] = payload_failed
                        exploited_cves.append(current_exploit.copy())
                        current_exploit = {}
                        # Reset payload stats
                        payload_total = payload_successful = payload_failed = None
                        capturing_payload_stats = False
                continue

            # Check for Summary
            summary_match = summary_re.search(line)
            if summary_match:
                total_cves_examined = int(summary_match.group(1))
                total_exploited = int(summary_match.group(2))
                incompatible_cves = int(summary_match.group(3))
                continue

    parsed_data = {
        "exploited_cves": exploited_cves,
        "cves_without_exploits": cves_without_exploits,
        "total_cves_examined": total_cves_examined,
        "total_exploited_cves": total_exploited,
        "incompatible_cves": incompatible_cves
    }

    return parsed_data


def load_historical_data(file_path):
    """
    Load historical scan counts from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        list: List of historical scan records.
    """
    if not os.path.exists(file_path):
        logger.info(f"Historical data file not found. Creating a new one at {file_path}.")
        return []
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} historical records.")
            return data
    except json.JSONDecodeError:
        logger.error(f"JSON decode error. The file {file_path} might be corrupted.")
        return []
    except Exception as e:
        logger.error(f"Failed to load historical data: {e}")
        return []


def save_historical_data(file_path, data):
    """
    Save historical scan counts to a JSON file.

    Args:
        file_path (str): Path to the JSON file.
        data (list): List of historical scan records.
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
            logger.info(f"Saved {len(data)} records to {file_path}.")
    except Exception as e:
        logger.error(f"Failed to save historical data: {e}")


def append_scan_result(data, high_count, medium_count, low_count, timestamp=None):
    """
    Append a new scan result to the historical data.

    Args:
        data (list): Existing historical data.
        high_count (int): Number of high-severity vulnerabilities.
        medium_count (int): Number of medium-severity vulnerabilities.
        low_count (int): Number of low-severity vulnerabilities.
        timestamp (str, optional): Specific timestamp for the scan. If None, current time is used.

    Returns:
        list: Updated historical data.
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = {
        "timestamp": timestamp,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count
    }
    data.append(new_entry)
    logger.info(f"Appended new scan result at {timestamp}.")
    return data


def generate_line_graph(data, graph_path):
    """
    Generate a line graph from historical scan data.

    Args:
        data (list): Historical scan data.
        graph_path (str): Path to save the generated graph.
    """
    if len(data) < 2:
        logger.info("Not enough data points to generate a line graph. Skipping graph generation.")

    # Convert data to DataFrame for easier plotting
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values('timestamp', inplace=True)

    plt.figure(figsize=(6.75, 3.375))

    high_color = '#d43f3a'
    medium_color = '#fdc432'
    low_color = '#3eae49'

    # Plotting the lines
    plt.plot(
        df['timestamp'], df['high_count'],
        marker='o', linestyle='-', linewidth=4, alpha=1.0,
        label='High Count', color=high_color, markersize=7
    )
    plt.plot(
        df['timestamp'], df['medium_count'],
        marker='o', linestyle='-', linewidth=2, alpha=0.7,
        label='Medium Count', color=medium_color, markersize=5
    )
    plt.plot(
        df['timestamp'], df['low_count'],
        marker='o', linestyle='-', linewidth=2, alpha=0.5,
        label='Low Count', color=low_color, markersize=5
    )

    plt.xlabel('Timestamp', fontsize=8)
    plt.ylabel('Vulnerability Count', fontsize=8)
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    plt.title('Vulnerability Counts Over Time', fontsize=10, fontweight='bold')
    plt.legend(loc='upper left', fontsize=8, frameon=False)

    # Gridlines
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, color='lightgray', alpha=0.5)

    # Improve date formatting on x-axis
    plt.gcf().autofmt_xdate()  # Auto-format the x-axis labels for better readability

    # Removes the top and right spines for a cleaner look
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    try:
        plt.savefig(graph_path, bbox_inches="tight", dpi=300)
        plt.close()
        logger.info(f"Line graph generated and saved to {graph_path}.")
    except Exception as e:
        logger.eror(f"Failed to save line graph: {e}")


# -------------------- #
#   Report Generation  #
# -------------------- #

def generate_report(
    csv_path,
    task_name,
    hosts_count,
    high_count,
    medium_count,
    low_count,
    os_count,
    apps_count,
    reportname,
    exploitedcves,
    incompatiblecves,
    nikto_csv_path=None,
    nuclei_combined_output_file=None,
):
    """
    Generate an executive PDF report based on the scan results.

    This function creates a detailed PDF report that includes:
    - Pie and bar charts summarizing the vulnerabilities.
    - A summary of vulnerabilities and key findings.
    - Recommendations and conclusions.
    - Appendices with definitions and detailed vulnerability lists.
    - Optionally, includes Nikto scan results if provided.

    Args:
        csv_path (str): Path to the CSV file containing the OpenVAS scan results.
        task_name (str): Name of the task for which the report is generated.
        hosts_count (int): Number of hosts that were scanned.
        high_count (int): Number of high-severity vulnerabilities found.
        medium_count (int): Number of medium-severity vulnerabilities found.
        low_count (int): Number of low-severity vulnerabilities found.
        os_count (int): Number of operating systems scanned.
        apps_count (int): Number of applications scanned.
        reportname (str): Name of the metasploit report.
        exploitedcves (int): Number of exploited CVEs.
        incompatiblecves (int): Number of incompatible CVEs.
        nikto_csv_path (str, optional): Path to the Nikto scan results CSV file. Defaults to None.
        nuclei_combined_output_file (str, optional): Path to the combined nuclei scan results. Defaults to None.
    """
    # Generate a timestamp for filenames
    completion_time = time.strftime("%H-%M-%S_%Y-%m-%d")

    # Create directories for output files if they don't exist
    result_graphs_dir = "result_graphs"
    os.makedirs(result_graphs_dir, exist_ok=True)

    # Define paths for the output files
    rep_csv_path = Path(csv_path)
    out_path = os.path.join(
        "custom_reports", f"{task_name}_executive_report_{completion_time}.pdf"
    )
    output_pdf_path = out_path
    pie_out = os.path.join(
        result_graphs_dir, f"{task_name}_piechart_{completion_time}.png"
    )
    pie_chart_path = pie_out
    exploit_pie_out = os.path.join(
        result_graphs_dir, f"{task_name}_exploitpiechart_{completion_time}.png"
    )
    exploit_pie_chart_path = exploit_pie_out
    gui_pie_out = os.path.join(
        result_graphs_dir, f"vuln_pie.png"
    )
    gui_pie_out = gui_pie_out
    gui_exploit_pie_out = os.path.join(
        result_graphs_dir, f"exploit_pie.png"
    )
    gui_exploit_pie_out = gui_exploit_pie_out

    # Load and process CSV data from OpenVAS scan results
    df = pd.read_csv(rep_csv_path)
    df = df.astype(str).fillna("Value not found")
    df["CVSS"] = pd.to_numeric(df["CVSS"], errors="coerce")

    # Summarise counts
    total_vulns = high_count + medium_count + low_count
    high_vulns = high_count
    medium_vulns = medium_count
    low_vulns = low_count
    hosts_scanned = hosts_count
    apps_count = apps_count
    os_count = os_count

    # Define paths for historical data and the line graph
    historical_data_file = "historical_results.json"
    historical_graph_out = os.path.join(
        result_graphs_dir, f"{task_name}_historical_counts_{completion_time}.png"
    )

    # Sort vulnerabilities by CVSS score for reporting
    top_vulns = df.sort_values(by="CVSS", ascending=False)

    # Prepare data for the pie chart (vulnerability severity distribution)
    labels = ["High", "Medium", "Low"]
    colors_list = ["#d43f3a", "#fdc432", "#3eae49"]  # Red, Orange, Green
    sizes = [high_vulns, medium_vulns, low_vulns]

    # Prepare data for the pie chart (exploit results)
    exploit_labels = ["Successful", "Unsuccessful"]
    exploit_color_list = ["#009688", "#FF6F61"]
    exploit_sizes = [exploitedcves, incompatiblecves]


    # Prepare data for the bar chart (scan information)
    #bar_legend_labels = ["Systems", "Applications", "Operating Systems"]
    #bar_sizes = [hosts_count, os_count, apps_count]
    #bar_colors = ["#bbeeff", "#3366ff", "#77aaff"]  # Shades of blue

    # Load and process Nikto CSV data if provided
    if nikto_csv_path and os.path.exists(nikto_csv_path):
        # Read the file content
        with open(nikto_csv_path, "r") as file:
            lines = file.readlines()

        # Filter out lines that start with "Nikto" or are empty
        data_lines = [
            line
            for line in lines
            if not line.startswith('"Nikto') and line.strip() != ""
            and line.strip() != ""
            and not line.startswith('Host IP')
        ]

        # Check if there are any data lines
        if data_lines:
            # Create a string from the data_lines
            data_str = "".join(data_lines)

            # Use io.StringIO to read the data into pandas
            nikto_df = pd.read_csv(io.StringIO(data_str), header=None)
            nikto_df.columns = [
                "Host",
                "IP",
                "Port",
                "Reference",
                "Method",
                "URI",
                "Description",
                "MID",
                "DID",
            ]
            nikto_df.fillna("N/A", inplace=True)
        else:
            nikto_df = None
    else:
        nikto_df = None

    try:
        # Generate the pie chart for vulnerabilities
        fig1, ax1 = plt.subplots(figsize=(3.5, 3.5))
        wedges, texts = ax1.pie(
            sizes,
            labels=labels,
            colors=colors_list,
            startangle=90,
            wedgeprops=dict(width=0.6, edgecolor="white"),
            textprops=dict(color="black", fontsize=10),
        )

        # Add a center circle to make it a donut chart
        center_circle = plt.Circle((0, 0), 0.60, fc="white")
        fig1.gca().add_artist(center_circle)

        # Set the title and legend
        ax1.set_title("Vulnerabilities", fontsize=12, fontweight="bold", pad=15)
        ax1.legend(
            wedges,
            labels,
            title="Severity",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=10,
        )

        plt.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle

        # Save the pie chart image
        plt.savefig(pie_chart_path, bbox_inches="tight", dpi=300)
        plt.close(fig1)  # Close the figure to free memory
    except Exception as e:
        print(colored(f"[ERROR] Failed to generate pie graph: {e}", "red"))

    # Generate the pie chart for exploits
    try:
        fig1, ax1 = plt.subplots(figsize=(3.5, 3.5))
        wedges, texts = ax1.pie(
            exploit_sizes,
            labels=exploit_labels,
            colors=exploit_color_list,
            startangle=90,
            wedgeprops=dict(width=0.6, edgecolor="white"),
            textprops=dict(color="black", fontsize=10),
        )

        # Add a center circle to make it a donut chart
        center_circle = plt.Circle((0, 0), 0.60, fc="white")
        fig1.gca().add_artist(center_circle)

        # Set the title and legend
        ax1.set_title("Exploits", fontsize=12, fontweight="bold", pad=15)
        ax1.legend(
            wedges,
            exploit_labels,
            title="Exploit Status",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=10,
        )

        plt.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle

        # Save the pie chart image
        plt.savefig(exploit_pie_out, bbox_inches="tight", dpi=300)
        plt.close(fig1)  # Close the figure to free memory
    except Exception as e:
        print(colored(f"[ERROR] Failed to generate exploits pie chart: {e}", "red"))

    try:
        gui_vuln_labels = ['High', 'Medium', 'Low']
        gui_vuln_sizes = [high_vulns, medium_vulns, low_vulns]
        gui_vuln_colors = ['#ff6f61', '#ffcc66', '#66cc66']
        explode = (0, 0, 0)  # No slice explode

        # Adjust the figure size to provide more room for the legend
        fig_vuln_gui, ax = plt.subplots(figsize=(3.12, 1.96))

        # Create the pie chart
        ax.pie(gui_vuln_sizes, labels=None, colors=gui_vuln_colors, autopct=lambda p: f'{round(p * sum(gui_vuln_sizes) / 100)}',
               startangle=90, explode=explode, textprops={'fontsize': 8})

        fig_vuln_gui.patch.set_alpha(0)  # Makes the background transparent

        # Create custom legend with circle markers and no lines
        legend_elements = [Line2D([0], [0], marker='o', color='w', label=label, markersize=7,
                                  markerfacecolor=color, linestyle='None')
                           for label, color in zip(gui_vuln_labels, gui_vuln_colors)]

        # Place the legend closer to the pie chart
        legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(0.85, 0.5), frameon=False,
                           fontsize=8)

        for text in legend.get_texts():
            text.set_color("white")

        plt.savefig(gui_pie_out, bbox_inches="tight")
        plt.close(fig_vuln_gui)  # Close the figure to free memory
    except Exception as e:
        print(colored(f"[ERROR] Failed to generate GUI vuln pie chart: {e}", "red"))

    # Generate the pie graph for the GUI result section (exploits)
    try:
        explode = (0, 0)  # No slice explode
        # Adjust the figure size to provide more room for the legend
        fig_exp_gui, ax = plt.subplots(figsize=(3.12, 1.96))
        # Create the pie chart
        ax.pie(exploit_sizes, labels=None, colors=exploit_color_list,
               autopct=lambda p: f'{round(p * sum(exploit_sizes) / 100)}',
               startangle=90, explode=explode, textprops={'fontsize': 8})
        fig_exp_gui.patch.set_alpha(0)  # Makes the background transparent
        # Create custom legend with circle markers and no lines
        legend_elements = [Line2D([0], [0], marker='o', color='w', label=label, markersize=7,
                                  markerfacecolor=color, linestyle='None')
                           for label, color in zip(exploit_labels, exploit_color_list)]
        # Place the legend closer to the pie chart
        legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(0.85, 0.5), frameon=False,
                           fontsize=8)
        for text in legend.get_texts():
            text.set_color("white")
        plt.savefig(gui_exploit_pie_out, bbox_inches="tight")
        plt.close(fig_exp_gui)  # Close the figure to free memory
    except Exception as e:
        print(colored(f"[ERROR] Failed to generate GUI exploit pie chart: {e}", "red"))

    # -------------------- #
    # Historical Data      #
    # -------------------- #

    # Historical Vulnerability Counts
    try:
        # Load existing historical data
        historical_data = load_historical_data(historical_data_file)

        # Capture the current timestamp
        current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Append the current scan results
        historical_data = append_scan_result(
            historical_data,
            high_count=high_vulns,
            medium_count=medium_vulns,
            low_count=low_vulns,
            timestamp=current_timestamp
        )

        # Save the updated historical data
        save_historical_data(historical_data_file, historical_data)

        # Generate the historical line graph
        generate_line_graph(historical_data, historical_graph_out)

        # Check if the graph was generated successfully
        if os.path.exists(historical_graph_out):
            graph_generated = True
        else:
            graph_generated = False
    except Exception as e:
        logger.error(f"Failed to process historical data: {e}")
        graph_generated = False

    # -------------------- #
    #    PDF Document      #
    # -------------------- #

    try:
        # Initialize the PDF document
        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
        )

        elements = []  # List to hold the flowable elements of the PDF

        # Styles for the PDF
        styles = getSampleStyleSheet()
        styleN = styles["BodyText"]
        styleH = styles["Heading1"]
        styleTitle = styles["Title"]
        styleH.fontSize = 15
        styleH.leading = 17

        # Centered paragraph style
        centered_style = ParagraphStyle(
            name="Centered",
            alignment=1,  # Center the text
            fontSize=10,
            leading=14,  # Line height
            fontName="Helvetica",
        )

        # -------------------- #
        #     Title Page       #
        # -------------------- #

        # --- Build the Title Page ---
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(
            Paragraph("Vulnerability Scanning and Exploitation Report", styleTitle)
        )
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"Automated Security Assessment", centered_style))
        elements.append(Paragraph(f"Created by: MedusaGuard v1.0", centered_style))
        elements.append(
            Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", centered_style)
        )

        # Confidentiality note in italicized font
        confidentiality_style = ParagraphStyle(
            name="Confidentiality",
            fontSize=9,
            textColor=colors.HexColor("#666666"),
            fontName="Helvetica-Oblique",
            leading=12,
        )

        # Report summary style
        rep_summary_style = ParagraphStyle(
            name="Centered",
            fontSize=10,
            leading=14,  # Line height
            fontName="Helvetica",
        )

        elements.append(Spacer(1, 0.3 * inch))
        elements.append(
            Paragraph(
                "This document contains the results of the automated vulnerability scanning and exploitation tool known as MedusaGuard. "
                "It outlines identified vulnerabilities, their potential impacts, and suggested remediation strategies "
                "along with whether or not they are exploitable.",
                rep_summary_style,
            )
        )
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(
            Paragraph(
                "This document is confidential and intended solely for the use of the client. "
                "Unauthorized access, disclosure, or distribution is strictly prohibited.",
                confidentiality_style,
            )
        )

        elements.append(Spacer(1, 0.5 * inch))

        # -------------------- #
        #   Table of Contents   #
        # -------------------- #

        # --- Table of Contents ---
        toc_title_style = ParagraphStyle(
            name="TOCTitle",
            fontSize=10,
            fontName="Helvetica-Bold",
            alignment=1,  # Centered text
            spaceAfter=12,  # Space after the title
        )

        # Manually created Table of Contents data
        toc_data = [
            [
                "Executive Summary ................................................................................................................................................................................",
                "2",
            ],
            [
                "Key Findings ...........................................................................................................................................................................................",
                "2",
            ],
            [
                "Top 10 Vulnerabilities .............................................................................................................................................................................",
                "3",
            ],
            [
                "Recommendations ..................................................................................................................................................................................",
                "4",
            ],
            [
                "Conclusion ..............................................................................................................................................................................................",
                "4",
            ],
            [
                "Appendix 1: Definitions ...........................................................................................................................................................................",
                "4",
            ],
            [
                "Appendix 2: Recommended Actions to be Taken Based on Vulnerability Severity ................................................................................",
                "5",
            ],
            [
                "Appendix 3: Host-Level Vulnerability Metrics ..........................................................................................................................................",
                "6",
            ],
            [
                "Appendix 4: Detailed Tool Results  .........................................................................................................................................................",
                "7",
            ],
        ]

        # Create the Table of Contents table
        toc_table = Table(toc_data, colWidths=[5.7 * inch, 1 * inch])
        toc_table.setStyle(
            TableStyle(
                [
                    (
                        "ALIGN",
                        (0, 0),
                        (0, -1),
                        "LEFT",
                    ),  # Left-align the first column (section titles)
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),  # Right-align the page numbers
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )

        elements.append(Paragraph("Table of Contents", toc_title_style))
        elements.append(toc_table)
        elements.append(PageBreak())  # Start a new page

        # -------------------- #
        #   Executive Summary  #
        # -------------------- #

        # --- Executive Summary ---
        elements.append(Paragraph("1. Executive Summary", styleH))

        summary_availabe = all([
            hosts_scanned is not None,
            total_vulns is not None,
            high_vulns is not None,
            medium_vulns is not None,
            low_vulns is not None
        ])

        if summary_availabe:
            # Generate the executive summary based on the number of high vulnerabilities
            if high_vulns >= 5:
                exec_summary = (
                    f"The purpose of this security assessment was to identify weaknesses within our IT infrastructure "
                    f"that could be exploited by attackers, potentially leading to financial loss, regulatory penalties, "
                    f"or damage to our reputation. Of the {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were found, "
                    f"with {high_vulns} categorized as high, posing the most significant risk. "
                    f"Immediate remediation of any high vulnerabilities "
                    f"identified is necessary to avoid potential business disruptions and ensure the continued trust of our customers. "
                    f"This report provides detailed findings and actionable recommendations to mitigate these risks, safeguarding your operations."
                )
            elif 1 <= high_vulns < 5:
                exec_summary = (
                    f"The security assessment identified several areas of concern within the IT infrastructure. "
                    f"Out of {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were found, "
                    f"with {high_vulns} categorized as high severity. "
                    f"Timely remediation of identified vulnerabilities is recommended to enhance the security posture. "
                    f"This report provides detailed findings and actionable recommendations to address these risks."
                )
            else:
                exec_summary = (
                    f"The security assessment indicates a relatively low level of risk within the IT infrastructure. "
                    f"Out of {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were identified, "
                    f"with {high_vulns} categorized as high severity. "
                    f"While immediate risk is low, addressing identified vulnerabilities will help maintain and improve your security posture. "
                    f"This report provides detailed findings and recommendations for ongoing security enhancements."
                )

            elements.append(Paragraph(exec_summary, styleN))
        else:
            # Data is missing; inform the reader
            no_data_message = Paragraph(
                "The Executive Summary cannot be generated as essential vulnerability data is missing. "
                "Please ensure that all necessary data is provided to generate a comprehensive summary of the vulnerability scan results.",
                styleN
            )
            elements.append(no_data_message)

        elements.append(Spacer(1, 0.5 * inch))

        # -------------------- #
        #     Key Findings     #
        # -------------------- #

        # --- Key Findings ---
        elements.append(Paragraph("2. Key Findings", styleH))

        if any([high_vulns, medium_vulns, low_vulns]):
            # Styles for the vulnerability counts
            count_style = ParagraphStyle(
                name="count",
                alignment=1,  # Centered text
                fontSize=18,
                textColor=colors.whitesmoke,
                spaceAfter=6,
                fontName="Helvetica",
            )

            label_style = ParagraphStyle(
                name="label",
                alignment=1,  # Centered text
                fontSize=8,
                textColor=colors.whitesmoke,
                spaceBefore=0,
                fontName="Helvetica-Bold",
            )

            # Data for the counts table
            data = [
                [
                    Paragraph(str(high_vulns), count_style),
                    Paragraph(str(medium_vulns), count_style),
                    Paragraph(str(low_vulns), count_style),
                ],
                [
                    Paragraph("HIGH", label_style),
                    Paragraph("MEDIUM", label_style),
                    Paragraph("LOW", label_style),
                ],
            ]

            # Create the counts table
            table = Table(
                data,
                colWidths=[2.25 * inch, 2.25 * inch, 2.25 * inch],
                rowHeights=[0.75 * inch, 0.3 * inch],
            )
            table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (0, 0),
                            colors.HexColor("#E74C3C"),
                        ),  # Red background for High
                        (
                            "BACKGROUND",
                            (1, 0),
                            (1, 0),
                            colors.HexColor("#F39C12"),
                        ),  # Orange background for Medium
                        (
                            "BACKGROUND",
                            (2, 0),
                            (2, 0),
                            colors.HexColor("#2ECC71"),
                        ),  # Green background for Low
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.whitesmoke,
                        ),  # White text color for counts
                        (
                            "TEXTCOLOR",
                            (0, 1),
                            (-1, 1),
                            colors.whitesmoke,
                        ),  # White text color for labels
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),  # Center-align text in all cells
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Middle vertical alignment
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, 0),
                            "Helvetica",
                        ),  # Regular font for counts
                        (
                            "BACKGROUND",
                            (0, 1),
                            (0, 1),
                            colors.HexColor("#2C3E50"),
                        ),  # Dark background for labels
                        (
                            "BACKGROUND",
                            (1, 1),
                            (1, 1),
                            colors.HexColor("#2C3E50"),
                        ),  # Dark background for labels
                        (
                            "BACKGROUND",
                            (2, 1),
                            (2, 1),
                            colors.HexColor("#2C3E50"),
                        ),  # Dark background for labels
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.75,
                            colors.whitesmoke,
                        ),  # Thicker border around the table
                    ]
                )
            )

            # Add the heading
            heading = Paragraph(
                "Vulnerability count:",
                ParagraphStyle(
                    name="Heading1",
                    fontSize=10,
                    alignment=0,  # Aligned-left
                    textColor=colors.black,
                    spaceAfter=12,  # Space after the heading
                    fontName="Helvetica",
                ),
            )

            elements.append(heading)
            elements.append(table)
            elements.append(Spacer(1, 0.25 * inch))

            if os.path.exists(pie_chart_path) and os.path.exists(exploit_pie_chart_path):
                # Add the pie chart and bar chart side by side
                chart_table = Table(
                    [
                        [
                            Image(pie_chart_path, width=2.50 * inch, height=2 * inch),
                            Image(exploit_pie_chart_path, width=2.50 * inch, height=2 * inch),
                        ]
                    ],
                    colWidths=[2.875 * inch, 2.875 * inch],
                )
                chart_table.setStyle(
                    TableStyle(
                        [
                            ("LEFTPADDING", (0, 0), (-1, -1), 12),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                            ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ]
                    )
                )
                elements.append(chart_table)
                elements.append(Spacer(1, 0.5 * inch))

                # Add the Historical Line Graph
                if graph_generated:
                    # Create a new table row for the line graph
                    historical_graph_table = Table(
                        [
                            [
                                Image(historical_graph_out, width=6.75 * inch, height=3.375 * inch)
                            ]
                        ],
                        colWidths=[6.75 * inch]
                    )
                    historical_graph_table.setStyle(
                        TableStyle(
                            [
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ]
                        )
                    )
                    elements.append(historical_graph_table)
                    elements.append(Spacer(1, 0.5 * inch))
            else:
                # If charts are missing, display a message
                no_charts_message = Paragraph(
                    "Charts illustrating the vulnerability distribution are not available.", styleN
                )
                elements.append(no_charts_message)
                elements.append(Spacer(1, 0.5 * inch))
        else:
            # If no vulnerabilities are found, display a message
            no_vuln_message = Paragraph(
                "No vulnerabilities were found during the scan (likely an error).", styleN
            )
            elements.append(no_vuln_message)

        # -------------------- #
        # Top 10 Vulnerabilities#
        # -------------------- #

        # --- Top 10 Vulnerabilities ---
        elements.append(Paragraph("3. Top 10 Vulnerabilities", styleH))
        top_10_text = (
            "The following table details the top 10 most critical vulnerabilities identified in the scan. It is ordered from "
            "most significant risk to least significant risk, with a CVSS score of 10.0 being the highest score possible "
            "awarded to vulnerabilities that pose a major risk. Please refer to the definitions table in the appendix "
            "if any of the terms are unknown to you."
        )
        elements.append(Paragraph(top_10_text, styleN))

        # Prepare data for the vulnerabilities table
        vuln_data = [["Vulnerability", "CVSS", "Impact", "Remediation"]]
        # Set to track unique vulnerabilities
        unique_vulns = set()

        # Iterate over the sorted vulnerabilities to get the top 10 unique entries
        for i, (_, row) in enumerate(top_vulns.iterrows()):
            vuln_name = row["NVT Name"]

            # Check if the vulnerability is already in the set
            if vuln_name not in unique_vulns:
                # Add it to the set if it's not already present
                unique_vulns.add(vuln_name)

                # Append the row to the table data
                vuln_data.append(
                    [
                        Paragraph(
                            str(vuln_name), styleN
                        ),  # Wrap text in the 'Vulnerability' column
                        Paragraph(str(row["CVSS"]), styleN),  # CVSS score as a string
                        Paragraph(
                            str(row["Impact"]), styleN
                        ),  # Convert to string and wrap text in the 'Impact' column
                        Paragraph(
                            str(row["Solution"]), styleN
                        ),  # Convert to string and wrap text in the 'Remediation' column
                    ]
                )

                if len(vuln_data) > 10:
                    break  # Stop after adding 10 vulnerabilities

        # Conditional check: if there are vulnerabilities beyond the header, add the table; else, add a message
        if len(vuln_data) > 1:
            # Create the vulnerabilities table
            vuln_table = Table(
                vuln_data, colWidths=[1.3 * inch, 0.5 * inch, 2.6 * inch, 2.3 * inch]
            )
            vuln_table_style = TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#2C3E50"),
                    ),  # Blue background for the header row
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.whitesmoke,
                    ),  # White text color for the header row
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "LEFT",
                    ),  # Left-align text for better readability
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),  # Reduced font size for better fit
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (1, 0), (-1, -1), 8),
                    ("TOPPADDING", (1, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.75,
                        colors.black,
                    ),  # Thicker border around the table
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),  # Align text to the top of each cell
                ]
            )

            # Manually alternate row background colors
            for i in range(1, len(vuln_data)):
                if i % 2 == 0:
                    bg_color = colors.HexColor("#EAECEE")  # Light gray
                else:
                    bg_color = colors.HexColor("#F2F3F4")
                vuln_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

            vuln_table.setStyle(vuln_table_style)
            elements.append(Spacer(1, 0.25 * inch))
            elements.append(vuln_table)
        else:
            # No vulnerabilities found
            no_vuln_message = Paragraph(
                "No vulnerabilities were found during the scan.", styleN
            )
            elements.append(no_vuln_message)

        elements.append(Spacer(1, 0.75 * inch))

        # -------------------- #
        #    Recommendations   #
        # -------------------- #

        # --- Recommendations ---
        elements.append(Paragraph("4. Recommendations", styleH))
        recommendations = (
            "Immediately address any critical vulnerabilities, continue to perform regular security assessments, "
            "and allocate resources to strengthen the security posture of our organization. "
            "We strongly recommend establishing a continuous vulnerability management program, including regular security "
            "assessments and timely remediation of any identified high-risk vulnerabilities. By proactively managing vulnerabilities, "
            "the organisation can significantly reduce risk and ensure compliance with industry regulations and best practices. "
            "In addition, it is highly advisable to leverage robust security tools to verify these findings and validate remediation efforts. "
            "Tools like Tenable Nessus, Qualys, and Rapid7 InsightVM are industry-standard vulnerability scanners that can provide a secondary layer of assurance. "
            "Furthermore, manual exploitation of CVEs that were identified is recommended."
        )
        elements.append(Paragraph(recommendations, styleN))
        elements.append(Spacer(1, 0.75 * inch))

        # -------------------- #
        #      Conclusion      #
        # -------------------- #

        # --- Conclusion ---
        elements.append(Paragraph("5. Conclusion", styleH))
        conclusion = (
                f"In conclusion, the assessment identified a total of {total_vulns} vulnerabilities "
                f"across {hosts_scanned} hosts, with {high_vulns} high-risk, {medium_vulns} medium-risk, and "
                f"{low_vulns} low-risk vulnerabilities. The presence of high-risk vulnerabilities indicates a significant "
                "threat to the organisation. Immediate action is required to remediate high-risk vulnerabilities to prevent "
                "potential breaches that could lead to financial, reputational, or regulatory damages."
        )
        elements.append(Paragraph(conclusion, styleN))
        elements.append(Spacer(1, 0.75 * inch))
        elements.append(PageBreak())

        # -------------------- #
        #      Appendices      #
        # -------------------- #

        # -------------------- #
        #  Appendix 1: Definitions #
        # -------------------- #

        # --- Appendices ---

        # Appendix: Definitions
        elements.append(Paragraph("Appendix 1: Definitions", styleH))
        definitions_data = [
            ["Term", "Definition"],
            [
                Paragraph("CVE (Common Vulnerabilities and Exposure)", styleN),
                Paragraph(
                    "A list of publicly disclosed computer security flaws, each identified by a unique number called a CVE ID.",
                    styleN,
                ),
            ],
            [
                Paragraph("Severity", styleN),
                Paragraph(
                    "The level of impact that a vulnerability could have on the organisation, categorised as High, Medium, or Low with high being the most critical, etc.",
                    styleN,
                ),
            ],
            [
                Paragraph("Exploit", styleN),
                Paragraph(
                    "A piece of code or technique that takes advantage of a vulnerability to compromise a system.",
                    styleN,
                ),
            ],
            [
                Paragraph("Vulnerability", styleN),
                Paragraph(
                    "A weakness in a system that can be exploited by an attacker to perform malicious actions.",
                    styleN,
                ),
            ],
            [
                Paragraph("Vulnerability Scan", styleN),
                Paragraph(
                    "Automated process that identifies, evaluates, and reports potential security weaknesses in an organisation’s IT systems.",
                    styleN,
                ),
            ],
            [
                Paragraph("DID (Detection ID)", styleN),
                Paragraph(
                    "Detection ID (DID) is a unique identifier assigned to each individual occurrence of a vulnerability on a specific asset.",
                    styleN,
                ),
            ],
            [
                Paragraph("Quality of Detection (QoD)", styleN),
                Paragraph(
                    "A metric used in OpenVAS scanning to represent the confidence level or reliability of a detected vulnerability. QoD values are expressed as percentages, with higher percentages indicating greater confidence in the accuracy of the detection.",
                    styleN,
                ),
            ],
            [
                Paragraph("Asset Criticality Score (ACS)", styleN),
                Paragraph(
                    "A numerical value from 1 to 5 assigned to an asset to indicate its importance or criticality to the organisation. Higher scores denote higher criticality, which may warrant prioritising remediation efforts. For example, an asset with a criticality score of 5 is a highly critical asset and should be prioritised accordingly. The default ACS is 1. ",
                    styleN,
                ),
            ],
        ]

        definitions_table = Table(definitions_data, colWidths=[2.3 * inch, 4.4 * inch])
        definitions_table_style = TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#2C3E50"),
                ),  # Blue background for the header row
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),  # White text color for the header row
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),  # Left-align text
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (1, 0), (-1, -1), 8),
                ("TOPPADDING", (1, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.75,
                    colors.black,
                ),  # Thicker border around the table
            ]
        )

        # Manually alternate row background colors for definitions table
        for i in range(1, len(definitions_data)):
            if i % 2 == 0:
                bg_color = colors.HexColor("#EAECEE")  # Light gray
            else:
                bg_color = colors.HexColor("#F2F3F4")
            definitions_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

        definitions_table.setStyle(definitions_table_style)
        elements.append(definitions_table)
        elements.append(Spacer(1, 0.75 * inch))
        elements.append(PageBreak())

        # -------------------- #
        # Appendix 2: Recommended Actions #
        # -------------------- #

        # Appendix: Recommended Actions
        elements.append(
            Paragraph(
                "Appendix 2: Recommended Actions to be Taken Based on Vulnerability Severity",
                styleH,
            )
        )
        reccomended_actions_text = (
            "The following table outlines the recommended actions that should be taken based on vulnerability severity. "
            "It serves as a point of reference when analysing the report so when, for example, you discover a high vulnerability "
            "you can refer to this table to determine what actions should be taken."
        )
        elements.append(Paragraph(reccomended_actions_text, styleN))
        elements.append(Spacer(1, 0.25 * inch))
        actions_data = [
            ["Severity", "Description", "Recommended Actions"],
            [
                Paragraph("High", styleN),
                Paragraph(
                    "Vulnerabilities that pose an immediate threat to the organisation and could lead to significant business impact if exploited.",
                    styleN,
                ),
                Paragraph(
                    "1. Immediate remediation within 24 hours.<br/>2. Apply security patches or mitigations.<br/>3. Increase monitoring on affected systems.<br/>4. Notify relevant stakeholders.",
                    styleN,
                ),
            ],
            [
                Paragraph("Medium", styleN),
                Paragraph(
                    "Vulnerabilities that have a moderate impact and could lead to significant issues if left unaddressed.",
                    styleN,
                ),
                Paragraph(
                    "1. Remediate within 7 days.<br/>2. Apply available patches or mitigations.<br/>3. Monitor for signs of exploitation.",
                    styleN,
                ),
            ],
            [
                Paragraph("Low", styleN),
                Paragraph(
                    "Vulnerabilities that have a minor impact and are less likely to be exploited but should still be addressed.",
                    styleN,
                ),
                Paragraph(
                    "1. Remediate within 30 days.<br/>2. Apply patches as part of regular maintenance.<br/>3. Monitor the situation to ensure no escalation.",
                    styleN,
                ),
            ],
        ]

        actions_table = Table(
            actions_data, colWidths=[1.2 * inch, 2.5 * inch, 3 * inch]
        )
        actions_table_style = TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#2C3E50"),
                ),  # Blue background for the header row
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),  # White text color for the header row
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),  # Left-align text
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),  # Further reduced font size
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),  # Added padding
                ("TOPPADDING", (0, 0), (-1, 0), 10),  # Added padding
                ("BOTTOMPADDING", (1, 0), (-1, -1), 8),
                ("TOPPADDING", (1, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),  # Added padding
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),  # Added padding
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.75,
                    colors.black,
                ),  # Thicker border around the table
            ]
        )

        # Manually alternate row background colors for actions table
        for i in range(1, len(actions_data)):
            if i % 2 == 0:
                bg_color = colors.HexColor("#EAECEE")  # Light gray
            else:
                bg_color = colors.HexColor("#F2F3F4")
            actions_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

        actions_table.setStyle(actions_table_style)
        elements.append(actions_table)
        elements.append(Spacer(1, 0.75 * inch))  # Increased spacing
        elements.append(PageBreak())

        # -------------------- #
        # Appendix 3: Host-Level Vulnerability Metrics #
        # -------------------- #

        acs_file_path = "acs_scores.csv"  # Replace with your ACS file path
        acs_dict = load_asset_criticality_scores(acs_file_path)

        # Appendix: Host-Level Vulnerability Metrics
        elements.append(Paragraph("Appendix 3: Host-Level Vulnerability Metrics", styleH))

        host_metrics_description = (
            "This section provides a detailed analysis of vulnerability metrics at the host level. "
            "Specifically, it includes the median and maximum CVSS (Common Vulnerability Scoring System) scores for each host identified during the assessment. "
            "The median CVSS score offers a robust average that minimises the impact of outliers, while the maximum CVSS score highlights the most severe vulnerability present on each host. "
            "By presenting average CVSS scores per host, this section helps prioritise remediation efforts by identifying the most vulnerable systems in the network. "
            "It offers actionable insights into which hosts require immediate attention based on their overall risk profile."
        )

        elements.append(Paragraph(host_metrics_description, styleN))
        elements.append(Spacer(1, 0.25 * inch))

        # Read the CSV file into a DataFrame
        df_host_metrics = pd.read_csv(csv_path)

        # Clean the IP column
        df_host_metrics['IP'] = df_host_metrics['IP'].astype(str).str.strip().str.lower()
        df_host_metrics = df_host_metrics[df_host_metrics['IP'].notnull() & (df_host_metrics['IP'] != '')]

        # Exclude rows where CVSS is NaN or zero
        df_valid_cvss_host = df_host_metrics.dropna(subset=['CVSS'])
        df_valid_cvss_host = df_valid_cvss_host[df_valid_cvss_host['CVSS'] > 0]

        # Compute host-level metrics
        host_metrics = df_valid_cvss_host.groupby('IP').agg(
            Median_CVSS=('CVSS', 'median'),
            Maximum_CVSS=('CVSS', 'max'),
            Vulnerability_Count=('CVSS', 'count')
        ).reset_index()

        # Merge ACS scores
        host_metrics['ACS'] = host_metrics['IP'].map(acs_dict).fillna(1).astype(int)

        # Compute counts of severity per IP
        severity_counts = df_valid_cvss_host.groupby(['IP', 'Severity']).size().unstack(fill_value=0).reset_index()

        # Merge with host_metrics DataFrame on 'IP'
        host_metrics = host_metrics.merge(severity_counts, on='IP', how='left')

        # Sort the hosts by Maximum CVSS in descending order
        host_metrics = host_metrics.sort_values(by='Maximum_CVSS', ascending=False)

        # Prepare data for the table
        host_metrics_data = [["ACS", "Host IP", "Max CVSS", "Median CVSS", "Vuln Count", "High", "Medium", "Low"]]

        def create_acs_drawing(score, size=(20, 20)):
            """
            Create a Drawing object with a square border and the ACS number inside,
            with dynamic text color based on the ACS score.

            Args:
                score (int): The ACS score (1-5).
                size (tuple): Width and height of the square in points.

            Returns:
                Drawing: A ReportLab Drawing object representing the ACS.
            """
            width, height = size

            # Define color mappings for border based on ACS score
            border_color_mapping = {
                1: '#264653',
                2: '#2A9D8F',
                3: '#E9C46A',
                4: '#F4A261',
                5: '#E76f51'
            }

            # Define text color mappings based on ACS score for optimal contrast
            text_color_mapping = {
                1: '#264653',
                2: '#2A9D8F',
                3: '#E9C46A',
                4: '#F4A261',
                5: '#E76f51'
            }

            # Retrieve the appropriate colors, defaulting to black border and white text if out of range
            border_color = border_color_mapping.get(score, '#000000')
            text_color = text_color_mapping.get(score, '#FFFFFF')

            # Create a Drawing object
            d = Drawing(width, height)

            # Draw a rectangle with no fill and colored border
            d.add(Rect(0, 0, width, height, strokeColor=border_color, fillColor=None, strokeWidth=1))

            # Add the ACS number centered within the rectangle with dynamic text color
            d.add(String(width / 2, height / 2 - 3, str(score), fontSize=10, textAnchor='middle', fillColor=text_color))

            return d

        for index, row in host_metrics.iterrows():
            acs_score = int(row["ACS"])
            # Ensure ACS score is within expected range
            if acs_score < 1:
                acs_score = 1
            elif acs_score > 5:
                acs_score = 5

            host_metrics_data.append([
                create_acs_drawing(acs_score, size=(20, 20)),
                str(row["IP"]),
                f"{row['Maximum_CVSS']:.1f}",
                f"{row['Median_CVSS']:.1f}",
                str(int(row["Vulnerability_Count"])),
                int(row.get('High', 0)),
                int(row.get('Medium', 0)),
                int(row.get('Low', 0))
            ])

        # Create the table
        host_metrics_table = Table(
            host_metrics_data,
            colWidths=[0.5 * inch, 1.3 * inch, 1.1 * inch, 1.1 * inch, 1 * inch, 0.5 * inch, 0.7 * inch, 0.5 * inch],
            hAlign='CENTER'
        )

        # Apply initial styles
        host_metrics_table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),  # Header row background
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),  # Left-align text
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (1, 0), (-1, -1), 8),
                ("TOPPADDING", (1, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("VALIGN", (0, 1), (0, -1), "MIDDLE"),
            ]
        )

        # Apply styles per row
        for i in range(1, len(host_metrics_data)):
            # Alternate row background color
            bg_color = colors.HexColor("#EAECEE") if i % 2 == 0 else colors.HexColor("#F2F3F4")
            host_metrics_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

            ## Max CVSS styling
            #try:
            #    max_cvss_value = float(host_metrics_data[i][2])
            #except ValueError:
            #    max_cvss_value = None
            #
            #if max_cvss_value is not None:
            #    if 0.0 <= max_cvss_value <= 3.9:
            #        cell_color = colors.HexColor("#3eae49")  # Green
            #    elif 4.0 <= max_cvss_value <= 6.9:
            #        cell_color = colors.HexColor("#fdc432")  # Yellow/Orange
            #    elif 7.0 <= max_cvss_value <= 10.0:
            #        cell_color = colors.HexColor("#d43f3a")  # Red
            #    else:
            #        cell_color = None
            #
            #    if cell_color:
            #        host_metrics_table_style.add('BACKGROUND', (2, i), (2, i), cell_color)
            #
            ## Median CVSS styling
            #try:
            #    median_cvss_value = float(host_metrics_data[i][3])
            #except ValueError:
            #    median_cvss_value = None
            #
            #if median_cvss_value is not None:
            #    if 0.0 <= median_cvss_value <= 3.9:
            #        cell_color = colors.HexColor("#3eae49")  # Green
            #    elif 4.0 <= median_cvss_value <= 6.9:
            #        cell_color = colors.HexColor("#fdc432")  # Yellow
            #    elif 7.0 <= median_cvss_value <= 10.0:
            #        cell_color = colors.HexColor("#d43f3a")  # Red
            #    else:
            #        cell_color = None
            #
            #    if cell_color:
            #        host_metrics_table_style.add('BACKGROUND', (3, i), (3, i), cell_color)

        # Apply the style to the table
        host_metrics_table.setStyle(host_metrics_table_style)

        elements.append(host_metrics_table)

        # -------------------- #
        #      Heatmap         #
        # -------------------- #

        # Generate the heatmap and save the image
        try:
            # Define required columns without 'IP'
            required_columns = ['Maximum_CVSS', 'Median_CVSS', 'Vulnerability_Count']
            for col in required_columns:
                if col not in host_metrics.columns:
                    host_metrics[col] = 0  # Fill missing columns with zeros

            # Verify 'IP' column exists
            if 'IP' not in host_metrics.columns:
                logger.error("The 'IP' column is missing from the host_metrics DataFrame.")
                raise ValueError("The 'IP' column is required for heatmap generation.")

            # Select the columns you want to include in the heatmap, including 'IP'
            heatmap_data = host_metrics[['IP'] + required_columns].copy()
            heatmap_data.set_index('IP', inplace=True)

            # Define color mapping functions
            def map_cvss_color(value):
                """
                Maps CVSS score to color based on defined ranges.
                """
                if 0.0 <= value <= 3.9:
                    return '#3eae49'  # Green
                elif 4.0 <= value <= 6.9:
                    return '#fdc432'  # Yellow
                elif 7.0 <= value <= 10.0:
                    return '#d43f3a'  # Red
                else:
                    return '#FFFFFF'  # White for undefined ranges

            def map_vuln_count_color(value):
                """
                Maps Vulnerability Count to color based on defined ranges (same as CVSS).
                """
                if 0.0 <= value <= 15:
                    return '#3eae49'  # Green
                elif 16 <= value <= 30:
                    return '#fdc432'  # Yellow
                elif 31 <= value <= 35:
                    return '#d43f3a'  # Red
                elif value > 35:
                    return '#d43f3a'  # Red for counts above 35
                else:
                    return '#FFFFFF'  # White for undefined ranges

            # Create a color array based on the mappings
            color_array = []
            for idx, row in heatmap_data.iterrows():
                row_colors = []
                for col in required_columns:
                    if col in ['Maximum_CVSS', 'Median_CVSS']:
                        try:
                            color = map_cvss_color(float(row[col]))
                        except (ValueError, TypeError):
                            color = '#FFFFFF'  # Default to white if conversion fails
                    elif col == 'Vulnerability_Count':
                        try:
                            color = map_vuln_count_color(float(row[col]))
                        except (ValueError, TypeError):
                            color = '#FFFFFF'  # Default to white if conversion fails
                    else:
                        color = '#FFFFFF'  # Default to white if column not recognized
                    row_colors.append(color)
                color_array.append(row_colors)

            # Convert color array to RGBA
            rgba_array = []
            for row in color_array:
                rgba_row = []
                for hex_color in row:
                    try:
                        rgba = to_rgba(hex_color)
                    except ValueError:
                        rgba = to_rgba('#FFFFFF')  # Default to white if invalid color
                    rgba_row.append(rgba)
                rgba_array.append(rgba_row)

            rgba_array = np.array(rgba_array)

            # Fixed width and height for heatmap cells
            fixed_width = 5
            fixed_height = 5

            # Create plot
            fig, ax = plt.subplots(figsize=(fixed_width, fixed_height))

            # Display the heatmap with the mapped colors
            ax.imshow(rgba_array, aspect='auto')

            # Set ticks and labels
            ax.set_xticks(np.arange(len(required_columns)))
            ax.set_yticks(np.arange(len(heatmap_data.index)))
            ax.set_xticklabels(required_columns)
            ax.set_yticklabels(heatmap_data.index)

            # Rotate the tick labels and set their alignment
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')

            # Annotate each cell with the actual value
            for i in range(len(heatmap_data.index)):
                for j, col_name in enumerate(required_columns):
                    try:
                        value = heatmap_data.iloc[i, j]
                        # Format the text based on the column
                        if col_name in ['Maximum_CVSS', 'Median_CVSS']:
                            text = f"{float(value):.1f}"
                        elif col_name == 'Vulnerability_Count':
                            text = f"{int(value)}"
                        else:
                            text = str(value)
                        ax.text(j, i, text, ha='center', va='center', color='black', fontsize=9)
                    except IndexError:
                        # Handle cases where the value is missing
                        ax.text(j, i, "N/A", ha='center', va='center', color='black', fontsize=9)
                    except ValueError:
                        # Handle cases where conversion fails
                        ax.text(j, i, "N/A", ha='center', va='center', color='black', fontsize=9)

            # Set labels and title
            #ax.set_xlabel('Metrics', fontsize=8)
            #ax.set_ylabel('Host IP', fontsize=8)
            ax.set_title('Host-Level Vulnerability Metrics Heatmap', fontsize=10, fontweight='bold')

            # Set minor ticks to draw grid lines
            ax.set_xticks(np.arange(len(required_columns) + 1) - 0.5, minor=True)
            ax.set_yticks(np.arange(len(heatmap_data.index) + 1) - 0.5, minor=True)
            # Enable grid on minor ticks
            ax.grid(which='minor', color='black', linestyle='-', linewidth=1)
            # Hide major ticks
            ax.tick_params(which='minor', bottom=False, left=False)
            # Optional: Adjust the spines to ensure the grid lines are within the axes
            for spine in ax.spines.values():
                spine.set_visible(False)

            # Create legend for CVSS and Vulnerability Count colors
            legend_elements = [
                Patch(facecolor='#d43f3a', edgecolor='black', label='High Risk'),  # Red
                Patch(facecolor='#fdc432', edgecolor='black', label='Medium Risk'),  # Yellow/Orange
                Patch(facecolor='#3eae49', edgecolor='black', label='Low Risk'),  # Green
            ]

            ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)

            plt.tight_layout()

            # Save the heatmap image to the result_graphs directory
            heatmap_image_path = os.path.join(result_graphs_dir,
                                              f"{task_name}_host_metrics_heatmap_{completion_time}.png")
            plt.savefig(heatmap_image_path, bbox_inches='tight', dpi=300)
            plt.close()

            # Add the heatmap image to the PDF
            elements.append(Spacer(1, 0.25 * inch))

            # Create the Image object with fixed width and proportional height, centered
            heatmap_image = Image(heatmap_image_path, width=fixed_width * inch, height=fixed_height * inch,
                                  hAlign='CENTER')
            elements.append(heatmap_image)
            elements.append(PageBreak())
        except Exception as e:
            logger.error(f"Failed to generate heatmap: {e}")
            print(colored(f"[ERROR] Failed to generate heatmap: {e}", "red"))

        # -------------------- #
        # Detailed Vulnerabilities #
        # -------------------- #

        # Appendix: Detailed Vulnerability List
        # Extract relevant columns for the detailed vulnerability list
        detailed_vulns = df[["IP", "DID", "Severity", "Summary", "QoD", "Solution"]].copy()

        # Define the order for the 'Severity' column
        severity_order = ['High', 'Medium', 'Low']
        severity_dtype = CategoricalDtype(categories=severity_order, ordered=True)
        detailed_vulns['Severity'] = detailed_vulns['Severity'].astype(severity_dtype)

        # Exclude entries with 'Log' severity or any not in the specified categories
        detailed_vulns = detailed_vulns[detailed_vulns['Severity'].notna()]

        # Sort the DataFrame by 'Severity'
        detailed_vulns = detailed_vulns.sort_values('Severity')

        # Prepare the data for the detailed vulnerabilities table
        detailed_vulns_data = [["IP", "DID", "Severity", "Summary", "QoD", "Solution"]]
        for i, row in detailed_vulns.iterrows():
            detailed_vulns_data.append(
                [
                    Paragraph(str(row["IP"]), styleN),  # IP Address
                    Paragraph(str(row["DID"])[3:], styleN),  # DID without 'DID' prefix
                    Paragraph(str(row["Severity"]), styleN),  # Severity
                    Paragraph(str(row["Summary"]), styleN),  # Summary
                    Paragraph(str(row["QoD"]), styleN),  # Severity
                    Paragraph(str(row["Solution"]), styleN),  # Solution
                ]
            )

        if detailed_vulns is not None and not detailed_vulns.empty and len(detailed_vulns_data) > 1:
            elements.append(Paragraph("Appendix: Detailed Vulnerability List", styleH))
            detailed_vulnerability_text = (
                f"The following table outlines all of the {total_vulns} vulnerabilities identified using the scan accompanied by important information "
                "such as the impacted host, severity level, summary, and solution."
            )
            elements.append(Paragraph(detailed_vulnerability_text, styleN))
            elements.append(Spacer(1, 0.25 * inch))


            detailed_vulns_table = Table(
                detailed_vulns_data,
                colWidths=[1.2 * inch, 0.5 * inch, 0.7 * inch, 1.9 * inch, 0.5 * inch, 1.9 * inch],
            )

            detailed_vulns_table_style = TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#2C3E50"),
                    ),  # Blue background for the header row
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.whitesmoke,
                    ),  # White text color for the header row
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "LEFT",
                    ),  # Left-align text for better readability
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),  # Slightly reduced font size for better fit
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),  # Added padding
                    ("TOPPADDING", (0, 0), (-1, 0), 10),  # Added padding
                    ("BOTTOMPADDING", (1, 0), (-1, -1), 8),
                    ("TOPPADDING", (1, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),  # Added padding
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),  # Added padding
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.75,
                        colors.black,
                    ),  # Thicker border around the table
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),  # Align text to the top of each cell
                ]
            )

            # Manually alternate row background colors
            for i in range(1, len(detailed_vulns_data)):
                if i % 2 == 0:
                    bg_color = colors.HexColor("#EAECEE")  # Light gray
                else:
                    bg_color = colors.HexColor("#F2F3F4")
                detailed_vulns_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

            detailed_vulns_table.setStyle(detailed_vulns_table_style)
            elements.append(detailed_vulns_table)
            elements.append(Spacer(1, 0.75 * inch))  # Increased spacing
            elements.append(PageBreak())
        else:
            elements.append(Paragraph("No Detailed Vulnerability List was provided.", styleN))
            elements.append(Spacer(1, 0.75 * inch))

        # -------------------- #
        #    Nikto Scan Results#
        # -------------------- #

        # Appendix: Nikto Scan Results
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Appendix: Nikto Scan Results", styleH))
        nikto_text = (
            "The following table presents the results from the Nikto scan, detailing web service/application based vulnerabilities "
            "identified during the assessment."
        )
        elements.append(Paragraph(nikto_text, styleN))
        elements.append(Spacer(1, 0.25 * inch))

        if nikto_df is not None and not nikto_df.empty:
            # Prepare Nikto data for the table
            nikto_table_data = [["Host", "DID", "Port", "Reference", "Description"]]
            for index, row in nikto_df.iterrows():
                nikto_table_data.append(
                    [
                        Paragraph(str(row["Host"]), styleN),
                        Paragraph(str(row["DID"])[3:], styleN),
                        Paragraph(str(row["Port"]), styleN),
                        Paragraph(str(row["Reference"]), styleN),
                        Paragraph(str(row["Description"]), styleN),
                    ]
                )

            nikto_table = Table(
                nikto_table_data,
                colWidths=[1.2 * inch, 0.5 * inch, 0.5 * inch, 1.5 * inch, 3 * inch],
            )

            nikto_table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )

            # Alternate row colors
            for i in range(1, len(nikto_table_data)):
                bg_color = (
                    colors.HexColor("#EAECEE")
                    if i % 2 == 0
                    else colors.HexColor("#F2F3F4")
                )
                nikto_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

            nikto_table.setStyle(nikto_table_style)
            elements.append(nikto_table)
            elements.append(PageBreak())
        else:
            elements.append(Paragraph("No Nikto scan results were provided.", styleN))

        # -------------------- #
        #   Nuclei Scan Results#
        # -------------------- #

        # Appendix: Nuclei Scan Results
        elements.append(Spacer(1, 0.75 * inch))  # Increased spacing
        elements.append(Paragraph("Appendix: Nuclei Scan Results", styleH))
        nuclei_text = (
            "The following table presents the results from the Nuclei scan, detailing vulnerabilities "
            "identified during the assessment."
        )
        elements.append(Paragraph(nuclei_text, styleN))
        elements.append(Spacer(1, 0.25 * inch))

        if nuclei_combined_output_file and os.path.exists(nuclei_combined_output_file):
            with open(nuclei_combined_output_file, "r") as nuclei_file:
                nuclei_lines = nuclei_file.readlines()

            # Prepare data for the Nuclei table
            nuclei_table_data = [["Vulnerability", "Protocol", "Severity", "Target"]]
            for line in nuclei_lines:
                # Remove any square brackets and extra spaces from the line
                line = line.replace("[", "").replace("]", "").strip()
                parts = line.split()  # Split the line into parts

                if len(parts) >= 4:
                    nuclei_table_data.append(
                        [
                            Paragraph(parts[0], styleN),  # Vulnerability
                            Paragraph(parts[1], styleN),  # Protocol
                            Paragraph(parts[2], styleN),  # Severity
                            Paragraph(" ".join(parts[3:]), styleN),  # Target
                        ]
                    )

            nuclei_table = Table(
                nuclei_table_data,
                colWidths=[1.75 * inch, 1.0 * inch, 1.0 * inch, 2.9 * inch],
            )

            nuclei_table_style = TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )

            # Alternate row colors
            for i in range(1, len(nuclei_table_data)):
                bg_color = (
                    colors.HexColor("#EAECEE")
                    if i % 2 == 0
                    else colors.HexColor("#F2F3F4")
                )
                nuclei_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

            nuclei_table.setStyle(nuclei_table_style)
            elements.append(nuclei_table)
        else:
            elements.append(Paragraph("No Nuclei scan results were provided.", styleN))

        # -------------------- #
        #   Metasploit Results #
        # -------------------- #

        # Define path for the Metasploit report
        metasploit_report_path = os.path.join("metasploit_results",
                                              reportname) if reportname is None else os.path.join(
            "metasploit_results", reportname)

        # Parse the Metasploit report
        if os.path.exists(metasploit_report_path):
            metasploit_data = parse_metasploit_report(metasploit_report_path)
        else:
            metasploit_data = None
            print(colored(f"[WARNING] Metasploit report not found at path: {metasploit_report_path}", "yellow"))

        # Appendix: Metasploit Exploitation Results
        if metasploit_data:
            elements.append(PageBreak())
            elements.append(Paragraph("Appendix: Metasploit Exploitation Results", styleH))
            metasploit_intro = (
                "The following sections detail the results of the Metasploit exploitation attempts conducted during the assessment."
            )
            elements.append(Paragraph(metasploit_intro, styleN))
            elements.append(Spacer(1, 0.25 * inch))

            # Table: Exploited CVEs
            exploited_cves = metasploit_data.get("exploited_cves", [])
            if exploited_cves:
                elements.append(Paragraph("Exploited CVEs:", styleH))
                metasploit_exp_cve = (
                    """The table below enumerates the specific CVEs that were successfully exploited during the assessment. 
                    Each entry provides detailed information about the vulnerability, the exploit utilised, the target IP and port, 
                    and the number of payloads that were successfully deployed. This data underscores the effectiveness of the 
                    exploitation efforts and highlights the critical vulnerabilities that require immediate attention."""
                )

                elements.append(Paragraph(metasploit_exp_cve, styleN))
                elements.append(Spacer(1, 0.25 * inch))
                exploited_data = [["CVE", "Exploit (Metasploit Module)", "Target IP", "Target Port", "Payload Successful",]]
                for exploit in exploited_cves:
                    exploited_data.append([
                        Paragraph(exploit.get("cve", "N/A"), styleN),
                        Paragraph(exploit.get("exploit", "N/A"), styleN),
                        Paragraph(exploit.get("target_ip", "N/A"), styleN),
                        Paragraph(exploit.get("target_port", "N/A"), styleN),
                        Paragraph(str(exploit.get("payload_successful", "N/A")), styleN),
                    ])

                exploited_table = Table(
                    exploited_data,
                    colWidths=[1.2 * inch, 2.1 * inch, 1.2 * inch, 1 * inch, 1.2 * inch]
                )

                exploited_table_style = TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("TOPPADDING", (0, 0), (-1, 0), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
                    ]
                )

                # Alternate row colors
                for i in range(1, len(exploited_data)):
                    bg_color = colors.HexColor("#EAECEE") if i % 2 == 0 else colors.HexColor("#F2F3F4")
                    exploited_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

                exploited_table.setStyle(exploited_table_style)
                elements.append(exploited_table)
                elements.append(Spacer(1, 0.25 * inch))
            else:
                elements.append(Paragraph("No CVEs were exploited.", styleN))
                elements.append(Spacer(1, 0.25 * inch))

            # Table: CVEs Without Available Exploits
            cves_without_exploits = metasploit_data.get("cves_without_exploits", [])
            if cves_without_exploits:
                elements.append(Paragraph("CVEs Detected Without Available Exploits:", styleH))
                metasploit_no_exploit = (
                    """This section provides a list of CVEs for which have no corresponding Metasploit exploit."""
                )
                elements.append(Paragraph(metasploit_no_exploit, styleN))
                elements.append(Spacer(1, 0.25 * inch))
                cves_without_exploits_data = [["CVE"]]
                for cve in cves_without_exploits:
                    cves_without_exploits_data.append([Paragraph(cve, styleN)])

                cves_without_table = Table(
                    cves_without_exploits_data,
                    colWidths=[6.7 * inch]
                )

                cves_without_table_style = TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("TOPPADDING", (0, 0), (-1, 0), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
                    ]
                )

                # Alternate row colors
                for i in range(1, len(cves_without_exploits_data)):
                    bg_color = colors.HexColor("#EAECEE") if i % 2 == 0 else colors.HexColor("#F2F3F4")
                    cves_without_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

                cves_without_table.setStyle(cves_without_table_style)
                elements.append(cves_without_table)
                elements.append(Spacer(1, 0.25 * inch))
            else:
                elements.append(Paragraph("All detected CVEs have available exploits.", styleN))
                elements.append(Spacer(1, 0.25 * inch))

            # Summary Statistics
            if metasploit_data:
                with open('counts.json', 'r') as f:
                    counts = json.load(f)
                exploited_cves = counts.get('exploitedcves', 0)
                incompatible_cves = counts.get('incompatiblecves', 0)
                totcve = int(exploited_cves) + int(incompatible_cves)

                elements.append(Paragraph("Summary Statistics:", styleH))
                metasploit_summary = (
                    """This table provides a statistical overview of the exploitation module's 
                    performance. The 'Total CVEs Examined' column shows the number of CVEs that were processed by the 
                    exploit module. 'Total Exploited CVEs' represents the number of CVEs that were successfully 
                    exploited, while 'Incompatible CVEs' indicates the number of CVEs for which no corresponding 
                    Metasploit exploit is available."""
                )
                elements.append(Paragraph(metasploit_summary, styleN))
                elements.append(Spacer(1, 0.25 * inch))
                summary_data = [
                    ["Total CVEs Examined", "Total Exploited CVEs", "Incompatible CVEs"],
                    [
                        Paragraph(str(totcve), styleN),
                        Paragraph(str(exploited_cves), styleN),
                        Paragraph(str(incompatible_cves), styleN),
                    ]
                ]

                summary_table = Table(
                    summary_data,
                    colWidths=[2.2 * inch, 2.3 * inch, 2.2 * inch]
                )

                summary_table_style = TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                        ("TOPPADDING", (0, 0), (-1, 0), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
                    ]
                )

                # Alternate row colors
                for i in range(1, len(summary_data)):
                    bg_color = colors.HexColor("#EAECEE") if i % 2 == 0 else colors.HexColor("#F2F3F4")
                    summary_table_style.add("BACKGROUND", (0, i), (-1, i), bg_color)

                summary_table.setStyle(summary_table_style)
                elements.append(summary_table)
                elements.append(Spacer(1, 0.5 * inch))
            else:
                elements.append(Paragraph("Summary Statistics are not available.", styleN))
                elements.append(Spacer(1, 0.5 * inch))

        # Build PDF and add page numbers to each page
        doc.build(elements, onFirstPage=add_first_page_header, onLaterPages=add_later_page_number)

        print(
            colored("[INFO]", "cyan")
            + f" Executive report generated and saved to "
            + colored(f"{output_pdf_path}", attrs=["bold"])
        )

        print(
            colored("[SUCCESS]", "green")
            + " All scans completed. Reports generated successfully"
        )
    except Exception as e:
        print(colored(f"[ERROR] Failed to generate executive PDF report: {e}", "red"))
