import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from data_utils import get_enhanced_company_suggestions

# Import your existing FET checker
try:
    from fet_core2 import EnhancedFETChecker
except ImportError:
    try:
        from hrr3 import EnhancedFETChecker
    except ImportError:
        try:
            from fet_checker import EnhancedFETChecker
        except ImportError:
            try:
                from main import EnhancedFETChecker
            except ImportError:
                st.error(
                    "⚠️ Could not import EnhancedFETChecker. Please ensure your FET checker file is in the same directory.")
                st.stop()

# Configure page
st.set_page_config(
    page_title="Global Investor ESG Exclusions Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)



# Initialize session state
if 'checker' not in st.session_state:
    st.session_state.checker = None
    st.session_state.analysis_result = None


def format_date_for_display(date_value) -> str:
    """Enhanced function to format dates with full date display (YYYY-MM-DD)"""
    import re
    import pandas as pd

    if pd.isna(date_value) or not str(date_value).strip():
        return "N/A"

    date_str = str(date_value).strip()

    # If it's already in clean format, return as-is
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # Handle multiple dates (show first + count)
    if ';' in date_str:
        dates = [d.strip() for d in date_str.split(';') if d.strip()]
        if dates and re.match(r'^\d{4}-\d{2}-\d{2}$', dates[0]):
            if len(dates) > 1:
                return f"{dates[0]} (+{len(dates) - 1} more)"
            else:
                return dates[0]

    # Try to parse different date formats and return YYYY-MM-DD
    try:
        # Try pandas date parsing
        parsed_date = pd.to_datetime(date_str, errors='coerce')
        if not pd.isna(parsed_date):
            return parsed_date.strftime('%Y-%m-%d')
    except:
        pass

    # Handle corrupted timestamp data - extract first 13 digits and convert
    if date_str.isdigit() and len(date_str) > 13:
        try:
            timestamp_str = date_str[:13]
            timestamp = int(timestamp_str)
            dt = pd.to_datetime(timestamp, unit='ms', errors='coerce')
            if not pd.isna(dt):
                return dt.strftime('%Y-%m-%d')
        except:
            pass

    # Try to extract and format date components
    date_patterns = [
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD or YYYY-M-D
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY or M/D/YYYY
        r'(\d{1,2})\.(\d{1,2})\.(\d{4})',  # DD.MM.YYYY or D.M.YYYY
    ]

    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                try:
                    if pattern == date_patterns[0]:  # YYYY-MM-DD format
                        year, month, day = groups
                    elif pattern == date_patterns[1]:  # MM/DD/YYYY format
                        month, day, year = groups
                    else:  # DD.MM.YYYY format
                        day, month, year = groups

                    # Validate and format
                    year, month, day = int(year), int(month), int(day)
                    if 1900 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    continue

    # Fallback: Try to extract just year
    year_match = re.search(r'\b(20\d{2})\b', date_str)
    if year_match:
        return f"{year_match.group()}-01-01"  # Default to Jan 1st if only year available

    return "Invalid Date"


@st.cache_resource(show_spinner=False)  # Simple caching like the original
def load_fet_checker_cached(uploaded_file_data: bytes = None):
    """Load FET checker with caching to prevent multiple loads"""
    try:
        checker = EnhancedFETChecker()

        # Try to load database
        if checker.load_database(uploaded_file_data):
            return checker
        else:
            return None
    except Exception as e:
        st.error(f"❌ Failed to initialize FET checker: {e}")
        return None


def load_fet_checker(uploaded_file_data: bytes = None):
    """Wrapper to handle uploaded data (can't cache functions with mutable args)"""
    if uploaded_file_data is None:
        return load_fet_checker_cached()
    else:
        # For uploaded files, we need to create a new instance
        try:
            checker = EnhancedFETChecker()
            if checker.load_database(uploaded_file_data):
                return checker
            else:
                return None
        except Exception as e:
            st.error(f"❌ Failed to initialize FET checker: {e}")
            return None


def calculate_business_risk_score(result):
    """UPDATED: Simplified scoring aligned with fet_recommendations.py (no Critical Risk override)"""

    factors = result['risk_assessment']['factors']
    exclusion_details = result['exclusion_details']

    # Handle case with no exclusions early
    if not exclusion_details or len(exclusion_details) == 0:
        return {
            'final_score': 0,
            'consensus_score': 0,
            'consensus_desc': 'No Exclusions Found',
            'severity_score': 0,
            'severity_desc': 'No Issues Identified',
            'recency_score': 0,
            'recency_desc': 'No Recent Activity',
            'scope_score': 0,
            'scope_desc': 'No Exclusions',
            'breakdown': "No exclusions found - company appears clear for engagement"
        }

    df_details = pd.DataFrame(exclusion_details)
    total_exclusions = len(exclusion_details)

    if total_exclusions == 0:  # Double-check
        return {
            'final_score': 0,
            'consensus_score': 0,
            'consensus_desc': 'No Exclusions Found',
            'severity_score': 0,
            'severity_desc': 'No Issues Identified',
            'recency_score': 0,
            'recency_desc': 'No Recent Activity',
            'scope_score': 0,
            'scope_desc': 'No Exclusions',
            'breakdown': "No exclusions found - company appears clear for engagement"
        }

    # Factor 1: Consensus Strength (40% weight)
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)

    # Simplified consensus scoring
    if investors >= 20 or countries >= 6:
        consensus_score = 90
        consensus_desc = "Very Strong Multi-Country Consensus"
    elif investors >= 10 and countries >= 3:
        consensus_score = 70
        consensus_desc = "Strong Multi-Country Consensus"
    elif investors >= 5 and countries >= 2:
        consensus_score = 55
        consensus_desc = "Moderate Multi-Country Consensus"
    elif investors >= 3 or countries >= 2:
        consensus_score = 40
        consensus_desc = "Limited Multi-Country Consensus"
    else:
        consensus_score = 25
        consensus_desc = "Minimal Consensus"

    # Factor 2: Issue Severity (30% weight)
    severity_score = 50  # Default for any exclusions
    severity_desc = "Other Business Issues"

    # Check both motivation and category columns for better detection
    all_text_columns = []
    if 'motivation_canonical' in df_details.columns:
        all_text_columns.extend(df_details['motivation_canonical'].astype(str).str.lower().tolist())
    if 'main_category' in df_details.columns:
        all_text_columns.extend(df_details['main_category'].astype(str).str.lower().tolist())
    if 'motivation' in df_details.columns:
        all_text_columns.extend(df_details['motivation'].astype(str).str.lower().tolist())

    combined_text = ' '.join(all_text_columns).lower()

    # Issue severity assessment
    if any(term in combined_text for term in
           ['forced labour', 'child labour', 'forced labor', 'child labor', 'slavery']):
        severity_score = 95
        severity_desc = "Critical Human Rights Violations"
    elif any(term in combined_text for term in ['corruption', 'bribery', 'fraud', 'money laundering']):
        severity_score = 85
        severity_desc = "Serious Governance Issues"
    elif any(term in combined_text for term in ['thermal coal', 'fossil expansion', 'coal mining', 'coal power']):
        # Thermal coal severity depends on scope
        if 'scope_normalized' in df_details.columns and (df_details['scope_normalized'] == 'sector').any():
            severity_score = 80
            severity_desc = "Major Climate Concerns (Sector-Wide Coal)"
        else:
            severity_score = 70
            severity_desc = "Major Climate Concerns (Coal)"
    elif any(term in combined_text for term in
             ['climate', 'carbon', 'emission', 'fossil', 'oil', 'gas', 'environmental']):
        severity_score = 65
        severity_desc = "Climate & Environmental Concerns"
    elif any(term in combined_text for term in
             ['human rights', 'norms-based', 'norms based', 'labour rights', 'labor rights']):
        severity_score = 60
        severity_desc = "General ESG Concerns"
    elif any(term in combined_text for term in ['controversial', 'conduct', 'business practices']):
        severity_score = 55
        severity_desc = "Business Conduct Issues"

    # Factor 3: Recent Activity (20% weight)
    recent_exclusions = factors.get('recent_exclusions', 0)

    # Safe division to avoid division by zero
    if total_exclusions > 0:
        recency_ratio = recent_exclusions / total_exclusions
    else:
        recency_ratio = 0  # No exclusions = no recent activity

    if recency_ratio >= 0.8:
        recency_score = 100
        recency_desc = "Very Recent Activity"
    elif recency_ratio >= 0.5:
        recency_score = 80
        recency_desc = "Recent Activity"
    elif recency_ratio >= 0.3:
        recency_score = 60
        recency_desc = "Mixed Timeline"
    elif recency_ratio >= 0.1:
        recency_score = 40
        recency_desc = "Some Recent Activity"
    else:
        recency_score = 20
        recency_desc = "Historical Issues Only"

    # Factor 4: Scope Impact (10% weight)
    scope_score = 70  # Default company-level
    scope_desc = "Company-Level"

    if 'scope_normalized' in df_details.columns:
        if (df_details['scope_normalized'] == 'sector').any():
            scope_score = 100
            scope_desc = "Sector-Wide Impact"

    # Calculate weighted final score
    final_score = (
            consensus_score * 0.40 +
            severity_score * 0.30 +
            recency_score * 0.20 +
            scope_score * 0.10
    )

    # Create breakdown explanation
    breakdown = f"""
    Consensus (40%): {consensus_score:.0f}/100 - {consensus_desc}
    • {investors} investors, {countries} countries
    Severity (30%): {severity_score:.0f}/100 - {severity_desc}
    Recency (20%): {recency_score:.0f}/100 - {recency_desc}
    Scope (10%): {scope_score:.0f}/100 - {scope_desc}
    """

    return {
        'final_score': final_score,
        'consensus_score': consensus_score,
        'consensus_desc': consensus_desc,
        'severity_score': severity_score,
        'severity_desc': severity_desc,
        'recency_score': recency_score,
        'recency_desc': recency_desc,
        'scope_score': scope_score,
        'scope_desc': scope_desc,
        'breakdown': breakdown.strip()
    }


