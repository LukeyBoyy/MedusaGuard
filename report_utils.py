import os
import io
import time
import re
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
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
from datetime import datetime
from pathlib import Path
from termcolor import colored


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

    with open(report_path, 'r') as file:
        for line in file:
            line = line.strip()

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
                        total_exploited += 1
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

            # Detect the section listing CVEs without exploits
            if "The following CVEs were detected, but Metasploit does not have an exploit to target these:" in line:
                # Read subsequent lines for CVEs
                for cve_line in file:
                    cve_line = cve_line.strip()
                    if not cve_line:
                        break
                    if cve_line.startswith("CVE-"):
                        cves_without_exploits.append(cve_line)

    parsed_data = {
        "exploited_cves": exploited_cves,
        "cves_without_exploits": cves_without_exploits,
        "total_cves_examined": total_cves_examined,
        "total_exploited_cves": total_exploited,
        "incompatible_cves": incompatible_cves
    }

    return parsed_data


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
    #bar_out = os.path.join(
    #    result_graphs_dir, f"{task_name}_barchart_{completion_time}.png"
    #)
    #bar_chart_path = bar_out
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
                "Vulnerability",
                "Method",
                "URI",
                "Description",
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

    #try:
    #    # Generate the bar chart for scan information
    #    fig2, ax2 = plt.subplots(figsize=(3.5, 3.5))  # Smaller size
    #    bars = ax2.bar(bar_legend_labels, bar_sizes, color=bar_colors, edgecolor="none")
#
    #    # Add value labels on top of each bar
    #    for bar in bars:
    #        yval = bar.get_height()
    #        ax2.text(
    #            bar.get_x() + bar.get_width() / 2,
    #            yval + 0.5,
    #            f"{int(yval)}",
    #            ha="center",
    #            va="bottom",
    #            fontsize=10,
    #            color="black",
    #        )
#
    #    # Set labels and formatting
    #    ax2.set_ylabel("Count", fontsize=10)
    #    ax2.set_title("Scan Information", fontsize=12, fontweight="bold", pad=15)
    #    ax2.tick_params(axis="x", labelsize=10)
    #    ax2.tick_params(axis="y", labelsize=10)
    #    ax2.spines["top"].set_visible(False)
    #    ax2.spines["right"].set_visible(False)
    #    ax2.spines["left"].set_linewidth(1.5)
    #    ax2.spines["bottom"].set_linewidth(1.5)
    #    # Removes x-axis label.
    #    ax2.set_xticklabels([])
    #    ax2.yaxis.grid(False)
    #    ax2.xaxis.grid(False)
    #    ax2.set_axisbelow(True)
#
    #    ax2.legend(
    #        bars,
    #        bar_legend_labels,
    #        title="Categories",
    #        loc="upper left",
    #        fontsize=8,
    #        title_fontsize=10,
    #    )
#
    #    plt.tight_layout()
