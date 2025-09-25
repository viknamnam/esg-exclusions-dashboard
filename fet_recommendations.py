from typing import Dict, List


class RecommendationEngine:
    """
    DNV-specific recommendation engine for FET exclusion analysis.
    Provides categorization and actionable recommendations based on operational playbook.
    """

    # Category mapping for recommendations (updated for DNV context)
    CATEGORY_MAPPING = {
        'Human Rights': [
            'human rights', 'child labor', 'child labour', 'forced labor', 'forced labour',
            'labor rights', 'labour rights', 'workplace rights', 'social issues',
            'indigenous rights', 'community rights', 'worker rights', 'freedom of association'
        ],
        'Climate': [
            'climate', 'fossil', 'coal', 'oil', 'gas', 'carbon', 'emission',
            'environmental', 'deforestation', 'palm oil', 'renewable',
            'sustainability', 'green', 'energy transition', 'fossil expansion',
            'thermal coal', 'paris alignment', 'decarbonisation'
        ],
        'Country Policy': [
            'sanctions', 'embargoed', 'restricted', 'blacklist', 'watchlist',
            'country risk', 'geopolitical', 'trade restrictions', 'export controls'
        ],
        'Governance': [
            'corruption', 'bribery', 'fraud', 'governance', 'compliance',
            'money laundering', 'tax evasion', 'regulatory', 'ethics',
            'integrity', 'transparency', 'anti-corruption', 'norms-based'
        ]
    }

    # DNV Operational Playbook Recommendations (Updated)
    RECOMMENDATIONS = {
        'Low Risk': {
            'business_context': 'No significant ESG concerns identified. Proceed with standard controls.',
            'project_team_action': 'Proceed with standard onboarding and project risk assessment. Document "no exclusions detected / below threshold" and date-stamp sources.',
            'compliance_role': 'No pre-approval needed; random spot checks (e.g., quarterly sample). Keep evidence pack (sources, parsed year) in the central register.',
            'contract_scope': 'Standard clauses (Code of Conduct, anti-corruption, HSE, data privacy).',
            'monitoring': 'Passive monitoring. Re-screen before major new proposals or annually.',
            'color': '🟢'
        },
        'Medium Risk': {
            'business_context': 'Moderate ESG concerns identified. Engagement is viable with targeted mitigations and scope guardrails that support business continuity.',
            'project_team_action': 'Define guardrails to ensure work does not enable flagged activities. Consider adding a Risk & Mitigation section to the proposal with clear owners and dates. Hold a short pre-engagement briefing with Compliance/Sustainability to align on scope and mitigations.',
            'acceptable_scopes': 'Standard operations, safety improvements, compliance uplift, environmental remediation, transition planning.',
            'restricted_scopes': 'Activities that would directly worsen or expand the flagged issue area.',
            'compliance_role': 'Unit-level pre-approval with logged conditions. Provide model clauses aligned to risk. Define practical KPIs (e.g., quarterly worker interviews; milestone audits).',
            'contract_scope': 'Include right-to-suspend/terminate if credible allegations emerge. For climate-adjacent work, prohibit scopes that worsen the issue. Pre-clear sensitive communications/case studies.',
            'monitoring': 'Quarterly re-screening aligned to project milestones. Escalate to High if sector-level bans emerge, impacted countries reach ≥3, or investor exclusions reach ≥5 with diversification.',
            'quick_wins': [
                'Add a one-page "Scope Guardrails" annex to proposals—clear and client-friendly.'
            ],
            'client_messaging': 'We\'ll keep the project focused on improvements and avoid activities that could exacerbate the concern—so you can continue operating while strengthening stakeholder trust.',
            'commercial_opportunities': [
                'Focused partner/supplier due diligence tied to the flagged area',
                'Paris-alignment assessment or "Social Audit Lite"',
                'Quarterly ESG risk review synced with delivery milestones'
            ],
            'color': '🟡'
        },
        'High Risk': {
            'business_context': 'Significant ESG concerns identified. Engagement may proceed for strategic clients with executive approval and tightly defined, harm-reducing scopes.',
            'project_team_action': 'Default is to avoid scopes that could enable the flagged activities. Acceptable scopes focus on safety-critical, remediation, decommissioning, just transition, compliance uplift, and renewable transition. For strategic or public-interest cases, route to Executive Review with a concise business case detailing benefits and protections.',
            'acceptable_scopes': 'Safety-critical, environmental remediation, decommissioning, just transition, compliance uplift, renewable transition.',
            'restricted_scopes': 'Fossil expansion, exploration, or any services that could worsen ESG concerns.',
            'strategic_pathway': 'Executive Review path for major clients or public-interest scopes with strict boundaries and evidence requirements.',
            'compliance_role': 'Executive approval with documented rationale. Enhanced Due Diligence (UNGC/OECD/ILO evidence), third-party integrity reports, grievance mechanisms, and an independent verification plan. Define strict service boundaries to prevent greenwashing risk.',
            'contract_scope': 'Mandatory clauses—audit/access rights; corrective action plan with milestones; step-in/exit rights; disclosure cooperation; human-rights remediation obligations. Include performance triggers to pause/exit upon credible allegations, sanctions changes, or KPI failures.',
            'monitoring': 'Monthly active monitoring and milestone reviews. Terminate or pause if conditions are breached or risk escalates.',
            'quick_wins': [
                'Run a targeted "harm-reduction scoping" workshop to shape acceptable work packages.',
                'Produce a two-page executive brief summarizing safeguards, KPIs, and exit triggers.'
            ],
            'client_messaging': 'Given stakeholder expectations, we propose focusing on safety, remediation, and transition-aligned activities only—backed by independent verification and clear exit protections for both sides.',
            'commercial_opportunities': [
                'EDD package with third-party verification',
                'Transition strategy & decommissioning planning',
                'Independent monitoring & KPI assurance'
            ],
            'color': '🔴'
        }
    }

    def categorize_exclusion(self, exclusion_details: List[Dict]) -> str:
        """Categorize exclusions based on reasons and categories."""
        if not exclusion_details:
            return 'No Exclusion Found'

        # Count category matches
        category_scores = {cat: 0 for cat in self.CATEGORY_MAPPING.keys()}

        for detail in exclusion_details:
            motivation = str(detail.get('motivation', '')).lower()
            main_category = str(detail.get('main_category', '')).lower()
            sub_category = str(detail.get('sub_category', '')).lower()

            combined_text = f"{motivation} {main_category} {sub_category}"

            # Check for category keywords
            for category, keywords in self.CATEGORY_MAPPING.items():
                for keyword in keywords:
                    if keyword in combined_text:
                        category_scores[category] += 1
                        break  # Count once per exclusion record

        # Return the category with highest score
        if any(score > 0 for score in category_scores.values()):
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            # Default to Governance if no specific category found but exclusions exist
            return 'Governance'

    def generate_recommendations(self, risk_level: str, exclusion_category: str) -> Dict:
        """Generate DNV-specific recommendations based on risk level."""

        # Get base recommendation from risk level
        if risk_level in self.RECOMMENDATIONS:
            base_recommendation = self.RECOMMENDATIONS[risk_level].copy()
        else:
            # Fallback for edge cases
            base_recommendation = self.RECOMMENDATIONS['Low Risk'].copy()

        # Add category-specific context where relevant
        if risk_level == 'Medium Risk' or risk_level == 'High Risk':
            category_context = self._get_category_specific_context(exclusion_category, risk_level)
            if category_context:
                base_recommendation['category_context'] = category_context

        return base_recommendation

    def _get_category_specific_context(self, exclusion_category: str, risk_level: str) -> str:
        """Provide category-specific context for medium and high risk cases."""

        context_mapping = {
            ('Human Rights', 'Medium Risk'): 'Focus on Freedom of Association and Collective Bargaining commitments, worker voice mechanisms, independent audits with access and remediation clauses. Ensure supplier and partner due diligence covers worker welfare aspects.',

            ('Human Rights', 'High Risk'): 'Enhanced Due Diligence must include ILO compliance evidence, independent verification of working conditions, grievance mechanism effectiveness, and human rights impact assessment. Consider only safety-critical or harm-reduction scopes.',

            ('Climate', 'Medium Risk'): 'Conduct Paris-alignment assessment for all climate-adjacent work. Ensure project includes transition or advisory elements (renewables, decarbonisation). Document rationale for engagement and prohibit services enabling fossil expansion.',

            ('Climate', 'High Risk'): 'Restrict engagement to transition-aligned, decommissioning, or environmental remediation work only. Absolutely prohibit fossil expansion or greenwashing activities. Require monthly monitoring of Paris-alignment compliance.',

            ('Governance', 'Medium Risk'): 'Implement UNGC and OECD adherence requirements. Establish corrective action plans with time-bound milestones and periodic compliance reporting.',

            ('Governance', 'High Risk'): 'Enhanced Due Diligence must include anti-corruption policy evidence, third-party integrity reports, and independent compliance verification. Limit scope to compliance uplift activities only with strict monitoring.',

            ('Country Policy', 'Medium Risk'): 'Include compliance clauses covering sanctions adherence and supplier checks. Validate all contract clauses and monitor compliance exposure throughout engagement.',

            ('Country Policy', 'High Risk'): 'Engagement not recommended until sanctions and legal clearance obtained. If critical public interest scope approved, require monthly sanctions monitoring and immediate termination clause if status changes.'
        }

        return context_mapping.get((exclusion_category, risk_level), '')

    def get_detailed_playbook(self, risk_level: str) -> Dict:
        """Return the complete operational playbook for a given risk level."""

        playbook_details = {
            'Low Risk': {
                'title': 'Proceed per standard controls',
                'business_context': 'No significant ESG concerns identified. Proceed with standard controls.',
                'typical_drivers': ['No exclusions detected', 'Below risk threshold', 'Minimal investor concerns'],
                'project_team_actions': [
                    'Proceed with standard onboarding and project risk assessment',
                    'Document "no exclusions detected / below threshold" and date-stamp sources',
                    'Maintain standard KYC, HSE, Data Privacy checks',
                    'No special approvals required'
                ],
                'compliance_sustainability_role': [
                    'No pre-approval needed',
                    'Random spot checks (quarterly sample basis)',
                    'Add client to automated monitoring (monthly/quarterly update scans)',
                    'Keep evidence pack (sources, parsed year) in central register'
                ],
                'contract_scope_requirements': [
                    'Standard contractual clauses (Code of Conduct, anti-corruption, HSE, data privacy)',
                    'No extra conditions unless sector-specific norms apply'
                ],
                'monitoring_approach': [
                    'Passive monitoring',
                    'Re-screen before major new proposals or annually'
                ]
            },
            'Medium Risk': {
                'title': 'Controlled engagement with enhanced oversight',
                'business_context': 'Moderate ESG concerns identified. Engagement is viable with targeted mitigations and scope guardrails that support business continuity.',
                'typical_drivers': ['Norms/labour-rights concerns', 'Limited geography consensus', 'Single category issues'],
                'project_team_actions': [
                    'Define guardrails to ensure work does not enable flagged activities',
                    'Add a Risk & Mitigation section to the proposal with clear owners and dates',
                    'Hold a short pre-engagement briefing with Compliance/Sustainability to align on scope and mitigations',
                    'If partners are involved, run proportionate due diligence focused on the same risk area'
                ],
                'acceptable_scopes': [
                    'Standard operations',
                    'Safety improvements',
                    'Compliance uplift',
                    'Environmental remediation',
                    'Transition planning'
                ],
                'restricted_scopes': [
                    'Activities that would directly worsen or expand the flagged issue area'
                ],
                'compliance_sustainability_role': [
                    'Unit-level pre-approval with logged conditions',
                    'Provide model clauses aligned to risk (e.g., FoA/CB commitments, worker voice, UNGC/OECD adherence)',
                    'Define practical KPIs (e.g., quarterly worker interviews; milestone audits)'
                ],
                'contract_scope_requirements': [
                    'Include right-to-suspend/terminate if credible allegations emerge',
                    'For climate-adjacent work, add Paris-alignment assessment; prohibit scopes that worsen the issue',
                    'Pre-clear sensitive communications/case studies'
                ],
                'monitoring_approach': [
                    'Quarterly re-screening aligned to project milestones',
                    'Escalate to High if sector-level bans emerge, impacted countries reach ≥3, or investor exclusions reach ≥5 with diversification'
                ],
                'quick_wins': [
                    'Add a one-page "Scope Guardrails" annex to proposals—clear and client-friendly'
                ],
                'client_messaging': 'We\'ll keep the project focused on improvements and avoid activities that could exacerbate the concern—so you can continue operating while strengthening stakeholder trust.',
                'commercial_opportunities': [
                    'Focused partner/supplier due diligence tied to the flagged area',
                    'Paris-alignment assessment or "Social Audit Lite"',
                    'Quarterly ESG risk review synced with delivery milestones'
                ]
            },
            'High Risk': {
                'title': 'Strategic engagement with executive oversight',
                'business_context': 'Significant ESG concerns identified. Engagement may proceed for strategic clients with executive approval and tightly defined, harm-reducing scopes.',
                'typical_drivers': ['Sector-level fossil/coal', 'Multi-country multi-investor consensus', 'Severe Human Rights/Governance issues', 'Long persistence'],
                'project_team_actions': [
                    'Default is to avoid scopes that could enable the flagged activities',
                    'Acceptable scopes focus on safety-critical, remediation, decommissioning, just transition, compliance uplift, and renewable transition',
                    'For strategic or public-interest cases, route to Executive Review with a concise business case detailing benefits and protections'
                ],
                'acceptable_scopes': [
                    'Safety-critical',
                    'Environmental remediation',
                    'Decommissioning',
                    'Just transition',
                    'Compliance uplift',
                    'Renewable transition'
                ],
                'restricted_scopes': [
                    'Fossil expansion',
                    'Exploration',
                    'Any services that could worsen ESG concerns'
                ],
                'strategic_pathway': [
                    'Executive Review path for major clients or public-interest scopes with strict boundaries and evidence requirements'
                ],
                'compliance_sustainability_role': [
                    'Executive approval with documented rationale',
                    'Enhanced Due Diligence (UNGC/OECD/ILO evidence), third-party integrity reports, sanctions/country checks, grievance mechanisms, and an independent verification plan',
                    'Define strict service boundaries to prevent greenwashing risk'
                ],
                'contract_scope_requirements': [
                    'Mandatory clauses—audit/access rights; corrective action plan with milestones; step-in/exit rights; disclosure cooperation; human-rights remediation obligations',
                    'Include performance triggers to pause/exit upon credible allegations, sanctions changes, or KPI failures'
                ],
                'monitoring_approach': [
                    'Monthly active monitoring and milestone reviews',
                    'Terminate or pause if conditions are breached or risk escalates'
                ],
                'quick_wins': [
                    'Run a targeted "harm-reduction scoping" workshop to shape acceptable work packages',
                    'Produce a two-page executive brief summarizing safeguards, KPIs, and exit triggers'
                ],
                'client_messaging': 'Given stakeholder expectations, we propose focusing on safety, remediation, and transition-aligned activities only—backed by independent verification and clear exit protections for both sides.',
                'commercial_opportunities': [
                    'EDD package with third-party verification',
                    'Transition strategy & decommissioning planning',
                    'Independent monitoring & KPI assurance'
                ]
            }
        }

        return playbook_details.get(risk_level, playbook_details['Low Risk'])