def determine_risk_level_and_explanation(score_data, factors):
    """UPDATED: Align with fet_recommendations.py - only 3 risk levels"""

    score = score_data['final_score']
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)
    total_exclusions = factors.get('total_exclusions', 0)

    # Use the same logic as in fet_recommendations.py
    if score >= 80:  # High Risk threshold
        level = "High Risk"
        explanation = f"Strong consensus ({investors} investors, {countries} countries) on significant concerns"
        color_class = "high-risk"
    elif score >= 50:  # Medium Risk threshold
        level = "Medium Risk"
        explanation = f"Moderate consensus ({investors} investors, {countries} countries) requiring enhanced due diligence"
        color_class = "medium-risk"
    else:
        level = "Low Risk"
        explanation = f"Limited consensus ({investors} investors) with manageable concerns" if investors > 0 else "No significant exclusions identified in our database"
        color_class = "low-risk"

    return level, explanation, color_class


def translate_risk_to_business_language(result):
    """UPDATED: Simplified to align with fet_recommendations.py risk levels"""

    factors = result['risk_assessment']['factors']

    # Calculate the enhanced multi-factor score
    score_data = calculate_business_risk_score(result)

    # Determine risk level and explanation
    risk_level, explanation, color_class = determine_risk_level_and_explanation(score_data, factors)

    # Build consensus description
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)
    consensus_strength = f"{investors} investors across {countries} countries"

    # Confidence assessment
    confidence = factors.get('confidence_score', 1.0)
    if confidence >= 0.9:
        confidence_desc = "Very High"
    elif confidence >= 0.7:
        confidence_desc = "High"
    elif confidence >= 0.5:
        confidence_desc = "Moderate"
    else:
        confidence_desc = "Low"

    return {
        'enhanced_score': int(round(score_data['final_score'])),
        'risk_level': risk_level,
        'color_class': color_class,
        'score_explanation': explanation,
        'consensus_strength': consensus_strength,
        'confidence_desc': confidence_desc,
        'score_breakdown': score_data,
        'total_exclusions': len(result.get('exclusion_details', [])),
        'is_widespread': investors >= 5 or countries >= 3,

        # Keep some original metrics for comparison
        'raw_score': factors.get('consensus_adjusted_score', 0),
        'percentile': factors.get('percentile', 0)
    }


