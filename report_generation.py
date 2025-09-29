"""
Report generation functionality for the FET dashboard
"""
import io
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from data_utils import format_date_for_display



def generate_pdf_report(result):
    """Generate a comprehensive PDF report"""
    buffer = io.BytesIO()

    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    # Get styles
    styles = getSampleStyleSheet()

    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkblue
    )

    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=colors.darkgreen
    )

    # Story elements
    story = []

    # Extract key information
    from risk_scoring import translate_risk_to_business_language, get_alert_message

    query_name = result['query']['company_name']
    matched_name = result['match']['matched_company'] if result['match']['found'] else query_name
    factors = result['risk_assessment']['factors']
    exclusion_details = result['exclusion_details']
    wb_details = result.get('wb_details', [])  # NEW: World Bank details
    business_metrics = translate_risk_to_business_language(result)

    # Title
    story.append(Paragraph("🛡️ Risk Intelligence Report", title_style))
    story.append(Spacer(1, 12))

    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))

    exec_summary_data = [
        ['Company Name', matched_name],
        ['Risk Level', business_metrics['risk_level']],
        ['Risk Score', f"{business_metrics['enhanced_score']}/100"],
        ['Consensus', business_metrics['consensus_strength']],
        ['Total Exclusions', str(business_metrics['total_exclusions'])],
        ['Assessment Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    ]

    exec_table = Table(exec_summary_data, colWidths=[2 * inch, 3 * inch])
    exec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(exec_table)
    story.append(Spacer(1, 20))

    # Risk Assessment Details
    if business_metrics['total_exclusions'] > 0:
        story.append(Paragraph("Risk Assessment Details", heading_style))

        alert_info = get_alert_message(business_metrics['risk_level'], business_metrics, exclusion_details)
        story.append(Paragraph(f"<b>{alert_info['title']}</b>", subheading_style))
        story.append(Paragraph(alert_info['message'], styles['Normal']))
        story.append(Spacer(1, 12))

        # Score Breakdown
        story.append(Paragraph("Score Breakdown", subheading_style))
        score_breakdown = business_metrics['score_breakdown']

        breakdown_text = f"""
        <b>Final Score:</b> {business_metrics['enhanced_score']}/100<br/>
        <b>Consensus (40%):</b> {score_breakdown['consensus_score']:.0f}/100 - {score_breakdown['consensus_desc']}<br/>
        <b>Severity (30%):</b> {score_breakdown['severity_score']:.0f}/100 - {score_breakdown['severity_desc']}<br/>
        <b>Recency (20%):</b> {score_breakdown['recency_score']:.0f}/100 - {score_breakdown['recency_desc']}<br/>
        <b>Scope (10%):</b> {score_breakdown['scope_score']:.0f}/100 - {score_breakdown['scope_desc']}
        """

        story.append(Paragraph(breakdown_text, styles['Normal']))
        story.append(Spacer(1, 20))

    # Recommendations
    story.append(Paragraph("Operational Recommendations", heading_style))
    recommendations = result['recommendations']
    risk_level = business_metrics['risk_level']

    if risk_level in recommendations:
        current_recs = recommendations[risk_level]

        story.append(Paragraph("Project Team Actions", subheading_style))
        story.append(Paragraph(current_recs.get('project_team_action', 'Standard engagement procedures apply.'),
                               styles['Normal']))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Compliance Requirements", subheading_style))
        story.append(
            Paragraph(current_recs.get('compliance_role', 'Standard compliance processes apply.'), styles['Normal']))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Contract Requirements", subheading_style))
        story.append(
            Paragraph(current_recs.get('contract_scope', 'Standard contractual clauses apply.'), styles['Normal']))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Monitoring Approach", subheading_style))
        story.append(
            Paragraph(current_recs.get('monitoring', 'Standard monitoring procedures apply.'), styles['Normal']))

    # Exclusion Details Table (if any)
    if exclusion_details:
        story.append(PageBreak())
        story.append(Paragraph("Detailed Exclusion Records", heading_style))

        # Create table data
        df_details = pd.DataFrame(exclusion_details)

        # Select key columns for the PDF table
        table_columns = []
        table_headers = []

        if 'excluded_by' in df_details.columns:
            table_columns.append('excluded_by')
            table_headers.append('Financial Institution')

        if 'investor_country' in df_details.columns:
            table_columns.append('investor_country')
            table_headers.append('Country')

        if 'sub_category' in df_details.columns:
            table_columns.append('sub_category')
            table_headers.append('ESG Category')

        if 'exclusion_date_display' in df_details.columns:
            table_columns.append('exclusion_date_display')
            table_headers.append('Date')
        elif 'exclusion_date' in df_details.columns:
            df_details['exclusion_date_formatted'] = df_details['exclusion_date'].apply(format_date_for_display)
            table_columns.append('exclusion_date_formatted')
            table_headers.append('Date')

        if table_columns:
            # Prepare table data
            table_data = [table_headers]

            for _, row in df_details[table_columns].head(50).iterrows():  # Limit to 50 rows for PDF
                row_data = []
                for col in table_columns:
                    cell_value = str(row[col]) if pd.notna(row[col]) else 'N/A'
                    # Truncate long values
                    if len(cell_value) > 30:
                        cell_value = cell_value[:27] + '...'
                    row_data.append(cell_value)
                table_data.append(row_data)

            # Create and style the table
            detail_table = Table(table_data, repeatRows=1)
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))

            story.append(detail_table)

            if len(df_details) > 50:
                story.append(Spacer(1, 12))
                story.append(Paragraph(f"<i>Note: Showing first 50 of {len(df_details)} total exclusion records</i>",
                                       styles['Normal']))

    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} using Global Investor ESG Risk Intelligence Dashboard</i>",
        styles['Normal']))

    # Build PDF
    doc.build(story)

    # Get the PDF data
    buffer.seek(0)
    return buffer.getvalue()


def create_export_data(result, matched_name):
    """Create export data for CSV and JSON formats"""
    exclusion_details = result.get('exclusion_details', [])

    # CSV data
    csv_data = None
    if exclusion_details:
        export_df = pd.DataFrame(exclusion_details)
        csv_data = export_df.to_csv(index=False)

    return csv_data