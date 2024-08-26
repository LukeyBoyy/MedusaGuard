import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from datetime import datetime
from pathlib import Path
from termcolor import colored


def generate_report(csv_path, task_name, hosts_count, high_count, medium_count, low_count):
    completion_time = time.strftime("%H-%M-%S_%Y-%m-%d")  # Updated timestamp format

    # Paths
    result_graphs_dir = "result_graphs"
    os.makedirs(result_graphs_dir, exist_ok=True)  # Create the directory if it doesn't exist

    rep_csv_path = Path(csv_path)
    out_path = os.path.join("openvas_reports", f"{task_name}_executive_report_{completion_time}.pdf")
    output_pdf_path = out_path
    pie_out = os.path.join(result_graphs_dir, f"{task_name}_piechart_{completion_time}.png")
    pie_chart_path = pie_out
    bar_out = os.path.join(result_graphs_dir, f"{task_name}_barchart_{completion_time}.png")
    bar_chart_path = bar_out

    # Load CSV
    df = pd.read_csv(rep_csv_path)
    df = df.astype(str).fillna("Value not found")
    df['CVSS'] = pd.to_numeric(df['CVSS'], errors='coerce')

    #total_vulns = len(df)
    #high_vulns = len(df[df['Severity'] == 'High'])
    #medium_vulns = len(df[df['Severity'] == 'Medium'])
    #low_vulns = len(df[df['Severity'] == 'Low'])
    #hosts_scanned = df['IP'].nunique()
    total_vulns = high_count + medium_count + low_count
    high_vulns = high_count
    medium_vulns = medium_count
    low_vulns = low_count
    hosts_scanned = hosts_count
    top_vulns = df.sort_values(by='CVSS', ascending=False).head(10)

    labels = ["High", "Medium", "Low"]
    colors_list = ['#dc3841', '#FFA500', '#FFFF00']
    sizes = [high_vulns, medium_vulns, low_vulns]
    explode = [0.05, 0, 0]

    # Custom function to show the values on the pie chart
    def absolute_value(val):
        return f'{int(val / 100 * sum(sizes))}'

    # Create a pie chart
    fig1, ax1 = plt.subplots(figsize=(3.5, 3.5))  # Smaller size
    wedges, texts, autotexts = ax1.pie(
        sizes,
        labels=labels,
        explode=explode,
        colors=colors_list,
        autopct=absolute_value,
        startangle=90,
        wedgeprops=dict(edgecolor="black", linewidth=1.5),
        textprops=dict(color="black", fontsize=12)
    )
    plt.axis('equal')
    plt.savefig(pie_chart_path, bbox_inches='tight', dpi=300)

    # Create a bar graph
    fig2, ax2 = plt.subplots(figsize=(3.5, 3.5))  # Smaller size
    bars = ax2.bar(labels, sizes, color=colors_list, edgecolor='black', linewidth=1.5)

    # Add value labels on top of each bar with formatting
    for bar in bars:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, yval + 0.5, f'{int(yval)}',
                 ha='center', va='bottom', fontsize=12, color='black')

    # Add labels and format them
    ax2.set_ylabel('Number of Vulnerabilities', fontsize=10)
    ax2.set_xlabel('Severity Level', fontsize=10)

    # Improve the appearance of the x and y axis labels and ticks
    ax2.tick_params(axis='x', labelsize=10)
    ax2.tick_params(axis='y', labelsize=10)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_linewidth(1.5)
    ax2.spines['bottom'].set_linewidth(1.5)

    # Add grid lines only on the y-axis
    ax2.yaxis.grid(True, color='gray', linestyle='--', linewidth=0.5)
    ax2.set_axisbelow(True)

    # Save the bar chart
    plt.savefig(bar_chart_path, bbox_inches='tight', dpi=300)

    # Initialize PDF
    doc = SimpleDocTemplate(output_pdf_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50,
                            bottomMargin=50)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    styleN = styles["BodyText"]
    styleH = styles["Heading1"]
    styleTitle = styles["Title"]

    # Adjusting the section headers to be smaller
    styleH.fontSize = 14
    styleH.leading = 16

    # Title Page
    elements.append(Paragraph("Executive Vulnerability Report", styleTitle))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(
        Paragraph("This report contains sensitive information. Unauthorized distribution is prohibited.",
                  styleN))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f"Created by: Greenbone Vulnerability Manager", styleN))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styleN))
    elements.append(Spacer(1, 0.5 * inch))

    # Executive Summary
    elements.append(Paragraph("1. Executive Summary", styleH))
    exec_summary = (
        f"The purpose of this vulnerability scan was to identify weaknesses within our IT infrastructure "
        f"that could be exploited by attackers, potentially leading to financial loss, regulatory penalties, "
        f"or damage to our reputation. Of the {hosts_scanned} hosts scanned, {total_vulns} vulnerabilities were found, "
        f"with {high_vulns} categorized as high, posing the most significant risk. Immediate remediation of any high vulnerabilities "
        f"identified is necessary to avoid potential business disruptions and ensure the continued trust of our customers. "
        f"The report provides detailed findings and actionable recommendations to mitigate these risks, safeguarding our operations."
    )
    elements.append(Paragraph(exec_summary, styleN))
    elements.append(Spacer(1, 0.5 * inch))

    # Key Findings
    elements.append(Paragraph("2. Key Findings", styleH))
    # Add the pie chart and bar chart side by side
    chart_table = Table(
        [
            [
                Image(pie_chart_path, width=2.50 * inch, height=2.50 * inch),  # Smaller size
                Image(bar_chart_path, width=2.50 * inch, height=2.50 * inch)  # Smaller size
            ]
        ],
        colWidths=[2.875 * inch, 2.875 * inch]
    )
    chart_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12)
    ]))
    elements.append(chart_table)

    data = [
        ["Vulnerability Severity", "Count"],
        [Paragraph('<font color="red">High</font>'), str(high_vulns)],
        [Paragraph('<font color="orange">Medium</font>'), str(medium_vulns)],
        [Paragraph('<font color="green">Low</font>'), str(low_vulns)],
    ]
    table = Table(data, colWidths=[2.3 * inch, 1.2 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),  # Blue background for the header row
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # White text color for the header row
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center-align text in the header and data rows
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Slightly reduced font size
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Added padding
        ('TOPPADDING', (0, 0), (-1, 0), 12),  # Added padding
        ('BOTTOMPADDING', (1, 0), (-1, -1), 8),
        ('TOPPADDING', (1, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),  # White background for the first data row
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor("#f2f2f2")),
        # Light gray background for the second data row
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),  # White background for the third data row
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),  # Thicker border around the table
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Top 10 Critical Vulnerabilities sorted by CVSS score (highest to lowest)
    elements.append(Paragraph("3. Top 10 Vulnerabilities", styleH))
    vuln_data = [["Vulnerability", "CVSS", "Impact", "Remediation"]]

    # Set to track unique vulnerabilities
    unique_vulns = set()

    for i, (_, row) in enumerate(top_vulns.iterrows()):
        vuln_name = row['NVT Name']

        # Check if the vulnerability is already in the set
        if vuln_name not in unique_vulns:
            # Add it to the set if it's not already present
            unique_vulns.add(vuln_name)

            # Append the row to the table data
            vuln_data.append([
                Paragraph(str(vuln_name), styleN),  # Wrap text in the 'Vulnerability' column
                Paragraph(str(row['CVSS']), styleN),  # CVSS score as a string
                Paragraph(str(row['Impact']), styleN),  # Convert to string and wrap text in the 'Impact' column
                Paragraph(str(row['Solution']), styleN)  # Convert to string and wrap text in the 'Remediation' column
            ])

            # Stop if we've added 10 unique vulnerabilities
            if len(vuln_data) > 10:
                break

    #for i, (_, row) in enumerate(top_vulns.iterrows()):
    #    vuln_data.append([
    #        Paragraph(str(row['NVT Name']), styleN),  # Wrap text in the 'Vulnerability' column
    #        Paragraph(str(row['CVSS']), styleN),  # CVSS score as a string
    #        Paragraph(str(row['Impact']), styleN),  # Convert to string and wrap text in the 'Impact' column
    #        Paragraph(str(row['Solution']), styleN)
    #        # Convert to string and wrap text in the 'Remediation' column
    #    ])

    # Apply alternating row colors manually
    vuln_table = Table(vuln_data, colWidths=[1.3 * inch, 0.5 * inch, 2.5 * inch, 2.5 * inch])
    vuln_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),  # Blue background for the header row
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # White text color for the header row
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Left-align text for better readability
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),  # Reduced font size for better fit
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('TOPPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('BOTTOMPADDING', (1, 0), (-1, -1), 8),
        ('TOPPADDING', (1, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),  # Thicker border around the table
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top of each cell
    ])

    # Manually alternate row background colors
    for i in range(1, len(vuln_data)):
        if i % 2 == 0:
            bg_color = colors.HexColor("#f2f2f2")  # Light gray
        else:
            bg_color = colors.white
        vuln_table_style.add('BACKGROUND', (0, i), (-1, i), bg_color)

    vuln_table.setStyle(vuln_table_style)
    elements.append(vuln_table)
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Recommendations
    elements.append(Paragraph("4. Recommendations", styleH))
    recommendations = (
        "Immediately address any critical vulnerabilities, continue to perform regular security assessments, "
        "and allocate resources to strengthen the security posture of our organization."
    )
    elements.append(Paragraph(recommendations, styleN))
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Conclusion
    elements.append(Paragraph("5. Conclusion", styleH))
    conclusion = (
        "Addressing these vulnerabilities will help mitigate significant risks to the organization and ensure compliance with "
        "industry standards. We recommend taking immediate action on any critical vulnerabilities and implementing long-term "
        "strategies to improve our security framework."
    )
    elements.append(Paragraph(conclusion, styleN))
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Appendix: Definitions
    elements.append(Paragraph("Appendix: Definitions", styleH))
    definitions_data = [
        ["Term", "Definition"],
        [Paragraph("CVE (Common Vulnerabilities and Exposure)", styleN), Paragraph(
            "A list of publicly disclosed computer security flaws, each identified by a unique number called a CVE ID.",
            styleN)],
        [Paragraph("Severity", styleN), Paragraph(
            "The level of impact that a vulnerability could have on the organisation, categorised as High, Medium, or Low with high being the most critical, etc.",
            styleN)],
        [Paragraph("Exploit", styleN), Paragraph(
            "A piece of code or technique that takes advantage of a vulnerability to compromise a system.",
            styleN)],
        [Paragraph("Vulnerability", styleN), Paragraph(
            "A weakness in a system that can be exploited by an attacker to perform malicious actions.",
            styleN)],
        [Paragraph("Vulnerability Scan", styleN), Paragraph(
            "Automated process that identifies, evaluates, and reports potential security weaknesses in an organisation’s IT systems.",
            styleN)],
    ]
    # Adjusted column widths to give more space to the "Term" column
    definitions_table = Table(definitions_data, colWidths=[2.3 * inch, 4.5 * inch])
    definitions_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),  # Blue background for the header row
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # White text color for the header row
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Left-align text
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # Further reduced font size
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('TOPPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('BOTTOMPADDING', (1, 0), (-1, -1), 8),
        ('TOPPADDING', (1, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),  # Thicker border around the table
    ])

    # Manually alternate row background colors for definitions table
    for i in range(1, len(definitions_data)):
        if i % 2 == 0:
            bg_color = colors.HexColor("#f2f2f2")  # Light gray
        else:
            bg_color = colors.white
        definitions_table_style.add('BACKGROUND', (0, i), (-1, i), bg_color)

    definitions_table.setStyle(definitions_table_style)
    elements.append(definitions_table)
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Appendix: Recommended Actions
    elements.append(
        Paragraph("Appendix: Recommended Actions to be Taken Based on Vulnerability Severity", styleH))
    actions_data = [
        ["Severity", "Description", "Recommended Actions"],
        [Paragraph("High", styleN), Paragraph(
            "Vulnerabilities that pose an immediate threat to the organisation and could lead to significant business impact if exploited.",
            styleN),
         Paragraph(
             "1. Immediate remediation within 24 hours.<br/>2. Apply security patches or mitigations.<br/>3. Increase monitoring on affected systems.<br/>4. Notify relevant stakeholders.",
             styleN)],
        [Paragraph("Medium", styleN), Paragraph(
            "Vulnerabilities that have a moderate impact and could lead to significant issues if left unaddressed.",
            styleN),
         Paragraph(
             "1. Remediate within 7 days.<br/>2. Apply available patches or mitigations.<br/>3. Monitor for signs of exploitation.",
             styleN)],
        [Paragraph("Low", styleN), Paragraph(
            "Vulnerabilities that have a minor impact and are less likely to be exploited but should still be addressed.",
            styleN),
         Paragraph(
             "1. Remediate within 30 days.<br/>2. Apply patches as part of regular maintenance.<br/>3. Monitor the situation to ensure no escalation.",
             styleN)],
    ]
    # Adjusted column widths to ensure table fits within the page
    actions_table = Table(actions_data, colWidths=[1.3 * inch, 2.5 * inch, 3 * inch])
    actions_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),  # Blue background for the header row
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # White text color for the header row
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Left-align text
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # Further reduced font size
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('TOPPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('BOTTOMPADDING', (1, 0), (-1, -1), 8),
        ('TOPPADDING', (1, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),  # Thicker border around the table
    ])

    # Manually alternate row background colors for actions table
    for i in range(1, len(actions_data)):
        if i % 2 == 0:
            bg_color = colors.HexColor("#f2f2f2")  # Light gray
        else:
            bg_color = colors.white
        actions_table_style.add('BACKGROUND', (0, i), (-1, i), bg_color)

    actions_table.setStyle(actions_table_style)
    elements.append(actions_table)
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Appendix: Detailed Vulnerability List
    elements.append(Paragraph("Appendix: Detailed Vulnerability List", styleH))
    elements.append(Spacer(1, 0.2 * inch))  # Add a small spacer for alignment

    # Extract relevant columns
    detailed_vulns = df[['IP', 'Severity', 'Summary', 'Solution']]

    # Prepare the data for the table
    detailed_vulns_data = [["IP Address", "Severity", "Summary", "Solution"]]
    for i, row in detailed_vulns.iterrows():
        if row['Severity'] == 'Log':
            continue
        detailed_vulns_data.append([
            Paragraph(str(row['IP']), styleN),  # IP Address
            Paragraph(str(row['Severity']), styleN),  # Severity
            Paragraph(str(row['Summary']), styleN),  # Summary
            Paragraph(str(row['Solution']), styleN)  # Solution
        ])

    # Adjust the column widths to fit the page
    detailed_vulns_table = Table(detailed_vulns_data,
                                 colWidths=[1.2 * inch, 0.7 * inch, 2.3 * inch, 2.6 * inch])

    # Apply the same styling as previous tables
    detailed_vulns_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),  # Blue background for the header row
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # White text color for the header row
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Left-align text for better readability
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # Slightly reduced font size for better fit
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('TOPPADDING', (0, 0), (-1, 0), 10),  # Added padding
        ('BOTTOMPADDING', (1, 0), (-1, -1), 8),
        ('TOPPADDING', (1, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Added padding
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Black grid lines
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),  # Thicker border around the table
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align text to the top of each cell
    ])

    # Manually alternate row background colors
    for i in range(1, len(detailed_vulns_data)):
        if i % 2 == 0:
            bg_color = colors.HexColor("#f2f2f2")  # Light gray
        else:
            bg_color = colors.white
        detailed_vulns_table_style.add('BACKGROUND', (0, i), (-1, i), bg_color)

    detailed_vulns_table.setStyle(detailed_vulns_table_style)
    elements.append(detailed_vulns_table)
    elements.append(Spacer(1, 0.75 * inch))  # Increased spacing

    # Build PDF
    doc.build(elements)

    print(
        colored("[INFO]", "cyan") +
        f" Executive report generated and saved to " +
        colored(f"{output_pdf_path}", attrs=['bold'])
    )
    print(
        colored("[SUCCESS]", "green") +
        " All scans completed. Reports generated successfully"
    )