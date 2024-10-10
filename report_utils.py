import os
import io
import time
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


def add_page_number(canvas, doc):
    """
    Add a page number to the canvas footer with a line above it, formatted as "1 | Page".

    This function is used as a callback by the ReportLab library to add page numbers
    to each page of the PDF document during generation.

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


def generate_report(
    csv_path,
    task_name,
    hosts_count,
    high_count,
    medium_count,
    low_count,
    os_count,
    apps_count,
    nikto_csv_path=None,
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
        nikto_csv_path (str, optional): Path to the Nikto scan results CSV file. Defaults to None.
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
    bar_out = os.path.join(
        result_graphs_dir, f"{task_name}_barchart_{completion_time}.png"
    )
    bar_chart_path = bar_out
    gui_pie_out = os.path.join(
        result_graphs_dir, f"vuln_pie.png"
    )
    gui_pie_out = gui_pie_out

    # Load and process CSV data from OpenVAS scan results
    df = pd.read_csv(rep_csv_path)
    df = df.astype(str).fillna("Value not found")
    df["CVSS"] = pd.to_numeric(df["CVSS"], errors="coerce")

    # Summarise vulnerability counts
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

    # Prepare data for the bar chart (scan information)
    bar_legend_labels = ["Systems", "Applications", "Operating Systems"]
    bar_sizes = [hosts_count, os_count, apps_count]
    bar_colors = ["#bbeeff", "#3366ff", "#77aaff"]  # Shades of blue

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

    try:
        # Generate the bar chart for scan information
        fig2, ax2 = plt.subplots(figsize=(3.5, 3.5))  # Smaller size
        bars = ax2.bar(bar_legend_labels, bar_sizes, color=bar_colors, edgecolor="none")

        # Add value labels on top of each bar
        for bar in bars:
            yval = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                yval + 0.5,
                f"{int(yval)}",
                ha="center",
                va="bottom",
                fontsize=10,
                color="black",
            )

        # Set labels and formatting
        ax2.set_ylabel("Count", fontsize=10)
        ax2.set_title("Scan Information", fontsize=12, fontweight="bold", pad=15)
        ax2.tick_params(axis="x", labelsize=10)
        ax2.tick_params(axis="y", labelsize=10)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)
        ax2.spines["left"].set_linewidth(1.5)
        ax2.spines["bottom"].set_linewidth(1.5)
        # Removes x-axis label.
        ax2.set_xticklabels([])
        ax2.yaxis.grid(False)
        ax2.xaxis.grid(False)
        ax2.set_axisbelow(True)

        ax2.legend(
            bars,
            bar_legend_labels,
            title="Categories",
            loc="upper left",
            fontsize=8,
            title_fontsize=10,
        )

        plt.tight_layout()

        # Save the bar chart
        plt.savefig(bar_chart_path, bbox_inches="tight", dpi=300)
        plt.close(fig2)  # Close the figure to free memory
    except Exception as e:
        print(colored(f"[ERROR] Failed to generate bar chart: {e}", "red"))

    # Generate the pie graph for the GUI result section
    try:
        gui_vuln_labels = ['High', 'Medium', 'Low']
        gui_vuln_sizes = [high_vulns, medium_vulns, low_vulns]
        gui_vuln_colors = ['#ff6f61', '#ffcc66', '#66cc66']
        explode = (0, 0, 0)  # No slice explode

        # Adjust the figure size to provide more room for the legend
        fig_vuln_gui, ax = plt.subplots(figsize=(3.12, 1.96))

        # Create the pie chart
        ax.pie(gui_vuln_sizes, labels=None, colors=gui_vuln_colors, autopct=lambda p: f'{int(p * sum(sizes) / 100)}',
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
        elements.append(Spacer(1, 0.5 * inch))

        # --- Key Findings ---
        elements.append(Paragraph("2. Key Findings", styleH))

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

        # Add the pie chart and bar chart side by side
        chart_table = Table(
            [
                [
                    Image(pie_chart_path, width=2.50 * inch, height=2 * inch),
                    Image(bar_chart_path, width=2.50 * inch, height=2 * inch),
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
        elements.append(Spacer(1, 0.5 * inch))
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

        # Appendix: Detailed Vulnerability List
        elements.append(Paragraph("Appendix: Detailed Vulnerability List", styleH))
        detailed_vulnerability_text = (
            "The following table outlines all of the vulnerabilities identified using the scan accompanied by important information "
            "such as the impacted host, severity level, summary, and solution."
        )
        elements.append(Paragraph(detailed_vulnerability_text, styleN))
        elements.append(Spacer(1, 0.5 * inch))

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

        # Appendix: Nikto Scan Results
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph("Appendix: Nikto Scan Results", styleH))
        nikto_text = (
            "The following table presents the results from the Nikto scan, detailing web server vulnerabilities "
            "identified during the assessment."
        )
        elements.append(Paragraph(nikto_text, styleN))
        elements.append(Spacer(1, 0.5 * inch))

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
        else:
            elements.append(Paragraph("No Nikto scan results were provided.", styleN))

        # Build PDF and add page numbers to each page
        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

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
