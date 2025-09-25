"""
Dashboard configuration, styling, and UI setup
"""
import streamlit as st

def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Investor ESG Exclusions Dashboard",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )


def load_css_styling():
    """Load CSS styling for the dashboard with DNV OneDesign branding"""
    css = """
    <style>
        /* Import Official DNV Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Gantari:wght@400;500;600&display=swap');

        /* DNV OneDesign Color & Typography System */
        :root {
            /* Official DNV Primary Colors */
            --dnv-blue-dark: #0F204B;        /* Dark Blue - headings, primary text */
            --dnv-blue-sea: #003591;         /* Sea Blue - links, interactive */
            --dnv-blue-sky: #99D9F0;         /* Sky Blue - hover effects, content modules */
            --dnv-green-digi: #91FFB4;       /* Digi Green - interactive on dark backgrounds */
            --dnv-black: #1A1A19;            /* Black - body text */
            --dnv-white: #FFFFFF;            /* White - backgrounds, text on dark */

            /* Official DNV Supporting Colors */
            --dnv-sandstone: #CCCBC9;        /* Sandstone - borders */
            --dnv-sandstone-30: #4F4D4A;     /* Sandstone 30 - muted text */
            --dnv-sandstone-95: #F3F2F2;     /* Sandstone 95 - neutral background */
            --dnv-sky-95: #E9F7FC;           /* Sky Blue 95 - soft background */
            --dnv-earth: #F2E6D5;            /* Earth - warm background */
            --dnv-earth-95: #F9F3EC;         /* Earth 95 - subtle background */

            /* Official DNV Alert Colors */
            --dnv-red-energy: #EB2A34;       /* Energy Red - critical alerts */
            --dnv-red-95: #FDE8E9;           /* Energy Red 95 - error backgrounds */
            --dnv-green-land: #3F9C35;       /* Land Green - success */
            --dnv-green-95: #EDF9EC;         /* Land Green 95 - success backgrounds */
            --dnv-sunflower: #FFE900;        /* Sunflower 50 - warning */
            --dnv-sunflower-95: #FFFDE5;     /* Sunflower 95 - warning backgrounds */
            --dnv-cyan: #33C8FF;             /* Cyan - information */
            --dnv-cyan-95: #E5F8FF;          /* Cyan 95 - info backgrounds */

            /* Design System */
            --dnv-radius: 12px;              /* Soft, professional radius */
            --dnv-shadow: 0 4px 16px rgba(15,32,75,0.06);

            /* Official DNV Typography - Application Scale */
            --dnv-font-primary: 'Gantari', Arial, sans-serif;
            --dnv-font-display: 'DNV Display', 'Gantari', Arial, sans-serif;

            /* Application Font Hierarchy */
            --dnv-title: 34px;               /* H1 Application */
            --dnv-lead: 22px;                /* Lead Application */ 
            --dnv-h2: 26px;                  /* H2 Application */
            --dnv-h3: 20px;                  /* H3 Application */
            --dnv-h4: 16px;                  /* H4 Application */
            --dnv-body: 16px;                /* Body Application */
            --dnv-small: 14px;               /* Small Application */

            /* Line Heights */
            --dnv-lh-title: 42px;
            --dnv-lh-lead: 28px;
            --dnv-lh-h2: 32px;
            --dnv-lh-h3: 24px;
            --dnv-lh-h4: 22px;
            --dnv-lh-body: 24px;
            --dnv-lh-small: 24px;
        }

        /* Official DNV Typography System */
        html, body { 
            font-family: var(--dnv-font-primary); 
            color: var(--dnv-blue-dark); 
            background: var(--dnv-white); 
        }

        /* DNV Application Font Hierarchy */
        h1 { 
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-title);
            line-height: var(--dnv-lh-title);
            color: var(--dnv-blue-dark);
            margin: 0 0 16px 0;
        }

        h2 { 
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-h2);
            line-height: var(--dnv-lh-h2);
            color: var(--dnv-blue-dark);
            margin: 0 0 12px 0;
        }

        h3 { 
            font-family: var(--dnv-font-primary);
            font-weight: 600; /* Demi-Bold */
            font-size: var(--dnv-h3);
            line-height: var(--dnv-lh-h3);
            color: var(--dnv-blue-dark);
            margin: 0 0 8px 0;
        }

        h4 { 
            font-family: var(--dnv-font-primary);
            font-weight: 600; /* Demi-Bold */
            font-size: var(--dnv-h4);
            line-height: var(--dnv-lh-h4);
            color: var(--dnv-blue-dark);
            margin: 0 0 6px 0;
        }

        p, li, .text-body { 
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-body);
            line-height: var(--dnv-lh-body);
            color: var(--dnv-black);
        }

        .lead-text {
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-lead);
            line-height: var(--dnv-lh-lead);
            color: var(--dnv-blue-sea);
        }

        .small-text, small {
            font-family: var(--dnv-font-primary);
            font-weight: 500; /* Medium */
            font-size: var(--dnv-small);
            line-height: var(--dnv-lh-small);
            color: var(--dnv-black);
        }

        .caption-text {
            font-family: var(--dnv-font-primary);
            font-weight: 600; /* Demi-Bold */
            font-size: var(--dnv-small);
            line-height: var(--dnv-lh-small);
            color: var(--dnv-sandstone-30);
        }

        /* Links - DNV Specification */
        a { 
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            color: var(--dnv-blue-sea); 
            text-decoration: underline;
        }
        a:hover { 
            color: var(--dnv-blue-dark); 
        }

        /* Streamlit App Layout */
        .main .block-container,
        .block-container {
          /* vertical spacing */
          padding-top: 0 !important;
          padding-bottom: 0.5rem;
        
          /* width + centering */
          max-width: 1100px;        /* central column width */
          margin-left: auto !important;
          margin-right: auto !important;
        
          /* comfy gutters on left/right */
          padding-left: 0.5rem !important;
          padding-right: 0.5rem !important;
        
          font-family: var(--dnv-font-primary);
        }
        
        @media (min-width: 1600px) {
          .main .block-container { max-width: 1200px; }
        }
        @media (min-width: 2000px) {
          .main .block-container { max-width: 1280px; }
        }

        .stApp { 
            background-color: var(--dnv-sandstone-95); 
            font-family: var(--dnv-font-primary);
        }

        
        .element-container:first-child {
            margin-top: 0 !important;
        }

        /* Ensure welcome header has minimal top margin */
        .welcome-header:first-child {
            margin-top: 0 !important;
        }

        /* Welcome Header - DNV Typography */
        .welcome-header {
            padding: 28px 18px; 
            border: 1px solid var(--dnv-sandstone);
            border-radius: var(--dnv-radius); 
            background: var(--dnv-white);
            box-shadow: var(--dnv-shadow); 
            text-align: center;
            margin-bottom: 1.5rem;
            margin-top: 0 !important;
        }

        .welcome-title {
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-title); /* 34px */
            line-height: var(--dnv-lh-title); /* 42px */
            color: var(--dnv-blue-dark);
            margin: 0 0 8px 0;
        }

        .welcome-subtitle {
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-lead); /* 22px */
            line-height: var(--dnv-lh-lead); /* 28px */
            color: var(--dnv-blue-sea);
            margin: 0 0 16px 0;
        }

        .context-box {
            margin: 8px auto 0; 
            max-width: 820px;
            background: var(--dnv-sky-95); 
            border: 1px solid var(--dnv-blue-sky);
            border-radius: 10px; 
            padding: 12px 14px; 
            text-align: left;
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-body); /* 16px */
            line-height: var(--dnv-lh-body); /* 24px */
            color: var(--dnv-black);
        }

        /* Company Header Card - DNV Typography */
        .company-header {
            background: var(--dnv-white);
            padding: 1rem;
            border-radius: var(--dnv-radius);
            margin-bottom: 1rem;
            border: 1px solid var(--dnv-sandstone);
            box-shadow: var(--dnv-shadow);
        }

        .company-title {
            font-family: var(--dnv-font-primary);
            font-weight: 400; /* Regular */
            font-size: var(--dnv-h2); /* 26px */
            line-height: var(--dnv-lh-h2); /* 32px */
            color: var(--dnv-blue-dark);
            margin: 0 0 8px 0;
        }

        .company-subtitle {
            font-family: var(--dnv-font-primary);
            font-weight: 500; /* Medium */
            font-size: var(--dnv-small); /* 14px */
            line-height: var(--dnv-lh-small); /* 24px */
            color: var(--dnv-sandstone-30);
            margin: 0 0 12px 0;
        }

        .risk-metrics-row {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 0.5rem;
        }

        /* Risk Badges - Official DNV Alert Colors */
        .risk-badge {
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.9rem;
            text-align: center;
            min-width: 100px;
            font-family: var(--dnv-font);
        }

        .quick-metric {
            font-size: var(--dnv-small);
            color: var(--dnv-sandstone-30);
            background: var(--dnv-white);
            padding: 0.4rem 0.8rem;
            border-radius: var(--dnv-radius);
            border: 1px solid var(--dnv-sandstone);
        }

        .quick-metric strong {
            color: var(--dnv-blue-dark);
        }

        /* Risk Level Colors - Official DNV Alert Colors */
        .high-risk { 
            background: var(--dnv-red-energy); 
            color: var(--dnv-white); 
            border: 1px solid var(--dnv-red-energy);
        }
        .medium-risk { 
            background: var(--dnv-sunflower); 
            color: var(--dnv-blue-dark); 
            border: 1px solid var(--dnv-sunflower);
        }
        .low-risk { 
            background: var(--dnv-green-land); 
            color: var(--dnv-white); 
            border: 1px solid var(--dnv-green-land);
        }

        /* Alert Containers */
        .alert-container {
            background: var(--dnv-white);
            padding: 1rem;
            border-radius: var(--dnv-radius);
            margin-bottom: 1rem;
            border: 1px solid var(--dnv-sandstone);
            box-shadow: var(--dnv-shadow);
        }

        .alert-box {
            padding: 0.8rem;
            border-radius: 6px;
            margin-bottom: 0.5rem;
        }

        /* Alert Colors - Official DNV Alert System */
        .alert-high { 
            background: var(--dnv-red-95); 
            border: 1px solid var(--dnv-red-energy); 
            color: var(--dnv-blue-dark);
        }
        .alert-medium { 
            background: var(--dnv-sunflower-95); 
            border: 1px solid var(--dnv-sunflower); 
            color: var(--dnv-blue-dark);
        }
        .alert-low { 
            background: var(--dnv-green-95); 
            border: 1px solid var(--dnv-green-land); 
            color: var(--dnv-blue-dark);
        }

        .alert-title {
            font-weight: 700;
            font-size: 0.95rem;
            margin: 0 0 0.3rem 0;
            color: inherit;
        }

        .alert-text {
            font-size: var(--dnv-small);
            margin: 0;
            line-height: 1.4;
            color: inherit;
        }

        /* Warning Flags */
        .flags-container {
            display: flex;
            gap: 0.4rem;
            flex-wrap: wrap;
            margin-top: 0.5rem;
        }

        .flag {
            background: #B91C1C;
            color: white;
            padding: 0.3rem 0.6rem;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            font-family: var(--dnv-font);
        }

        .flag-warning { background: #D97706; }
        .flag-info { background: var(--dnv-blue-sea); }

        /* Debug Panel */
        .debug-panel {
            background: #F0F9FF;
            padding: 1rem;
            border-radius: var(--dnv-radius);
            margin: 1rem 0;
            border: 1px solid var(--dnv-blue-sea);
        }

        .debug-title {
            font-weight: 700;
            color: var(--dnv-blue-sea);
            margin: 0 0 0.5rem 0;
        }

        /* Score Breakdown */
        .score-breakdown {
            background: var(--dnv-bg-alt);
            padding: 1rem;
            border-radius: 6px;
            margin: 0.5rem 0;
            border: 1px solid var(--dnv-sand-border-light);
        }

        /* Buttons - DNV Style */
        .btn {
            display: inline-flex; 
            align-items: center; 
            gap: 8px;
            padding: 10px 14px; 
            border-radius: 10px; 
            font-weight: 600;
            border: 1px solid transparent; 
            cursor: pointer; 
            line-height: 1.1;
            font-family: var(--dnv-font);
        }

        .btn-primary { 
            background: var(--dnv-blue-sea); 
            color: #fff; 
        }
        .btn-primary:hover { 
            filter: brightness(0.95); 
        }

        .btn-outline {
            background: #fff; 
            border: 1px solid var(--dnv-sand-border);
            color: var(--dnv-blue-dark);
        }
        .btn-outline:hover { 
            border-color: var(--dnv-blue-sea); 
            color: var(--dnv-blue-sea); 
        }

        /* Cards */
        .card {
            background: var(--dnv-bg); 
            border: 1px solid var(--dnv-sand-border-light);
            border-radius: var(--dnv-radius); 
            box-shadow: var(--dnv-shadow);
            padding: 14px;
        }

        .card-header { 
            font-weight: 700; 
            margin-bottom: 6px; 
            color: var(--dnv-blue-dark);
        }

        /* KPI Tiles */
        .kpi {
            display: flex; 
            flex-direction: column; 
            gap: 2px; 
            padding: 12px;
            border: 1px solid var(--dnv-sand-border-light); 
            border-radius: var(--dnv-radius); 
            background: var(--dnv-bg);
        }

        .kpi .label { 
            font-size: var(--dnv-small); 
            color: var(--dnv-sand-text);
        }

        .kpi .value { 
            font-weight: 800; 
            font-size: 20px; 
            color: var(--dnv-blue-dark); 
        }

        /* Utility Classes */
        .muted { color: var(--dnv-sand-text); }
        .hr { 
            height: 1px; 
            background: var(--dnv-sand-border-light); 
            border: 0; 
            margin: 12px 0; 
        }

        /* Hide Streamlit UI Elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_welcome_header(has_results=False):
    """Render the welcome header based on app state"""
    if not has_results:
        # Full welcome header for first-time users
        st.markdown("""
            <div class="welcome-header">
                <h1 class="welcome-title">🛡️ ESG Risk Intelligence Dashboard</h1>
                <p class="welcome-subtitle">Enhanced Investor Exclusion Analysis</p>
                <div class="context-box">
                    Track investor exclusions with clarity. Know which companies 
                    are flagged, why they’re flagged, and what it means for your next decision.
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Compact header when showing results
        st.markdown("""
            <div class="welcome-header" style="padding: 1rem 0; margin-bottom: 1rem;">
                <h2 class="welcome-title" style="font-size: 1.5rem; margin-bottom: 0.2rem;">🛡️ ESG Risk Intelligence Dashboard</h2>
                <p class="welcome-subtitle" style="font-size: 0.9rem; margin-bottom: 0;">Track investor exclusions with clarity. Know which companies 
                    are flagged, why they’re flagged, and what it means for your next decision.</p>
            </div>
            """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize all session state keys"""
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