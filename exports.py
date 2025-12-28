"""
Export functionality for Attribution MVP.
Supports CSV, Excel, and PDF report generation.
"""

import pandas as pd
import io
from datetime import datetime
from typing import Optional, Dict, List
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def export_to_csv(df: pd.DataFrame, filename: str = "export.csv") -> bytes:
    """
    Export DataFrame to CSV bytes.

    Args:
        df: DataFrame to export
        filename: Filename for the export

    Returns:
        CSV content as bytes
    """
    return df.to_csv(index=False).encode('utf-8')


def export_to_excel(
    dataframes: Dict[str, pd.DataFrame],
    filename: str = "export.xlsx"
) -> bytes:
    """
    Export multiple DataFrames to Excel with multiple sheets.

    Args:
        dataframes: Dictionary of {sheet_name: DataFrame}
        filename: Filename for the export

    Returns:
        Excel file content as bytes
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        currency_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })

        percent_format = workbook.add_format({
            'num_format': '0.0%',
            'border': 1
        })

        date_format = workbook.add_format({
            'num_format': 'yyyy-mm-dd',
            'border': 1
        })

        cell_format = workbook.add_format({
            'border': 1
        })

        for sheet_name, df in dataframes.items():
            # Write to sheet
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)

            worksheet = writer.sheets[sheet_name]

            # Write headers with formatting
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Apply formatting to data columns
            for col_num, col_name in enumerate(df.columns):
                # Auto-adjust column width
                max_len = max(
                    df[col_name].astype(str).apply(len).max(),
                    len(str(col_name))
                )
                worksheet.set_column(col_num, col_num, min(max_len + 2, 50))

                # Apply appropriate format based on column name/data
                if 'amount' in col_name.lower() or 'revenue' in col_name.lower() or 'value' in col_name.lower():
                    worksheet.set_column(col_num, col_num, None, currency_format)
                elif 'percent' in col_name.lower() or 'split' in col_name.lower():
                    worksheet.set_column(col_num, col_num, None, percent_format)
                elif 'date' in col_name.lower():
                    worksheet.set_column(col_num, col_num, None, date_format)
                else:
                    worksheet.set_column(col_num, col_num, None, cell_format)

    output.seek(0)
    return output.read()


def generate_pdf_report(
    title: str,
    summary_data: Dict[str, any],
    tables: Dict[str, pd.DataFrame],
    filename: str = "report.pdf"
) -> bytes:
    """
    Generate a PDF report with summary data and tables.

    Args:
        title: Report title
        summary_data: Dictionary of key metrics
        tables: Dictionary of {table_title: DataFrame}
        filename: Filename for the report

    Returns:
        PDF content as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=12
    )

    # Add title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Add generation timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Generated: {timestamp}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * inch))

    # Add summary metrics
    if summary_data:
        elements.append(Paragraph("Executive Summary", heading_style))

        summary_table_data = [['Metric', 'Value']]
        for key, value in summary_data.items():
            if isinstance(value, (int, float)):
                if 'revenue' in key.lower() or 'value' in key.lower() or 'amount' in key.lower():
                    formatted_value = f"${value:,.2f}"
                elif 'percent' in key.lower():
                    formatted_value = f"{value:.1f}%"
                else:
                    formatted_value = f"{value:,}"
            else:
                formatted_value = str(value)
            summary_table_data.append([key, formatted_value])

        summary_table = Table(summary_table_data, colWidths=[3.5 * inch, 2.5 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 0.5 * inch))

    # Add data tables
    for table_title, df in tables.items():
        if df.empty:
            continue

        elements.append(PageBreak())
        elements.append(Paragraph(table_title, heading_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Convert DataFrame to list of lists
        data = [df.columns.tolist()] + df.values.tolist()

        # Truncate if too many rows
        if len(data) > 51:  # 50 rows + header
            data = data[:51]
            elements.append(Paragraph(f"Showing first 50 of {len(df)} rows", styles['Italic']))

        # Format data
        formatted_data = []
        for row_idx, row in enumerate(data):
            formatted_row = []
            for col_idx, cell in enumerate(row):
                if row_idx > 0:  # Not header
                    if isinstance(cell, (int, float)):
                        col_name = df.columns[col_idx].lower()
                        if 'amount' in col_name or 'revenue' in col_name or 'value' in col_name:
                            formatted_row.append(f"${cell:,.2f}")
                        elif 'percent' in col_name or 'split' in col_name:
                            formatted_row.append(f"{cell:.1%}")
                        else:
                            formatted_row.append(str(cell))
                    else:
                        formatted_row.append(str(cell))
                else:
                    formatted_row.append(str(cell))
            formatted_data.append(formatted_row)

        # Calculate column widths dynamically
        num_cols = len(df.columns)
        available_width = 7 * inch
        col_width = available_width / num_cols

        table = Table(formatted_data, colWidths=[col_width] * num_cols, repeatRows=1)

        # Style the table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))

    # Build PDF
    doc.build(elements)

    buffer.seek(0)
    return buffer.read()


def create_partner_performance_report(
    partner_data: pd.DataFrame,
    attribution_data: pd.DataFrame,
    date_range: str
) -> bytes:
    """
    Create a comprehensive partner performance PDF report.

    Args:
        partner_data: DataFrame with partner performance metrics
        attribution_data: DataFrame with attribution details
        date_range: String describing the date range

    Returns:
        PDF content as bytes
    """
    summary_data = {
        'Report Period': date_range,
        'Total Partners': len(partner_data),
        'Total Attributed Revenue': partner_data['attributed_amount'].sum() if not partner_data.empty else 0,
        'Average Revenue per Partner': partner_data['attributed_amount'].mean() if not partner_data.empty else 0,
        'Total Accounts Influenced': partner_data['accounts_influenced'].sum() if not partner_data.empty and 'accounts_influenced' in partner_data.columns else 0,
    }

    tables = {
        'Partner Performance Summary': partner_data,
    }

    if not attribution_data.empty:
        tables['Detailed Attribution'] = attribution_data

    return generate_pdf_report(
        title="Partner Performance Report",
        summary_data=summary_data,
        tables=tables
    )


def create_account_drilldown_report(
    account_name: str,
    use_cases: pd.DataFrame,
    partners: pd.DataFrame,
    revenue: pd.DataFrame,
    attribution: pd.DataFrame
) -> bytes:
    """
    Create a comprehensive account drilldown PDF report.

    Args:
        account_name: Name of the account
        use_cases: DataFrame with use case information
        partners: DataFrame with partner relationships
        revenue: DataFrame with revenue events
        attribution: DataFrame with attribution breakdown

    Returns:
        PDF content as bytes
    """
    total_revenue = revenue['amount'].sum() if not revenue.empty else 0
    total_attributed = attribution['attributed_amount'].sum() if not attribution.empty else 0

    summary_data = {
        'Account': account_name,
        'Total Revenue (30d)': total_revenue,
        'Total Attributed Revenue': total_attributed,
        'Attribution Coverage': (total_attributed / total_revenue * 100) if total_revenue > 0 else 0,
        'Active Use Cases': len(use_cases),
        'Engaged Partners': len(partners),
    }

    tables = {
        'Use Cases': use_cases,
        'Partner Relationships': partners,
        'Revenue Attribution': attribution,
    }

    return generate_pdf_report(
        title=f"Account Drilldown: {account_name}",
        summary_data=summary_data,
        tables=tables
    )


def generate_partner_statement_pdf(
    partner_id: str,
    partner_name: str,
    ledger_entries: List,
    targets: List,
    report_period: str = None
) -> bytes:
    """
    Generate a partner-specific attribution statement PDF.

    Shows all deals where this partner received attribution credit,
    with detailed breakdown of their contribution and payout amounts.

    Args:
        partner_id: Partner identifier
        partner_name: Display name for partner
        ledger_entries: List of LedgerEntry objects for this partner
        targets: List of all AttributionTarget objects
        report_period: Optional period description (e.g., "January 2025")

    Returns:
        PDF content as bytes
    """
    from reportlab.pdfgen import canvas

    # Filter ledger entries for this partner
    partner_ledger = [entry for entry in ledger_entries if entry.partner_id == partner_id]

    if not partner_ledger:
        # Return empty statement if no attribution
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"Partner Attribution Statement: {partner_name}", styles['Title']))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("No attribution entries found for this partner in the selected period.", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer.read()

    # Calculate summary metrics
    total_attributed_value = sum(entry.attributed_value for entry in partner_ledger)
    num_deals = len(partner_ledger)
    avg_split = sum(entry.split_percentage for entry in partner_ledger) / len(partner_ledger) if partner_ledger else 0

    # Create target lookup
    target_lookup = {t.id: t for t in targets}

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch
    )

    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=20
    )

    # COVER PAGE
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph(f"Partner Attribution Statement", title_style))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(partner_name, styles['Heading2']))
    elements.append(Spacer(1, 0.5*inch))

    # Statement details
    statement_info = [
        ['Partner ID:', partner_id],
        ['Statement Period:', report_period or datetime.now().strftime("%B %Y")],
        ['Generated:', datetime.now().strftime("%B %d, %Y at %I:%M %p")],
        ['Status:', 'Draft' if not report_period else 'Final']
    ]

    info_table = Table(statement_info, colWidths=[2*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))

    elements.append(info_table)
    elements.append(PageBreak())

    # SUMMARY
    elements.append(Paragraph("Attribution Summary", heading_style))

    summary_data = [
        ['Metric', 'Value'],
        ['Total Attributed Revenue', f'${total_attributed_value:,.2f}'],
        ['Number of Deals Influenced', str(num_deals)],
        ['Average Attribution Split', f'{avg_split:.1%}'],
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1f2937')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*inch))

    # DEAL BREAKDOWN
    elements.append(Paragraph("Deal-by-Deal Breakdown", heading_style))

    deal_data = [['Deal ID', 'Deal Value', 'Your Split %', 'Attributed $', 'Rule Applied']]

    for entry in sorted(partner_ledger, key=lambda e: e.attributed_value, reverse=True):
        target = target_lookup.get(entry.target_id)
        target_id_str = target.external_id if target else f"Target #{entry.target_id}"
        target_value = target.value if target else 0

        deal_data.append([
            str(target_id_str)[:20],
            f'${target_value:,.0f}',
            f'{entry.split_percentage:.1%}',
            f'${entry.attributed_value:,.2f}',
            f'Rule #{entry.rule_id}'
        ])

    deal_table = Table(deal_data, colWidths=[1.5*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
    deal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eff6ff')]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(deal_table)
    elements.append(Spacer(1, 0.5*inch))

    # FOOTER NOTE
    elements.append(Paragraph(
        "<i>This statement reflects attribution calculations as of the generation date. "
        "For questions or disputes, please contact your Partner Operations team.</i>",
        styles['Normal']
    ))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


def generate_bulk_partner_statements(
    ledger_entries: List,
    targets: List,
    partners: Dict[str, str],
    report_period: str = None
) -> bytes:
    """
    Generate attribution statements for ALL partners and package into ZIP file.

    This is used for monthly payout processes where you need to send statements
    to all partners simultaneously.

    Args:
        ledger_entries: List of all LedgerEntry objects
        targets: List of all AttributionTarget objects
        partners: Dictionary mapping partner_id -> partner_name
        report_period: Optional period description (e.g., "January 2025")

    Returns:
        ZIP file content as bytes containing individual PDF statements
    """
    import zipfile

    # Group ledger entries by partner
    partners_with_attribution = {}
    for entry in ledger_entries:
        if entry.partner_id not in partners_with_attribution:
            partners_with_attribution[entry.partner_id] = []
        partners_with_attribution[entry.partner_id].append(entry)

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Generate PDF for each partner
        for partner_id, partner_entries in partners_with_attribution.items():
            partner_name = partners.get(partner_id, partner_id)

            # Generate partner statement PDF
            partner_pdf = generate_partner_statement_pdf(
                partner_id=partner_id,
                partner_name=partner_name,
                ledger_entries=ledger_entries,  # Pass all entries, function will filter
                targets=targets,
                report_period=report_period
            )

            # Sanitize filename (remove special characters)
            safe_partner_name = "".join(c for c in partner_name if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = f"{safe_partner_name}_{partner_id}_statement.pdf"

            # Add PDF to ZIP
            zip_file.writestr(filename, partner_pdf)

        # Add a README file to the ZIP
        readme_content = f"""Partner Attribution Statements
================================

Report Period: {report_period or 'Current Period'}
Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

This ZIP file contains individual attribution statements for all partners
with attributed revenue in the selected period.

Files included: {len(partners_with_attribution)} partner statements

Instructions:
1. Extract all files from this ZIP archive
2. Send each PDF to the respective partner
3. Keep a copy for your records

For questions, contact your Partner Operations team.
"""
        zip_file.writestr("README.txt", readme_content)

    zip_buffer.seek(0)
    return zip_buffer.read()
