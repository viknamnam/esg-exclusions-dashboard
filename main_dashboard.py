"""
Main dashboard entry point and search functionality
"""

#this one works very well. but created a new version as I want the screen to be smaller and mroe compact and perhaps better organised.
import streamlit as st

from dashboard_config import (
    configure_page,
    load_css_styling,
    render_welcome_header,
    initialize_session_state
)
from data_utils import handle_database_loading, get_enhanced_company_suggestions
from dashboard_display import display_comprehensive_dashboard


def enhanced_search_section():
    """Enhanced search section for the dashboard"""

    # Search section header
    if st.session_state.analysis_result is None:
        st.subheader("")
    else:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.subheader("")
        with col2:
            if st.button("🔄 New Search", key="new_search"):
                st.session_state.analysis_result = None
                st.rerun()

    # Enhanced search input with improved placeholder
    search_query = st.text_input(
        "🔎 Company Search",
        placeholder="Enter company name (e.g., 'Shell', 'Royal Dutch', 'Tesla Inc')...",
        key="search_input",
        label_visibility="visible",
        help="Search supports exact matches, partial words, and fuzzy matching"
    )

    selected_company = None

    # Enhanced search logic
    if search_query.strip() and len(search_query.strip()) >= 2:
        with st.spinner("🔍 Searching companies..."):
            suggestions = get_enhanced_company_suggestions(
                st.session_state.checker,
                search_query,
                max_results=15
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


def main():
    """Main application entry point"""

    # Configure the page
    configure_page()

    # Load CSS styling
    load_css_styling()

    # Initialize session state
    initialize_session_state()

    # Handle database loading
    if not handle_database_loading():
        return

    # Render welcome header based on state
    has_results = st.session_state.analysis_result is not None
    render_welcome_header(has_results)

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