"""
Risk scoring and assessment logic for the FET dashboard
CONSOLIDATED VERSION - Uses existing fet_utils functions to avoid duplication
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Import existing foundation functions to avoid duplication
from fet_utils import FETDataUtils


def calculate_business_risk_score(result):
    """Enhanced scoring that builds on existing fet_core risk calculations to avoid duplication"""

    factors = result['risk_assessment']['factors']
    exclusion_details = result['exclusion_details']

    # Handle case with no exclusions early
    if not exclusion_details or len(exclusion_details) == 0:
        return _get_no_exclusion_score_data()

    df_details = pd.DataFrame(exclusion_details)
    total_exclusions = len(exclusion_details)

    if total_exclusions == 0:  # Double-check
        return _get_no_exclusion_score_data()

    # Use existing consensus calculation from fet_core (already calculated in factors)
    consensus_score = _calculate_consensus_component(factors)

    # Dashboard-specific enhancements
    severity_score, severity_desc = _analyze_issue_severity(exclusion_details)
    recency_score, recency_desc = _analyze_recency_patterns(exclusion_details, factors)
    scope_score, scope_desc = _analyze_scope_impact(exclusion_details)

    # Calculate weighted final score
    final_score = (
            consensus_score['score'] * 0.40 +
            severity_score * 0.30 +
            recency_score * 0.20 +
            scope_score * 0.10
    )

    # Create breakdown explanation
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)
    breakdown = f"""
    Consensus (40%): {consensus_score['score']:.0f}/100 - {consensus_score['desc']}
    • {investors} investors, {countries} countries
    Severity (30%): {severity_score:.0f}/100 - {severity_desc}
    Recency (20%): {recency_score:.0f}/100 - {recency_desc}
    Scope (10%): {scope_score:.0f}/100 - {scope_desc}
    """

    return {
        'final_score': final_score,
        'consensus_score': consensus_score['score'],
        'consensus_desc': consensus_score['desc'],
        'severity_score': severity_score,
        'severity_desc': severity_desc,
        'recency_score': recency_score,
        'recency_desc': recency_desc,
        'scope_score': scope_score,
        'scope_desc': scope_desc,
        'breakdown': breakdown.strip()
    }


def _get_no_exclusion_score_data():
    """Return consistent no-exclusion score data"""
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


def _calculate_consensus_component(factors):
    """Calculate consensus component using existing fet_core calculations"""
    # Use existing calculations from fet_core to avoid duplication
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)

    # Use the existing consensus_adjusted_score calculation as a guide
    # but map it to our 100-point scale for the dashboard
    base_score = factors.get('consensus_adjusted_score', 0)

    # Map the consensus strength to our dashboard scale
    if investors >= 20 or countries >= 6:
        score = 90
        desc = "Very Strong Multi-Country Consensus"
    elif investors >= 10 and countries >= 4:
        score = 70
        desc = "Strong Multi-Country Consensus"
    elif investors >= 5 and countries >= 3:
        score = 50
        desc = "Moderate Multi-Country Consensus"
    elif investors >= 3 and countries >= 2:
        score = 30
        desc = "Limited Multi-Country Consensus"
    elif investors >= 2 or countries >= 2:
        score = 15  # Reduced from 40 to 15
        desc = "Minimal Multi-Authority Consensus"
    else:
        # Single investor, single country = very low score
        score = 5  # Reduced from 25 to 5
        desc = "Single Authority Concern"

    return {'score': score, 'desc': desc}


def _analyze_issue_severity(exclusion_details):
    """Analyze severity of issues (dashboard-specific enhancement)"""
    if not exclusion_details:
        return 0, "No Issues Identified"

    df_details = pd.DataFrame(exclusion_details)
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

    # Issue severity assessment using existing category logic
    if any(term in combined_text for term in
           ['forced labour', 'child labour', 'forced labor', 'child labor', 'slavery']):
        severity_score = 95
        severity_desc = "Critical Human Rights Violations"
    elif any(term in combined_text for term in ['corruption', 'bribery', 'fraud', 'money laundering']):
        severity_score = 85
        severity_desc = "Serious Governance Issues"
    elif any(term in combined_text for term in ['thermal coal', 'fossil expansion', 'coal mining', 'coal power']):
        # Check scope using existing scope_normalized field
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

    return severity_score, severity_desc


def _analyze_recency_patterns(exclusion_details, factors):
    """Analyze recency patterns (dashboard-specific enhancement)"""
    if not exclusion_details:
        return 0, "No Recent Activity"

    total_exclusions = len(exclusion_details)
    recent_exclusions = factors.get('recent_exclusions', 0)

    # Safe division to avoid division by zero
    if total_exclusions > 0:
        recency_ratio = recent_exclusions / total_exclusions
    else:
        recency_ratio = 0

    if recency_ratio >= 0.8:
        return 100, "Very Recent Activity"
    elif recency_ratio >= 0.5:
        return 80, "Recent Activity"
    elif recency_ratio >= 0.3:
        return 60, "Mixed Timeline"
    elif recency_ratio >= 0.1:
        return 40, "Some Recent Activity"
    else:
        return 20, "Historical Issues Only"


def _analyze_scope_impact(exclusion_details):
    """Analyze scope impact (using existing scope_normalized field)"""
    if not exclusion_details:
        return 0, "No Exclusions"

    df_details = pd.DataFrame(exclusion_details)
    scope_score = 70  # Default company-level
    scope_desc = "Company-Level"

    if 'scope_normalized' in df_details.columns:
        if (df_details['scope_normalized'] == 'sector').any():
            scope_score = 100
            scope_desc = "Sector-Wide Impact"

    return scope_score, scope_desc


def determine_risk_level_and_explanation(score_data, factors):
    """Determine risk level using existing thresholds"""
    score = score_data['final_score']
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)

    # Use the same logic as in fet_recommendations.py
    if score >= 80:  # High Risk threshold
        level = "High Risk"
        explanation = f"Strong consensus ({investors} investors, {countries} countries) on significant concerns"
        color_class = "high-risk"
    elif score >= 50:  # Medium Risk threshold
        level = "Medium Risk"
        explanation = f"Moderate consensus ({investors} investors, {countries} countries) requiring targeted mitigation."
        color_class = "medium-risk"
    else:
        level = "Low Risk"
        explanation = f"Limited consensus ({investors} investors) with manageable concerns" if investors > 0 else "No significant exclusions identified in our database"
        color_class = "low-risk"

    return level, explanation, color_class


def translate_risk_to_business_language(result):
    """Translate risk to business language using consolidated scoring"""
    factors = result['risk_assessment']['factors']

    # Calculate the enhanced multi-factor score (using existing data where possible)
    score_data = calculate_business_risk_score(result)

    # Determine risk level and explanation
    risk_level, explanation, color_class = determine_risk_level_and_explanation(score_data, factors)

    # Build consensus description using existing data
    investors = factors.get('unique_investors', 0)
    countries = factors.get('unique_countries', 0)
    consensus_strength = f"{investors} investors across {countries} countries"

    # Confidence assessment (reuse existing calculation)
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

        # Keep original metrics for comparison (already calculated in fet_core)
        'raw_score': factors.get('consensus_adjusted_score', 0),
        'percentile': factors.get('percentile', 0)
    }


def get_alert_message(risk_level, business_metrics, exclusion_details, wb_details=None):
    """Generate alert messages using EXACT titles and content from fet_recommendations.py with World Bank considerations"""
    consensus = business_metrics['consensus_strength']
    wb_found = wb_details and len(wb_details) > 0

    if risk_level == "High Risk":
        base_message = f"Significant ESG concerns identified with {consensus}. Engagement may proceed for strategic clients with executive approval and tightly defined, harm-reducing scopes. Default is to avoid scopes that could enable the flagged activities. Acceptable scopes focus on safety-critical, environmental remediation, decommissioning, just transition, compliance uplift, and renewable transition. For strategic or public-interest cases, route to Executive Review with a concise business case detailing benefits and protections. Executive approval with documented rationale required."

        if wb_found:
            base_message += " 🏛️ WORLD BANK SANCTIONS DETECTED - Additional compliance and legal review needed."

        return {
            'level': 'high',
            'title': '🔴 Strategic engagement with executive oversight',
            'message': base_message
        }
    elif risk_level == "Medium Risk":
        base_message = f"Moderate ESG concerns identified with {consensus}. Engagement is viable with targeted mitigations. Define guardrails to ensure work does not enable flagged activities. Add a Risk & Mitigation section to the proposal with clear owners and dates. Hold a short pre-engagement briefing with Compliance/Sustainability to align on scope and mitigations. Unit-level pre-approval with logged conditions."

        if wb_found:
            base_message += " 🏛️ World Bank sanctions require additional compliance verification."

        return {
            'level': 'medium',
            'title': '🟡 Controlled engagement with enhanced oversight',  # Actual title from fet_recommendations.py
            'message': base_message
        }
    else:
        base_message = f"No significant ESG concerns identified with {consensus if consensus != '0 investors across 0 countries' else 'no exclusions found'}. Proceed with standard onboarding and project risk assessment. Document 'no exclusions detected / below threshold' and date-stamp sources. No pre-approval needed."

        if wb_found:
            # Even for low risk, World Bank sanctions are serious
            return {
                'level': 'medium',  # Upgrade to medium due to WB sanctions
                'title': '🏛️ World Bank Sanctions - Enhanced Controls Required',
                'message': f"This company is sanctioned by the World Bank. Enhanced due diligence and compliance verification required. {base_message.replace('No pre-approval needed.', 'Unit-level pre-approval required due to World Bank sanctions.')}"
            }

        return {
            'level': 'low',
            'title': '🟢 Proceed per standard controls',  # Actual title from fet_recommendations.py
            'message': base_message
        }