def get_recent_activity_and_latest_date(df_details):
    """UPDATED: Get full date information instead of just year"""
    current_year = datetime.now().year
    recent_activity = 0
    latest_date = "N/A"

    if df_details.empty:
        return recent_activity, latest_date

    # Try to get actual dates from the date columns
    dates_found = []

    # Try different date column names
    date_columns = ['exclusion_date_display', 'exclusion_date', 'Date of FI Exclusion list', 'date']
    for col in date_columns:
        if col in df_details.columns:
            for date_val in df_details[col].dropna():
                formatted_date = format_date_for_display(date_val)
                if formatted_date != "N/A" and formatted_date != "Invalid Date":
                    try:
                        # Try to parse the date
                        parsed_date = pd.to_datetime(formatted_date, errors='coerce')
                        if not pd.isna(parsed_date):
                            dates_found.append(parsed_date)
                    except:
                        continue
            if dates_found:
                break

    # If we found dates, calculate metrics
    if dates_found:
        dates_series = pd.Series(dates_found)
        # Count recent activity (last 2 years)
        two_years_ago = datetime.now() - timedelta(days=730)
        recent_activity = int((dates_series >= two_years_ago).sum())
        # Get latest date
        latest_date = dates_series.max().strftime('%Y-%m-%d')

    return recent_activity, latest_date


def get_alert_message(risk_level, business_metrics, exclusion_details):
    """UPDATED: Generate alert messages aligned with fet_recommendations.py"""
    consensus = business_metrics['consensus_strength']

    if risk_level == "High Risk":
        return {
            'level': 'high',
            'title': '🔴 HIGH RISK - Executive Approval Required',
            'message': f"Significant ESG concerns identified with {consensus}. Engagement may proceed for strategic clients with executive approval and tightly defined, harm-reducing scopes. Default: Avoid scopes enabling flagged activities. Enhanced Due Diligence mandatory including policy evidence (UNGC/OECD/ILO) plus third-party reports."
        }
    elif risk_level == "Medium Risk":
        return {
            'level': 'medium',
            'title': '🟡 MEDIUM RISK - Controlled Engagement with Enhanced Oversight',
            'message': f"Moderate ESG concerns identified with {consensus}. Engagement is viable with targeted mitigations and scope guardrails that support business continuity. Apply scoping guardrails to ensure work does not enable flagged activities. Pre-engagement briefing with Compliance and Sustainability teams required."
        }
    else:
        return {
            'level': 'low',
            'title': '🟢 LOW RISK - Standard Procedures with Monitoring',
            'message': f"No significant ESG concerns identified. Proceed with standard controls. Standard due diligence with quarterly monitoring is appropriate for this engagement." if exclusion_details else "No institutional exclusions found in our database. This company appears clear for standard business engagement with normal due diligence procedures."
        }


