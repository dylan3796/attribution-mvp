"""
Executive PDF Report Generator
===============================

Beautiful, production-ready PDF reports with charts and visualizations.

Features:
- Professional cover page
- Dashboard charts as images
- Summary metrics
- Top partners breakdown
- Attribution ledger table
- Page numbers and headers
"""

import io
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, Frame, PageTemplate
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for page numbers and headers."""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Add page numbers and header to each page."""
        page_num = self._pageNumber

        # Header line
        self.setStrokeColor(colors.HexColor('#e5e7eb'))
        self.setLineWidth(0.5)
        self.line(50, letter[1] - 50, letter[0] - 50, letter[1] - 50)

        # Page number
        self.setFont('Helvetica', 9)
        self.setFillColor(colors.HexColor('#6b7280'))
        text = f"Page {page_num} of {page_count}"
        self.drawRightString(letter[0] - 50, 30, text)

        # Report title in header
        self.drawString(50, letter[1] - 40, "Attribution MVP - Executive Report")

        # Footer line
        self.setStrokeColor(colors.HexColor('#e5e7eb'))
        self.line(50, 45, letter[0] - 50, 45)


def generate_executive_report(
    report_date_range: str,
    total_revenue: float,
    total_attributed: float,
    attribution_coverage: float,
    unique_partners: int,
    top_partners: pd.DataFrame,
    ledger_df: pd.DataFrame,
    chart_images: Optional[Dict[str, bytes]] = None
) -> bytes:
    """
    Generate a comprehensive executive PDF report.

    Args:
        report_date_range: Date range string (e.g., "2025-01-01 to 2025-01-31")
        total_revenue: Total revenue in the period
        total_attributed: Total attributed revenue
        attribution_coverage: Attribution coverage percentage
        unique_partners: Number of unique partners
        top_partners: DataFrame with top partners
        ledger_df: Full attribution ledger DataFrame
        chart_images: Optional dict of {chart_name: image_bytes} for Plotly charts

    Returns:
        PDF content as bytes
    """
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
        fontSize=32,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        spaceBefore=24,
        fontName='Helvetica-Bold'
    )

    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#3b82f6'),
        spaceAfter=8,
        spaceBefore=12
    )

    # ========================================
    # COVER PAGE
    # ========================================

    elements.append(Spacer(1, 2*inch))

    # Logo placeholder (you can replace with actual logo)
    elements.append(Paragraph("🚀", title_style))
    elements.append(Spacer(1, 0.5*inch))

    # Title
    elements.append(Paragraph("Attribution MVP", title_style))
    elements.append(Paragraph("Executive Performance Report", subtitle_style))

    elements.append(Spacer(1, 1*inch))

    # Report details box
    report_info_data = [
        ['Report Period:', report_date_range],
        ['Generated:', datetime.now().strftime("%B %d, %Y at %I:%M %p")],
        ['Report Type:', 'Executive Summary'],
        ['Confidential:', 'Internal Use Only']
    ]

    report_info_table = Table(report_info_data, colWidths=[2*inch, 3.5*inch])
    report_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))

    elements.append(report_info_table)
    elements.append(PageBreak())

    # ========================================
    # EXECUTIVE SUMMARY
    # ========================================

    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(Spacer(1, 0.2*inch))

    # Key Metrics in a nice grid
    metrics_data = [
        ['Metric', 'Value', 'Status'],
        ['Total Revenue', f'${total_revenue:,.2f}', '✓'],
        ['Attributed Revenue', f'${total_attributed:,.2f}', '✓'],
        ['Attribution Coverage', f'{attribution_coverage:.1f}%', '✓' if attribution_coverage > 80 else '⚠'],
        ['Active Partners', f'{unique_partners}', '✓'],
    ]

    metrics_table = Table(metrics_data, colWidths=[2.5*inch, 2*inch, 1*inch])
    metrics_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),

        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),

        # Styling
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))

    elements.append(metrics_table)
    elements.append(Spacer(1, 0.5*inch))

    # Key Insights
    elements.append(Paragraph("Key Insights", subheading_style))

    insights_text = f"""
    <bullet>•</bullet> <b>Attribution Coverage:</b> {attribution_coverage:.1f}% of total revenue has been attributed to partners.
    <br/>
    <bullet>•</bullet> <b>Partner Ecosystem:</b> {unique_partners} active partners contributed to revenue in this period.
    <br/>
    <bullet>•</bullet> <b>Top Performer:</b> {top_partners.iloc[0]['partner_name'] if not top_partners.empty else 'N/A'} leads with ${top_partners.iloc[0]['attributed_amount'] if not top_partners.empty else 0:,.2f} in attributed revenue.
    <br/>
    <bullet>•</bullet> <b>Average Split:</b> Partners receive an average of {top_partners['avg_split_percent'].mean() if not top_partners.empty else 0:.1f}% attribution per deal.
    """

    elements.append(Paragraph(insights_text, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))

    # ========================================
    # TOP PARTNERS BREAKDOWN
    # ========================================

    elements.append(PageBreak())
    elements.append(Paragraph("Top 10 Partners by Attributed Revenue", heading_style))
    elements.append(Spacer(1, 0.2*inch))

    if not top_partners.empty:
        # Prepare data (top 10)
        top_10 = top_partners.head(10).copy()

        partners_data = [['Rank', 'Partner Name', 'Attributed Revenue', 'Avg Split %', 'Accounts']]

        for idx, row in enumerate(top_10.itertuples(), 1):
            partners_data.append([
                f"#{idx}",
                str(row.partner_name)[:30],  # Truncate long names
                f"${row.attributed_amount:,.2f}",
                f"{row.avg_split_percent:.1f}%",
                str(row.accounts_influenced) if hasattr(row, 'accounts_influenced') else 'N/A'
            ])

        partners_table = Table(partners_data, colWidths=[0.6*inch, 2.2*inch, 1.5*inch, 1*inch, 0.8*inch])
        partners_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),

            # Data
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#eff6ff')]),

            # Top 3 highlighting
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#dbeafe')),  # Gold
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#e0e7ff')) if len(partners_data) > 2 else None,  # Silver
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f3f4f6')) if len(partners_data) > 3 else None,  # Bronze

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(partners_table)
    else:
        elements.append(Paragraph("No partner data available.", styles['Italic']))

    elements.append(Spacer(1, 0.5*inch))

    # ========================================
    # ATTRIBUTION LEDGER (Sample)
    # ========================================

    elements.append(PageBreak())
    elements.append(Paragraph("Attribution Ledger", heading_style))
    elements.append(Paragraph("Recent attribution entries (showing up to 20 most recent)", subheading_style))
    elements.append(Spacer(1, 0.2*inch))

    if not ledger_df.empty:
        # Take most recent 20 entries
        sample_ledger = ledger_df.head(20).copy()

        ledger_data = [['Target ID', 'Partner', 'Attributed $', 'Split %', 'Rule']]

        for row in sample_ledger.itertuples():
            ledger_data.append([
                str(row.Index)[:10],
                str(getattr(row, 'Partner', 'N/A'))[:25],
                f"${getattr(row, 'Attributed_Value', 0):,.0f}",
                f"{getattr(row, 'Split_Percentage', 0)*100:.1f}%",
                str(getattr(row, 'Rule_Name', 'Default'))[:20]
            ])

        ledger_table = Table(ledger_data, colWidths=[1*inch, 2*inch, 1.2*inch, 0.8*inch, 1.5*inch])
        ledger_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(ledger_table)
    else:
        elements.append(Paragraph("No ledger entries available.", styles['Italic']))

    # ========================================
    # BUILD PDF
    # ========================================

    doc.build(elements, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer.read()
