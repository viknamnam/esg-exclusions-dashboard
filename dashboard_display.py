"""
Updated dashboard display components with World Bank integration
"""
import streamlit as st
import pandas as pd
import re, json
from datetime import datetime

from risk_scoring import (
    translate_risk_to_business_language,
    get_alert_message
)
from data_utils import get_recent_activity_and_latest_date, format_date_for_display
from report_generation import generate_pdf_report, create_export_data


def _slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(name)).strip("_")


def render_company_header(result, business_metrics):
    """Render the company header with top-right export buttons and database indicators."""
    query_name = result['query']['company_name']
    matched_name = result['match']['matched_company'] if result['match']['found'] else query_name
    exclusion_details = result.get('exclusion_details', []) or []
    wb_details = result.get('wb_details', []) or []

    # NEW: Show which databases found the company
    fet_found = result['match'].get('fet_found', False)
    wb_found = result['match'].get('wb_found', False)

    # Resolve country
    company_country = "Location Unknown"
    if exclusion_details:
        df_details = pd.DataFrame(exclusion_details)
        if 'company_country' in df_details.columns:
            countries = df_details['company_country'].dropna().unique()
            if len(countries) > 0:
                company_country = countries[0]

    risk_level = business_metrics['risk_level']
    color_class = business_metrics['color_class']

    # ---- Layout: header (left) + actions (right)
    left, right = st.columns([0.78, 0.22], gap="small")

    # LEFT: company header card with database indicators
    with left:
        # NEW: Database indicators
        db_indicators = []
        if fet_found:
            db_indicators.append("📊 FET Database")
        if wb_found:
            db_indicators.append("🏛️ World Bank")

        db_indicator_text = " | ".join(db_indicators) if db_indicators else "No exclusions found"

        st.markdown(f"""
        <div class="company-header">
            <div class="company-title">🏢 {matched_name}</div>
            <div class="company-subtitle">📍 {company_country} | Found in: {db_indicator_text}</div>
            <div class="risk-metrics-row">
                <div class="risk-badge {color_class}">{risk_level}</div>
                <div class="quick-metric"><strong>Risk Score:</strong> {business_metrics['enhanced_score']}/100</div>
                <div class="quick-metric"><strong>Consensus:</strong> {business_metrics['consensus_strength']}</div>
                <div class="quick-metric"><strong>Assessment:</strong> {business_metrics['score_explanation']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # RIGHT: export buttons (top-right)
    with right:
        st.markdown(
            "<div style='display:flex; justify-content:flex-end; gap:8px; flex-wrap:wrap;'>",
            unsafe_allow_html=True
        )

        if (result['match']['found'] and (exclusion_details or wb_details)):
            safe = _slugify(matched_name)

            # CSV
            csv_data = create_export_data(result, matched_name)
            if csv_data:
                st.download_button(
                    "📊 Export CSV  ",
                    csv_data,
                    file_name=f"{safe}_exclusions.csv",
                    mime="text/csv",
                    key=f"csv_{safe}",
                    help="Download exclusions for this company"
                )

            # PDF (fallback to JSON if PDF fails)
            try:
                pdf_data = generate_pdf_report(result)
                st.download_button(
                    "📋 Full PDF Report",
                    pdf_data,
                    file_name=f"{safe}_risk_report.pdf",
                    mime="application/pdf",
                    key=f"pdf_{safe}",
                    help="Download full risk report (PDF)"
                )
            except Exception as e:
                # Optional: small JSON fallback button if PDF fails
                enhanced = result.copy()
                enhanced['enhanced_scoring'] = translate_risk_to_business_language(result)
                st.download_button(
                    "🧾 JSON",
                    json.dumps(enhanced, indent=2, default=str),
                    file_name=f"{safe}_enhanced_report.json",
                    mime="application/json",
                    key=f"json_{safe}",
                    help=f"PDF generator error: {e}"
                )
        else:
            st.caption("No export available for this company.")

        st.markdown("</div>", unsafe_allow_html=True)


def render_alert_box(alert_info):
    """Render the main alert box"""
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


def render_kpi_metrics(result, factors, exclusion_details, wb_details):
    """Render KPI metrics section with both databases."""
    # FET metrics
    if result['match'].get('fet_found', False) and exclusion_details:
        df_details = pd.DataFrame(exclusion_details)
        total_exclusions = len(df_details)
        unique_investors = factors.get('unique_investors', 0)
        unique_countries = factors.get('unique_countries', 0)

        # Use the date parsing function to get full dates
        recent_activity, last_date = get_recent_activity_and_latest_date(df_details)
    else:
        unique_investors = unique_countries = total_exclusions = recent_activity = 0
        last_date = "N/A"

    # NEW: World Bank metrics
    wb_sanctions_count = len(wb_details) if wb_details else 0

    # Display KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Financial Institutions",
            unique_investors,
            help="Number of investors excluding this company (FET Database)"
        )

    with col2:
        st.metric(
            "Countries Represented",
            unique_countries,
            help="Geographic spread of investor concerns (FET Database)"
        )

    with col3:
        st.metric(
            "Recent FET Exclusions",
            recent_activity,
            help="FET exclusions in last 2 years"
        )

    with col4:
        # NEW: Show World Bank sanctions if found
        if wb_sanctions_count > 0:
            st.metric(
                "World Bank Status",
                "SANCTIONED",
                help=f"Company is sanctioned by the World Bank ({wb_sanctions_count} record(s))"
            )
        else:
            st.metric(
                "Latest FET Exclusion",
                last_date,
                help="Most recent FET exclusion date"
            )


def render_score_breakdown(business_metrics):
    """Render enhanced scoring breakdown"""
    if st.checkbox("📊 Show Enhanced Scoring Breakdown", help="View detailed multi-factor scoring"):
        score_breakdown = business_metrics['score_breakdown']

        # Use Streamlit components instead of complex HTML
        st.markdown("### 🎯 Enhanced Multi-Factor Risk Scoring")

        # Score summary
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Final Score", f"{business_metrics['enhanced_score']}/100")
        with col2:
            st.metric("Risk Level", business_metrics['risk_level'])

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


def kcard(title, subtitle, items):
    """Create a custom card component for the operational playbook"""
    st.markdown(
        f"""
        <div style="
            border:1px solid #e7e7e7; border-radius:14px; padding:14px 16px; 
            background:white; box-shadow:0 1px 3px rgba(0,0,0,0.04);">
          <div style="font-size:16px;font-weight:700;margin-bottom:2px;">{title}</div>
          <div style="font-size:12px;color:#6b7280;margin-bottom:8px;">{subtitle}</div>
          <ul style="margin:0 0 0 18px;padding:0;">
            {''.join(f'<li style="margin:4px 0;">{i}</li>' for i in items)}
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_operational_playbook(result, business_metrics):
    """Render the operational playbook section with custom cards"""
    recommendations = result['recommendations']
    risk_level = business_metrics['risk_level']

    with st.container():
        st.subheader("💼 Operational Playbook")

        # NEW: Special considerations for World Bank sanctions
        wb_found = result['match'].get('wb_found', False)
        if wb_found:
            st.warning(
                "🏛️ **World Bank Sanctions Alert**: This company is sanctioned by the World Bank. Additional due diligence and compliance considerations may apply.")

        # Get detailed playbook if available
        checker = st.session_state.checker
        if hasattr(checker.recommendation_engine, 'get_detailed_playbook'):
            playbook = checker.recommendation_engine.get_detailed_playbook(risk_level)

            # Main action cards
            col1, col2 = st.columns(2, gap="medium")

            with col1:
                # Project Team Actions
                actions = playbook.get('project_team_actions', [
                    recommendations.get(risk_level, {}).get('project_team_action',
                                                            'Standard engagement procedures apply.')])
                if isinstance(actions, str):
                    actions = [actions]

                # NEW: Add World Bank consideration
                if wb_found:
                    actions.append("⚠️ Verify World Bank sanctions compliance requirements")

                kcard("👥 Project Team Actions", "", actions)

                # Compliance Requirements
                compliance = playbook.get('compliance_sustainability_role', [
                    recommendations.get(risk_level, {}).get('compliance_role', 'Standard compliance processes apply.')])
                if isinstance(compliance, str):
                    compliance = [compliance]

                # NEW: Add World Bank compliance
                if wb_found:
                    compliance.append("🏛️ World Bank sanctions compliance check required")

                kcard("⚖️ Compliance Requirements", "", compliance)

            with col2:
                # Risk-specific cards for Medium and High risk levels
                if risk_level in ["Medium Risk", "High Risk"]:
                    monitoring = playbook.get('monitoring_approach', [])
                    if monitoring:
                        # NEW: Add World Bank monitoring
                        if wb_found:
                            monitoring.append("Monitor World Bank sanctions status changes")
                        kcard("📊 Monitoring Approach", "How we keep it on track", monitoring)

                    # Contract Requirements
                    contract_reqs = playbook.get('contract_scope_requirements', [])
                    if contract_reqs:
                        # NEW: Add World Bank contractual considerations
                        if wb_found:
                            contract_reqs.append("Include World Bank sanctions compliance warranties")
                        kcard("📋 Contract Requirements", "", contract_reqs)

            # Additional monitoring section for all risk levels
            st.markdown("---")

            # Main action cards
            col1, col2 = st.columns(2, gap="medium")

            with col1:
                # Risk-specific cards for Medium and High risk levels
                if risk_level in ["Medium Risk", "High Risk"]:
                    # Acceptable Scopes
                    acceptable = playbook.get('acceptable_scopes', [])
                    if acceptable:
                        # Format as bullet points with separators
                        formatted_acceptable = [" • ".join(acceptable)]
                        kcard("✅ Acceptable Scopes", "", formatted_acceptable)

            with col2:
                # Risk-specific cards for Medium and High risk levels
                if risk_level in ["Medium Risk", "High Risk"]:

                    # Restricted Scopes
                    restricted = playbook.get('restricted_scopes', [])
                    if restricted:
                        # NEW: Add World Bank restriction
                        if wb_found:
                            restricted.append("Activities that could violate World Bank sanctions")
                        kcard("🚫 Restricted Scopes", "", restricted)

            # Commercial opportunities section (if available)
            commercial_opps = playbook.get('commercial_opportunities', [])
            if commercial_opps:
                st.markdown("---")
                kcard("💡 Commercial Opportunities", "Value-add services", commercial_opps)

        else:
            # Fallback to simple display if detailed playbook not available
            col1, col2 = st.columns(2, gap="medium")

            with col1:
                current_recs = recommendations.get(risk_level, recommendations.get("Low Risk", {}))

                action_text = current_recs.get('project_team_action', 'Standard engagement procedures apply.')
                if wb_found:
                    action_text += "\n⚠️ Verify World Bank sanctions compliance requirements"

                kcard("💼 Operational Playbook", "👥 Project Team Actions", [action_text])

            with col2:
                compliance_text = current_recs.get('compliance_role', 'Standard compliance processes apply.')
                if wb_found:
                    compliance_text += "\n🏛️ World Bank sanctions compliance check required"

                kcard("⚖️ Compliance Requirements", "Approvals & oversight", [compliance_text])

            # Monitoring for fallback
            st.markdown("---")
            monitoring_text = current_recs.get('monitoring', 'Standard monitoring procedures apply.')
            if wb_found:
                monitoring_text += "\nMonitor World Bank sanctions status changes"

            kcard("📊 Monitoring Approach", "Standard procedures", [monitoring_text])


def render_exclusion_details_table(result):
    """Render the detailed exclusions table with both databases."""
    exclusion_details = result['exclusion_details']
    wb_details = result.get('wb_details', [])

    # Show FET exclusions if available
    if result['match'].get('fet_found', False) and exclusion_details:
        st.markdown("---")
        st.subheader("📋 FET Database Exclusions")

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

        # Display ALL filtered records (no limit)
        if not filtered_df.empty:
            display_df = filtered_df

            # Configure columns
            display_columns = []
            column_config = {}

            # Standard columns to display
            column_mappings = [
                ('excluded_by', 'Financial Institution', 'large'),
                ('investor_country', 'Investor Country', 'medium'),
                ('sub_category', 'ESG Category', 'medium'),
                ('further_sub_category', 'Specific Issue', 'medium'),
                ('source', 'Source', 'medium')
            ]

            for col_name, display_name, width in column_mappings:
                if col_name in display_df.columns:
                    display_columns.append(col_name)
                    column_config[col_name] = st.column_config.TextColumn(
                        display_name,
                        width=width,
                        help=f"{display_name} information"
                    )

            # Handle dates specially
            if 'exclusion_date_display' in display_df.columns:
                display_columns.append('exclusion_date_display')
                column_config['exclusion_date_display'] = st.column_config.TextColumn(
                    "Exclusion Date",
                    width="medium",
                    help="Date when the exclusion was implemented (YYYY-MM-DD format)"
                )
            elif 'exclusion_date' in display_df.columns:
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

            # Website link
            if 'website' in display_df.columns:
                display_columns.append('website')
                column_config['website'] = st.column_config.LinkColumn(
                    "Website",
                    width="medium",
                    help="Link to the source website",
                    display_text="🔗 Link"
                )

            # Display the table
            if display_columns:
                st.dataframe(
                    display_df[display_columns],
                    width='stretch',
                    height=400,  # Reduced height if we have WB data too
                    hide_index=True,
                    column_config=column_config
                )



            else:
                st.error("❌ No display columns available - please check data structure")

        else:
            st.info("ℹ️ No FET records match the selected filters")

    # NEW: Show World Bank sanctions if available
    if result['match'].get('wb_found', False) and wb_details:
        st.markdown("---")
        st.subheader("🏛️ World Bank Sanctions")

        # Create a simple display for World Bank data
        wb_df = pd.DataFrame(wb_details)

        if not wb_df.empty:
            # Configure World Bank display
            wb_display_columns = []
            wb_column_config = {}

            if 'sanctioned_entity' in wb_df.columns:
                wb_display_columns.append('sanctioned_entity')
                wb_column_config['sanctioned_entity'] = st.column_config.TextColumn(
                    "Sanctioned Entity",
                    width="large",
                    help="Name of the sanctioned entity in World Bank database"
                )

            if 'sanction_type' in wb_df.columns:
                wb_display_columns.append('sanction_type')
                wb_column_config['sanction_type'] = st.column_config.TextColumn(
                    "Sanction Type",
                    width="medium",
                    help="Type of World Bank sanction"
                )

            if 'match_confidence' in wb_df.columns:
                wb_display_columns.append('match_confidence')
                wb_column_config['match_confidence'] = st.column_config.NumberColumn(
                    "Match Confidence",
                    width="small",
                    help="Confidence level of the match (%)",
                    format="%d%%"
                )

            if wb_display_columns:
                st.dataframe(
                    wb_df[wb_display_columns],
                    width='stretch',
                    height=200,
                    hide_index=True,
                    column_config=wb_column_config
                )

                st.info(f"🏛️ {len(wb_df)} World Bank sanction record(s)")
            else:
                st.error("❌ World Bank data structure issue")
        else:
            st.info("ℹ️ World Bank sanctions found but no details available")


def render_export_options(result):
    """Render export options"""
    matched_name = result['match']['matched_company'] if result['match']['found'] else result['query']['company_name']
    exclusion_details = result['exclusion_details']
    wb_details = result.get('wb_details', [])

    if not result['match']['found'] or (not exclusion_details and not wb_details):
        return

    col1, col2 = st.columns(2)

    with col1:
        csv_data = create_export_data(result, matched_name)
        if csv_data:
            st.download_button(
                "📊 Export CSV",
                csv_data,
                f"{matched_name.replace(' ', '_')}_exclusions.csv",
                "text/csv"
            )

    with col2:
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
            enhanced_result['enhanced_scoring'] = translate_risk_to_business_language(result)
            json_data = json.dumps(enhanced_result, indent=2, default=str)
            st.download_button(
                "📋 Full Report (JSON)",
                json_data,
                f"{matched_name.replace(' ', '_')}_enhanced_report.json",
                "application/json"
            )


def display_comprehensive_dashboard(result):
    """Main dashboard display function with dual database support."""
    # Calculate business metrics
    business_metrics = translate_risk_to_business_language(result)
    risk_level = business_metrics['risk_level']
    exclusion_details = result['exclusion_details']
    wb_details = result.get('wb_details', [])
    factors = result['risk_assessment']['factors']

    # Get alert information
    alert_info = get_alert_message(risk_level, business_metrics, exclusion_details, wb_details)

    # Render main components
    render_company_header(result, business_metrics)
    render_alert_box(alert_info)
    render_kpi_metrics(result, factors, exclusion_details, wb_details)
    render_score_breakdown(business_metrics)
    render_operational_playbook(result, business_metrics)
    render_exclusion_details_table(result)