def calculate_auto_flags(result):
    """Calculate warning flags with business-friendly descriptions"""
    flags = []

    if not result['match']['found'] or not result['exclusion_details']:
        return flags

    factors = result['risk_assessment']['factors']
    df_details = pd.DataFrame(result['exclusion_details'])

    # High-priority institutional flags
    if factors.get('unique_investors', 0) >= 15:
        flags.append(('15+ Financial Institutions', 'flag'))
    elif factors.get('unique_investors', 0) >= 10:
        flags.append(('10+ Financial Institutions', 'flag'))
    elif factors.get('unique_investors', 0) >= 5:
        flags.append(('5+ Financial Institutions', 'flag-warning'))

    if factors.get('unique_countries', 0) >= 8:
        flags.append(('8+ Countries', 'flag'))
    elif factors.get('unique_countries', 0) >= 5:
        flags.append(('5+ Countries', 'flag'))
    elif factors.get('unique_countries', 0) >= 3:
        flags.append(('Multi-Country', 'flag-warning'))

    # Specific serious issue flags
    if 'motivation_canonical' in df_details.columns:
        motivations = df_details['motivation_canonical'].astype(str).str.lower()
        if motivations.str.contains('forced labour|child labour', na=False).any():
            flags.append(('Labour Rights Issues', 'flag'))
        if motivations.str.contains('corruption|bribery', na=False).any():
            flags.append(('Corruption Concerns', 'flag'))
        if motivations.str.contains('thermal coal', na=False).any():
            flags.append(('Coal-Related', 'flag-warning'))

    # Sector-level exclusions
    if 'scope_normalized' in df_details.columns:
        if (df_details['scope_normalized'] == 'sector').any():
            flags.append(('Sector-Wide Exclusion', 'flag'))

    # Recent activity flag
    recent_activity = factors.get('recent_exclusions', 0)
    if recent_activity >= 5:
        flags.append(('Recent Activity', 'flag-info'))

    return flags


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
    query_name = result['query']['company_name']
    matched_name = result['match']['matched_company'] if result['match']['found'] else query_name
    factors = result['risk_assessment']['factors']
    exclusion_details = result['exclusion_details']
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
        f"<i>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} using Global ESG Risk Intelligence Dashboard</i>",
        styles['Normal']))

    # Build PDF
    doc.build(story)

    # Get the PDF data
    buffer.seek(0)
    return buffer.getvalue()