#
    #    # Save the bar chart
    #    plt.savefig(bar_chart_path, bbox_inches="tight", dpi=300)
    #    plt.close(fig2)  # Close the figure to free memory
    #except Exception as e:
    #    print(colored(f"[ERROR] Failed to generate bar chart: {e}", "red"))

    # Generate the pie graph for the GUI result section
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

        # --- Build the Title Page ---
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(
            Paragraph("Vulnerability Scanning and Exploitation Report", styleTitle)
        )
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"Automated Security Assessment", centered_style))
        elements.append(Paragraph(f"Created by: MedusaGuard v1.0", centered_style))
        elements.append(
            Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", centered_style)
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
                "This document contains the results of the automated vulnerability scanning and exploitation tool. "
                "It outlines identified vulnerabilities, their potential impacts, and suggested remediation strategies "
                "along with whether or not exploitation was successful.",
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
                "Recommendations .................................................................................................................................................................................",
                "4",
            ],
            [
                "Conclusion ..............................................................................................................................................................................................",
                "4",
            ],
            [
                "Appendix: Definitions ..............................................................................................................................................................................",
                "4",
            ],
            [
                "Appendix: Recommended Actions to be Taken Based on Vulnerability Severity ...................................................................................",
                "5",
            ],
            [
                "Appendix: Detailed Tool Results  .........................................................................................................................................................",
                "5",
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
            if high_count <= 3:
                exec_summary = (
                    f"The purpose of this vulnerability scan was to identify weaknesses within our IT infrastructure "
                    f"that could be exploited by attackers, potentially leading to financial loss, regulatory penalties, "
                    f"or damage to our reputation. Of the {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were found, "
                    f"with {high_vulns} categorized as high, posing the most significant risk. Immediate remediation of any high vulnerabilities "
                    f"identified is necessary to avoid potential business disruptions and ensure the continued trust of our customers. "
                    f"This report provides detailed findings and actionable recommendations to mitigate these risks, safeguarding our operations."
                )
            elif high_count > 4:
                exec_summary = (
                    f"The vulnerability scan identified several high-risk vulnerabilities within our IT infrastructure. "
                    f"Out of the {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were found, with {high_vulns} being high-risk. "
                    f"These should be addressed promptly to avoid potential security breaches."
                    f"This report provides detailed findings and actionable recommendations to mitigate these risks, safeguarding our operations."
                )
            else:
                exec_summary = (
                    f"The vulnerability scan did not identify any high-risk vulnerabilities. "
                    f"Out of the {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were found, with none classified as high risk "
                    f"{medium_vulns} classified as medium risk, and {low_vulns} classified as low risk. Therefore, our IT infrastructure shows "
                    f"a strong security posture, though continuous monitoring and improvement are still recommended. "
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

        # --- Top 10 Vulnerabilities ---
        elements.append(Paragraph("3. Top 10 Vulnerabilities", styleH))
        top_10_text = (
            "The following table details the top 10 most critical vulnerabilities identified in the scan. It is ordered from "
            "most significant risk to least significant risk, with a CVSS score of 10.0 being the highest score possible "
            "awarded to vulnerabilities that pose a major risk. Please refer to the definitions table in the appendix "
            "if any of the terms are unknown to you."
        )
        elements.append(Paragraph(top_10_text, styleN))
        elements.append(PageBreak())

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
                vuln_data, colWidths=[1.3 * inch, 0.5 * inch, 2.5 * inch, 2.5 * inch]
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
            elements.append(vuln_table)
        else:
            # No vulnerabilities found
            no_vuln_message = Paragraph(
                "No vulnerabilities were found during the scan.", styleN
            )
            elements.append(no_vuln_message)

        elements.append(Spacer(1, 0.75 * inch))

        # --- Recommendations ---
        elements.append(Paragraph("4. Recommendations", styleH))
        recommendations = (
            "Immediately address any critical vulnerabilities, continue to perform regular security assessments, "
            "and allocate resources to strengthen the security posture of our organization."
        )
        elements.append(Paragraph(recommendations, styleN))
        elements.append(Spacer(1, 0.75 * inch))

        # --- Conclusion ---
        elements.append(Paragraph("5. Conclusion", styleH))
        conclusion = (
            "Addressing these vulnerabilities will help mitigate risks to the organization and ensure compliance with "
            "industry standards. We recommend taking immediate action on any critical vulnerabilities and implementing long-term "
            "strategies to improve our security framework."
        )
        elements.append(Paragraph(conclusion, styleN))
        elements.append(Spacer(1, 0.75 * inch))

        # --- Appendices ---

        # Appendix: Definitions
        elements.append(Paragraph("Appendix: Definitions", styleH))
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
        ]

        definitions_table = Table(definitions_data, colWidths=[2.3 * inch, 4.5 * inch])
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

        # Appendix: Recommended Actions
        elements.append(
            Paragraph(
                "Appendix: Recommended Actions to be Taken Based on Vulnerability Severity",
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
            actions_data, colWidths=[1.3 * inch, 2.5 * inch, 3 * inch]
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

        # Appendix: Detailed Vulnerability List
        # Extract relevant columns for the detailed vulnerability list
        detailed_vulns = df[["IP", "Severity", "Summary", "Solution"]]

        # Prepare the data for the detailed vulnerabilities table
        detailed_vulns_data = [["IP Address", "Severity", "Summary", "Solution"]]
        for i, row in detailed_vulns.iterrows():
            if row["Severity"] == "Log":
                continue  # Skip entries with 'Log' severity
            detailed_vulns_data.append(
                [
                    Paragraph(str(row["IP"]), styleN),  # IP Address
                    Paragraph(str(row["Severity"]), styleN),  # Severity
                    Paragraph(str(row["Summary"]), styleN),  # Summary
                    Paragraph(str(row["Solution"]), styleN),  # Solution
                ]
            )

        if detailed_vulns is not None and not detailed_vulns.empty and len(detailed_vulns_data) > 1:
            elements.append(Paragraph("Appendix: Detailed Vulnerability List", styleH))
            detailed_vulnerability_text = (
                "The following table outlines all of the vulnerabilities identified using the scan accompanied by important information "
                "such as the impacted host, severity level, summary, and solution."
            )
            elements.append(Paragraph(detailed_vulnerability_text, styleN))
            elements.append(Spacer(1, 0.25 * inch))


            detailed_vulns_table = Table(
                detailed_vulns_data,
                colWidths=[1.2 * inch, 0.7 * inch, 2.3 * inch, 2.6 * inch],
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

        # Appendix: Nikto Scan Results
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Appendix: Nikto Scan Results", styleH))
        nikto_text = (
            "The following table presents the results from the Nikto scan, detailing web server vulnerabilities "
            "identified during the assessment."
        )
        elements.append(Paragraph(nikto_text, styleN))
        elements.append(Spacer(1, 0.25 * inch))

        if nikto_df is not None and not nikto_df.empty:
            # Prepare Nikto data for the table
            nikto_table_data = [["Host", "Port", "Vulnerability", "Description"]]
            for index, row in nikto_df.iterrows():
                nikto_table_data.append(
                    [
                        Paragraph(str(row["Host"]), styleN),
                        Paragraph(str(row["Port"]), styleN),
                        Paragraph(str(row["Vulnerability"]), styleN),
                        Paragraph(str(row["Description"]), styleN),
                    ]
                )

            nikto_table = Table(
                nikto_table_data,
                colWidths=[1.5 * inch, 0.7 * inch, 1.5 * inch, 3.0 * inch],
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
                colWidths=[1.75 * inch, 1.0 * inch, 1.0 * inch, 3.0 * inch],
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
                    Each entry provides detailed information about the vulnerability, the exploit utilized, the target IP and port, 
                    and the number of payloads that were successfully deployed. This data underscores the effectiveness of the 
                    exploitation efforts and highlights the critical vulnerabilities that require immediate attention."""
                )

                elements.append(Paragraph(metasploit_exp_cve, styleN))
                elements.append(Spacer(1, 0.25 * inch))
                exploited_data = [["CVE", "Exploit", "Target IP", "Target Port", "Payload Successful",]]
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
                    """This section provides a list of CVEs for which have no corresponding Metasploit exploit"""
                )
                elements.append(Paragraph(metasploit_no_exploit, styleN))
                elements.append(Spacer(1, 0.25 * inch))
                cves_without_exploits_data = [["CVE"]]
                for cve in cves_without_exploits:
                    cves_without_exploits_data.append([Paragraph(cve, styleN)])

                cves_without_table = Table(
                    cves_without_exploits_data,
                    colWidths=[6.75 * inch]
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
                    """This table provides a comprehensive statistical overview of the exploitation module's 
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