def display_comprehensive_dashboard(result):
    """UPDATED: Display dashboard aligned with fet_recommendations.py"""

    # Extract key information
    query_name = result['query']['company_name']
    matched_name = result['match']['matched_company'] if result['match']['found'] else query_name
    factors = result['risk_assessment']['factors']
    exclusion_details = result['exclusion_details']

    # Use enhanced multi-factor scoring aligned with fet_recommendations.py
    business_metrics = translate_risk_to_business_language(result)
    risk_level = business_metrics['risk_level']  # Only 3 levels now
    color_class = business_metrics['color_class']

    alert_info = get_alert_message(risk_level, business_metrics, exclusion_details)
    warning_flags = calculate_auto_flags(result)

    # Get company details
    company_country = "Location Unknown"
    if exclusion_details:
        df_details = pd.DataFrame(exclusion_details)
        if 'company_country' in df_details.columns:
            countries = df_details['company_country'].dropna().unique()
            if len(countries) > 0:
                company_country = countries[0]

    # Header with ENHANCED metrics
    st.markdown(f"""
    <div class="company-header">
        <div class="company-title">🏢 {matched_name}</div>
        <div class="company-subtitle">📍 {company_country}</div>
        <div class="risk-metrics-row">
            <div class="risk-badge {color_class}">{risk_level}</div>
            <div class="quick-metric"><strong>Risk Score:</strong> {business_metrics['enhanced_score']}/100</div>
            <div class="quick-metric"><strong>Consensus:</strong> {business_metrics['consensus_strength']}</div>
            <div class="quick-metric"><strong>Assessment:</strong> {business_metrics['score_explanation']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Warning flags
    if warning_flags:
        flags_html = ''.join(
            [f'<span class="flag {flag_class}">{flag_text}</span>' for flag_text, flag_class in warning_flags])
        st.markdown(f'<div class="flags-container">{flags_html}</div>', unsafe_allow_html=True)

    # Alert box with updated class mapping (removed critical)
    alert_class_mapping = {
        'high': 'alert-high',
        'medium': 'alert-medium',
        'low': 'alert-low',
    }
    alert_class = alert_class_mapping.get(alert_info['level'], 'alert-low')

    st.markdown(f"""
    <div class="alert-container">
        <div class="alert-box {alert_class}">
            <div class="alert-title">{alert_info['title']}</div>
            <div class="alert-text">{alert_info['message']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI metrics with robust date parsing (UPDATED to show full dates)
    if result['match']['found'] and exclusion_details:
        df_details = pd.DataFrame(exclusion_details)
        total_exclusions = len(df_details)
        unique_investors = factors.get('unique_investors', 0)
        unique_countries = factors.get('unique_countries', 0)

        # Use the UPDATED date parsing function to get full dates
        recent_activity, last_date = get_recent_activity_and_latest_date(df_details)

        # Scope analysis
        sector_exclusions = 0
        if 'sector_company' in df_details.columns:
            sector_exclusions = (df_details['sector_company'] == 'sector').sum()
    else:
        unique_investors = unique_countries = total_exclusions = recent_activity = sector_exclusions = 0
        last_date = "N/A"

    # Display KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Financial Institutions", unique_investors, help="Number of investors excluding this company")
    with col2:
        st.metric("Countries Represented", unique_countries, help="Geographic spread of concerns")
    with col3:
        st.metric("Recent Exclusions", recent_activity, help="Exclusions in last 2 years")
    with col4:
        st.metric("Latest Exclusion", last_date, help="Most recent exclusion date")  # Now shows full date

    # Enhanced Score Breakdown
    if st.checkbox("📊 Show Enhanced Scoring Breakdown", help="View detailed multi-factor scoring"):
        score_breakdown = business_metrics['score_breakdown']

        # Use Streamlit components instead of complex HTML
        st.markdown("### 🎯 Enhanced Multi-Factor Risk Scoring")

        # Score summary
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Final Score", f"{business_metrics['enhanced_score']}/100")
        with col2:
            st.metric("Risk Level", risk_level)

        st.markdown("---")

        # Score components in a clean format
        st.markdown("**Score Components:**")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**🤝 Consensus Strength (40%):** {score_breakdown['consensus_score']:.0f}/100")
            st.caption(f"→ {score_breakdown['consensus_desc']}")

            st.write(f"**⚡ Recent Activity (20%):** {score_breakdown['recency_score']:.0f}/100")
            st.caption(f"→ {score_breakdown['recency_desc']}")

        with col2:
            st.write(f"**⚠️ Issue Severity (30%):** {score_breakdown['severity_score']:.0f}/100")
            st.caption(f"→ {score_breakdown['severity_desc']}")

            st.write(f"**🎯 Scope Impact (10%):** {score_breakdown['scope_score']:.0f}/100")
            st.caption(f"→ {score_breakdown['scope_desc']}")

        st.markdown("---")

    # Recommendations (UPDATED to align with fet_recommendations.py)
    recommendations = result['recommendations']

    # Use the risk level directly (no more Critical Risk override)
    current_recs = recommendations.get(risk_level, recommendations.get("Low Risk", {})).copy()

    with st.container():
        st.subheader("💼 Operational Playbook")

        # Get detailed playbook if available
        if hasattr(st.session_state.checker.recommendation_engine, 'get_detailed_playbook'):
            playbook = st.session_state.checker.recommendation_engine.get_detailed_playbook(risk_level)

            # Business context
            business_context = playbook.get('business_context', '')
            if business_context:
                if risk_level == "High Risk":
                    st.warning(f"**Business Context:** {business_context}")
                elif risk_level == "Medium Risk":
                    st.info(f"**Business Context:** {business_context}")

            # Main action columns
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**👥 Project Team Actions**")
                actions = playbook.get('project_team_actions', [
                    current_recs.get('project_team_action', 'Standard engagement procedures apply.')])
                if isinstance(actions, list):
                    for action in actions:
                        st.write(f"• {action}")
                else:
                    st.write(actions)

            with col2:
                st.markdown("**⚖️ Compliance Requirements**")
                compliance = playbook.get('compliance_sustainability_role', [
                    current_recs.get('compliance_role', 'Standard compliance processes apply.')])
                if isinstance(compliance, list):
                    for req in compliance:
                        st.write(f"• {req}")
                else:
                    st.write(compliance)

            # Additional sections for Medium/High Risk
            if risk_level in ["Medium Risk", "High Risk"]:

                # Scope guidance for higher risk levels
                if risk_level == "High Risk":
                    st.markdown("---")
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**✅ Acceptable Scopes**")
                        acceptable = playbook.get('acceptable_scopes', [])
                        if acceptable:
                            for scope in acceptable:
                                st.success(f"• {scope}")
                        else:
                            st.success("• Safety-critical work\n• Environmental remediation\n• Decommissioning")

                    with col2:
                        st.markdown("**🚫 Restricted Scopes**")
                        restricted = playbook.get('restricted_scopes', [])
                        if restricted:
                            for scope in restricted:
                                st.error(f"• {scope}")
                        else:
                            st.error("• Activities enabling flagged concerns")

                # Contract requirements
                st.markdown("---")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**📋 Contract Requirements**")
                    contract_reqs = playbook.get('contract_scope_requirements', [])
                    if contract_reqs:
                        for req in contract_reqs:
                            st.write(f"• {req}")
                    else:
                        st.write("• Standard contractual clauses apply")

                with col2:
                    st.markdown("**📊 Monitoring Approach**")
                    monitoring = playbook.get('monitoring_approach', [])
                    if monitoring:
                        for approach in monitoring:
                            st.write(f"• {approach}")
                    else:
                        st.write("• Standard monitoring procedures apply")

        else:
            # Fallback to simple display
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**👥 Project Team Actions**")
                st.write(current_recs.get('project_team_action', 'Standard engagement procedures apply.'))

            with col2:
                st.markdown("**⚖️ Compliance Requirements**")
                st.write(current_recs.get('compliance_role', 'Standard compliance processes apply.'))

    # UPDATED Table display - Show ALL records, not just 15
    if result['match']['found'] and exclusion_details:
        st.subheader("📋 Detailed Exclusions")

        df_display = pd.DataFrame(exclusion_details)

        # Simple filters
        col1, col2, col3 = st.columns(3)

        with col1:
            if 'sub_category' in df_display.columns:
                sub_categories = ['All'] + sorted(df_display['sub_category'].dropna().unique().tolist())
                filter_column = 'sub_category'
            else:
                sub_categories = ['All']
                filter_column = None

            selected_subcategory = st.selectbox('ESG Category:', sub_categories, key='subcat_filter')

        with col2:
            countries_list = ['All'] + sorted(df_display[
                                                  'investor_country'].dropna().unique().tolist()) if 'investor_country' in df_display.columns else [
                'All']
            selected_country = st.selectbox('Investor Country:', countries_list, key='country_filter')

        with col3:
            years = ['All'] + sorted(df_display['year'].dropna().astype(str).unique().tolist(),
                                     reverse=True) if 'year' in df_display.columns else ['All']
            selected_year = st.selectbox('Year:', years, key='year_filter')

        # Apply filters
        filtered_df = df_display.copy()

        if selected_subcategory != 'All' and filter_column and filter_column in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[filter_column] == selected_subcategory]

        if selected_country != 'All' and 'investor_country' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['investor_country'] == selected_country]

        if selected_year != 'All' and 'year' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['year'].astype(str) == selected_year]

        # UPDATED: Display ALL filtered records (no .head(15) limit)
        if not filtered_df.empty:
            display_df = filtered_df  # Show ALL records, not just first 15

            # Configure columns based on user requirements
            display_columns = []
            column_config = {}

            # 1. Investor Name (excluded_by)
            if 'excluded_by' in display_df.columns:
                display_columns.append('excluded_by')
                column_config['excluded_by'] = st.column_config.TextColumn(
                    "Financial Institution",
                    width="large",
                    help="Name of the financial institution that excluded this company"
                )

            # 2. Investor Parent Country (investor_country)
            if 'investor_country' in display_df.columns:
                display_columns.append('investor_country')
                column_config['investor_country'] = st.column_config.TextColumn(
                    "Investor Country",
                    width="medium",
                    help="Country where the investor is headquartered"
                )

            # 3. ESG Category (sub_category with more informative title)
            if 'sub_category' in display_df.columns:
                display_columns.append('sub_category')
                column_config['sub_category'] = st.column_config.TextColumn(
                    "ESG Category",
                    width="medium",
                    help="Primary area of ESG concern (e.g., Coal, Human Rights, Weapons)"
                )

            # 4. Specific Issue (further_sub_category with more informative title)
            if 'further_sub_category' in display_df.columns:
                display_columns.append('further_sub_category')
                column_config['further_sub_category'] = st.column_config.TextColumn(
                    "Specific Issue",
                    width="medium",
                    help="Detailed description of the specific ESG concern (e.g., Thermal Coal, Child Labour)"
                )

            # 5. Date of FI Exclusion (UPDATED with full date display)
            if 'exclusion_date_display' in display_df.columns:
                display_columns.append('exclusion_date_display')
                column_config['exclusion_date_display'] = st.column_config.TextColumn(
                    "Exclusion Date",
                    width="medium",
                    help="Date when the exclusion was implemented (YYYY-MM-DD format)"
                )
            elif 'exclusion_date' in display_df.columns:
                # Fallback: format on the fly using the enhanced function
                display_df = display_df.copy()
                display_df['exclusion_date_formatted'] = display_df['exclusion_date'].apply(
                    format_date_for_display
                )
                display_columns.append('exclusion_date_formatted')
                column_config['exclusion_date_formatted'] = st.column_config.TextColumn(
                    "Exclusion Date",
                    width="medium",
                    help="Date when the exclusion was implemented (YYYY-MM-DD format)"
                )

            # 6. Source
            if 'source' in display_df.columns:
                display_columns.append('source')
                column_config['source'] = st.column_config.TextColumn(
                    "Source",
                    width="medium",
                    help="Source of the exclusion information"
                )

            # 7. Website
            if 'website' in display_df.columns:
                display_columns.append('website')
                column_config['website'] = st.column_config.LinkColumn(
                    "Website",
                    width="medium",
                    help="Link to the source website",
                    display_text="🔗 Link"
                )

            # Display the table with ALL records
            if display_columns:
                st.dataframe(
                    display_df[display_columns],
                    width='stretch',
                    height=600,  # Increased height to accommodate more records
                    hide_index=True,
                    column_config=column_config
                )

                # Show record count info
                total_after_filter = len(filtered_df)
                total_original = len(df_display)

                st.info(f"📊 Showing all {total_after_filter:,} filtered records (of {total_original:,} total)")

                # Translation status indicator
                translation_columns = [col for col in ['motivation_en', 'main_category_en'] if
                                       col in display_df.columns]
                if translation_columns:
                    st.success(
                        f"🌍 Foreign language content translated to English in: {', '.join([col.replace('_en', '').replace('_', ' ').title() for col in translation_columns])}")
                else:
                    if 'motivation' in display_df.columns:
                        st.info("📖 Text content displayed in original language (translation available if needed)")

            else:
                st.error("❌ No display columns available - please check data structure")

                # Debug info
                with st.expander("🔧 Debug: Available Columns"):
                    st.write("Available columns in data:")
                    st.write(list(display_df.columns))

        else:
            st.info("ℹ️ No records match the selected filters")

            # Show what filters were applied
            active_filters = []
            if selected_subcategory != 'All':
                active_filters.append(f"ESG Category: {selected_subcategory}")
            if selected_country != 'All':
                active_filters.append(f"Country: {selected_country}")
            if selected_year != 'All':
                active_filters.append(f"Year: {selected_year}")

            if active_filters:
                st.write(f"**Active filters:** {' | '.join(active_filters)}")

    # UPDATED Export options with PDF report
    if result['match']['found'] and exclusion_details:
        col1, col2 = st.columns(2)

        with col1:
            export_df = pd.DataFrame(exclusion_details)
            csv_data = export_df.to_csv(index=False)
            st.download_button(
                "📊 Export CSV",
                csv_data,
                f"{matched_name.replace(' ', '_')}_exclusions.csv",
                "text/csv"
            )

        with col2:
            # UPDATED: Generate PDF report instead of JSON
            try:
                pdf_data = generate_pdf_report(result)
                st.download_button(
                    "📋 Full PDF Report",
                    pdf_data,
                    f"{matched_name.replace(' ', '_')}_risk_report.pdf",
                    "application/pdf"
                )
            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")
                # Fallback to JSON if PDF generation fails
                enhanced_result = result.copy()
                enhanced_result['enhanced_scoring'] = business_metrics
                json_data = json.dumps(enhanced_result, indent=2, default=str)
                st.download_button(
                    "📋 Full Report (JSON)",
                    json_data,
                    f"{matched_name.replace(' ', '_')}_enhanced_report.json",
                    "application/json"
                )

def main():
    """Restored main function using the original approach that worked better for search"""

    # Initialize all session state keys upfront (like the original)
    session_keys = {
        'checker': None,
        'analysis_result': None,
        'database_loaded': False,
        'loading_attempted': False,
        'upload_processed': False
    }

    for key, default_value in session_keys.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

    # Only attempt loading once per session (like the original)
    if not st.session_state.database_loaded and not st.session_state.loading_attempted:
        st.session_state.loading_attempted = True

        with st.spinner("🔥 Initializing Global Investor ESG Exclusions database..."):
            checker = load_fet_checker()

        if checker:
            st.session_state.checker = checker
            st.session_state.database_loaded = True
        else:
            st.session_state.loading_attempted = False

    # Handle file upload separately and only if no database loaded (like the original)
    if not st.session_state.database_loaded:
        st.error("📂 Database not found. Please upload the Excel file.")

        uploaded_file = st.file_uploader(
            "Upload Excel Dataset (.xlsx)",
            type=["xlsx"],
            help="Upload the ESG exclusion database Excel file",
            key="main_file_uploader"
        )

        if uploaded_file and not st.session_state.upload_processed:
            st.session_state.upload_processed = True

            with st.spinner("🔥 Processing uploaded database..."):
                file_data = uploaded_file.read()
                checker = load_fet_checker(file_data)

            if checker:
                st.session_state.checker = checker
                st.session_state.database_loaded = True
                st.success("🎉 Database loaded successfully!")
                st.rerun()
            else:
                st.session_state.upload_processed = False
                st.error("❌ Failed to process uploaded file")
                return

        elif not uploaded_file:
            st.info("👆 Please upload the database Excel file to continue")
            return

    # Safety check with better error handling (like the original)
    if not st.session_state.database_loaded or st.session_state.checker is None:
        st.error("❌ Database not ready. Please refresh the page.")
        return

    # Only show loading message once (like the original)
    if st.session_state.database_loaded and 'load_success_shown' not in st.session_state:
        st.session_state.load_success_shown = True

    # Welcome header based on state (like the original)
    if st.session_state.analysis_result is None:
        # Full welcome header for first-time users
        st.markdown("""
            <div class="welcome-header">
                <h1 class="welcome-title">🛡️ Risk Intelligence Dashboard</h1>
                <p class="welcome-subtitle">Enhanced Multi-Factor Investor Exclusion Analysis</p>
                <div class="context-box">
                    <strong>Enhanced Scoring:</strong> Our multi-factor model considers consensus strength (40%), 
                    issue severity (30%), recent activity (20%), and scope impact (10%) to provide nuanced 
                    and explainable risk assessments.<br><br>
                    <strong>Business Value:</strong> Clear, defensible risk levels that map directly to operational 
                    procedures - from standard engagement to executive-level approvals with enhanced due diligence.
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Compact header when showing results
        st.markdown("""
            <div class="welcome-header" style="padding: 1rem 0; margin-bottom: 1rem;">
                <h2 class="welcome-title" style="font-size: 1.5rem; margin-bottom: 0.2rem;">🛡️ Risk Intelligence Dashboard</h2>
                <p class="welcome-subtitle" style="font-size: 0.9rem; margin-bottom: 0;">Enhanced Multi-Factor Institutional Investor Exclusion Analysis</p>
            </div>
            """, unsafe_allow_html=True)

    # Enhanced search section
    def enhanced_search_section():
        """Enhanced search section for the dashboard"""

        # Search section header
        if st.session_state.analysis_result is None:
            st.subheader("🔍 Company Risk Assessment")
        else:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.subheader("🔍 Search Another Company")
            with col2:
                if st.button("🔄 New Search", key="new_search"):
                    st.session_state.analysis_result = None
                    st.rerun()

        # Enhanced search input with improved placeholder
        search_query = st.text_input(
            "Company Search",
            placeholder="Enter company name (supports partial matches: e.g., 'Shell', 'Royal Dutch', 'Tesla Inc')...",
            key="search_input",
            label_visibility="collapsed",
            help="Search supports exact matches, partial words, and fuzzy matching"
        )

        selected_company = None

        # Enhanced search logic
        if search_query.strip() and len(search_query.strip()) >= 2:
            with st.spinner("🔍 Searching companies..."):
                suggestions = get_enhanced_company_suggestions(
                    st.session_state.checker,
                    search_query,
                    max_results=9
                )

            if suggestions:
                st.markdown("**📋 Select from matches:**")

                # Display suggestions with enhanced information
                for i in range(0, len(suggestions), 3):
                    cols = st.columns(3)
                    for j in range(3):
                        if i + j < len(suggestions):
                            company_name, match_info, match_type = suggestions[i + j]

                            # Color coding based on match type
                            if match_type == "word_match":
                                button_help = f"🎯 Word match: {match_info}"
                            elif match_type == "fuzzy_match":
                                button_help = f"🔍 Fuzzy match: {match_info}"
                            else:
                                button_help = f"🔍 Partial match: {match_info}"

                            with cols[j]:
                                if st.button(
                                        company_name,
                                        key=f"enhanced_suggestion_{i}_{j}",
                                        use_container_width=True,
                                        help=button_help
                                ):
                                    selected_company = company_name
                                    break

                # Show search tips if few results
                if len(suggestions) < 1:
                    st.info(
                        "💡 **Tip**: Try shorter search terms or partial company names (e.g., 'Shell' instead of 'Royal Dutch Shell plc')")

            else:
                st.warning("❌ No companies found. Try:")
                st.markdown("""
                - Shorter search terms (e.g., 'Shell' instead of full name)
                - Different spellings or common abbreviations  
                - Removing legal suffixes (Inc, Corp, Ltd, etc.)
                - Single words from the company name
                """)

                # Debugging help
                with st.expander("🔧 Search Debug Info"):
                    if hasattr(st.session_state.checker, 'debug_company_search_streamlit'):
                        st.session_state.checker.debug_company_search_streamlit(search_query)
                    elif hasattr(st.session_state.checker, 'debug_company_search'):
                        st.warning("Debug output may not display properly. Please update fet_core.py")
                        st.session_state.checker.debug_company_search(search_query)
                    else:
                        st.error("Debug functionality not available")

        return selected_company

    # Get selected company from search
    selected_company = enhanced_search_section()

    # Perform analysis
    if selected_company:
        with st.spinner(f"🔍 Analyzing {selected_company} with enhanced scoring..."):
            result = st.session_state.checker.analyze_company(selected_company)
            st.session_state.analysis_result = result
            st.rerun()

    # Display results
    if st.session_state.analysis_result:
        display_comprehensive_dashboard(st.session_state.analysis_result)


if __name__ == "__main__":
    main()