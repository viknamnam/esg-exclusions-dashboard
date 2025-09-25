"""
Data loading, processing, and utility functions for the FET dashboard
"""
import pandas as pd
import re
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Tuple
from fet_utils import FETDataUtils

def _norm_key(name: str) -> str:
    # normalize and also strip any trailing parentheticals for dedupe
    base = FETDataUtils.normalize_company_name(name)
    base = re.sub(r"\([^)]*\)", "", base).strip()
    return base

def _parse_company_and_label(raw: str) -> tuple[str, str]:
    raw = str(raw).strip()
    # Only treat parentheses as metadata if they match known labels
    m = re.match(
        r"^(?P<name>.+?)\s+\((?P<label>(?:alias|aka|exact|partial|word match|fuzzy(?:\s*\d+%)?|score\s*\d+%|confidence\s*\d+%))\)$",
        raw, flags=re.I
    )
    if m:
        return m.group("name").strip(), m.group("label")
    return raw, "match"


# Replace or enhance the format_date_for_display function in data_utils.py:

def format_date_for_display(date_value) -> str:
    """Enhanced function to format dates with full date display (YYYY-MM-DD) including Excel serial dates"""
    import pandas as pd
    import re
    from datetime import datetime

    if pd.isna(date_value) or not str(date_value).strip():
        return "N/A"

    date_str = str(date_value).strip()

    # If it's already in clean format, return as-is
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # Handle Excel serial dates (numbers)
    try:
        if date_str.isdigit() or (date_str.replace('.', '').isdigit() and '.' in date_str):
            excel_date = float(date_str)
            if excel_date > 0 and excel_date < 100000:  # Reasonable range for Excel dates
                # Convert Excel serial date to datetime
                # Excel epoch is 1900-01-01 but Excel incorrectly treats 1900 as leap year
                base_date = datetime(1899, 12, 30)
                try:
                    converted_date = base_date + pd.Timedelta(days=excel_date)
                    return converted_date.strftime('%Y-%m-%d')
                except:
                    pass
    except (ValueError, OverflowError):
        pass

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


@st.cache_resource(show_spinner=False)
def load_fet_checker_cached(uploaded_file_data: bytes = None):
    """Load FET checker with caching to prevent multiple loads"""
    try:
        # Import here to avoid circular imports
        from fet_core3 import FETCoreEngine
        from pathlib import Path

        app_dir = Path(__file__).parent
        checker = FETCoreEngine(app_dir)

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
            from fet_core3 import FETCoreEngine
            from pathlib import Path

            app_dir = Path(__file__).parent
            checker = FETCoreEngine(app_dir)
            if checker.load_database(uploaded_file_data):
                return checker
            else:
                return None
        except Exception as e:
            st.error(f"❌ Failed to initialize FET checker: {e}")
            return None


def get_recent_activity_and_latest_date(df_details):
    """Get full date information instead of just year"""
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


def get_enhanced_company_suggestions(checker, search_query, max_results=9):
    """
    Enhanced company search using fet_core's advanced capabilities
    Combines word-by-word matching, fuzzy matching, and intelligent ranking
    """
    if not search_query.strip() or len(search_query.strip()) < 2:
        return []

    suggestions = []
    seen_companies = set()

    # Method 1: Use fet_core's advanced search_similar_companies
    if False:
        try:
            similar_companies = checker.search_similar_companies(search_query, limit=20)

            for company_info in similar_companies:
                company_name, match_info = _parse_company_and_label(company_info)
                key = _norm_key(company_name)
                if key and key not in seen_companies:
                    suggestions.append((company_name, match_info, "word_match"))
                    seen_companies.add(key)

        except Exception as e:
            st.error(f"Word-by-word search error: {e}")

    # Method 2: Try direct fuzzy matching for additional high-confidence matches
    try:
        fuzzy_result = checker._fuzzy_match_company(search_query, threshold=70)
        if fuzzy_result:
            fuzzy_company, confidence = fuzzy_result
            if fuzzy_company not in seen_companies and confidence >= 75:
                match_info = f"{confidence}% similarity"
                suggestions.append((fuzzy_company, match_info, "fuzzy_match"))
                seen_companies.add(fuzzy_company)
    except Exception as e:
        st.error(f"Fuzzy matching error: {e}")

    # Method 3: Fallback to simple filtering with improved logic
    if len(suggestions) < 3 and hasattr(checker, 'df_master'):
        try:
            from fet_utils import FETDataUtils
            all_companies = checker.df_master[FETDataUtils.COLUMNS['company_group']].dropna().unique()
            search_terms = search_query.lower().strip().split()

            fallback_matches = []
            for company in all_companies:
                company_str = str(company).lower()

                # Score based on how many search terms appear
                matches = sum(1 for term in search_terms if term in company_str)
                if matches > 0:
                    score = (matches / len(search_terms)) * 100
                    if score >= 50 and str(company) not in seen_companies:  # At least half the terms match
                        match_info = f"{matches}/{len(search_terms)} terms matched"
                        fallback_matches.append((str(company), match_info, "fallback", score))

            # Sort by score and add top matches
            fallback_matches.sort(key=lambda x: x[3], reverse=True)
            for company_name, match_info, match_type, score in fallback_matches[:10]:
                if company_name not in seen_companies:
                    suggestions.append((company_name, match_info, match_type))
                    seen_companies.add(company_name)

        except Exception as e:
            st.error(f"Fallback search error: {e}")

    # Sort suggestions by match type priority and limit results
    def sort_key(item):
        match_type = item[2]
        if match_type == "word_match":
            return 0  # Highest priority
        elif match_type == "fuzzy_match":
            return 1
        else:
            return 2  # Lowest priority

    suggestions.sort(key=sort_key)
    return suggestions[:max_results]


def handle_database_loading():
    """Handle database loading logic with proper error handling for both FET and World Bank databases"""
    # Only attempt loading once per session
    if not st.session_state.database_loaded and not st.session_state.loading_attempted:
        st.session_state.loading_attempted = True

        with st.spinner("🔥 Initializing databases..."):
            checker = load_fet_checker()

        if checker:
            st.session_state.checker = checker
            st.session_state.database_loaded = True
        else:
            st.session_state.loading_attempted = False

    # Handle file upload separately and only if no database loaded
    if not st.session_state.database_loaded:
        st.error("📂 Databases not found. Please upload the Excel files.")

        # Create two columns for file uploads
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**FET Exclusions Database**")
            fet_file = st.file_uploader(
                "Upload FET Excel Dataset (.xlsx)",
                type=["xlsx"],
                help="Upload the FET exclusion database Excel file",
                key="fet_file_uploader"
            )

        with col2:
            st.markdown("**World Bank Sanctions Database**")
            wb_file = st.file_uploader(
                "Upload World Bank Sanctions (.xlsx)",
                type=["xlsx"],
                help="Upload the World Bank sanctions Excel file (optional)",
                key="wb_file_uploader"
            )

        # Process uploads
        if fet_file and not st.session_state.upload_processed:
            st.session_state.upload_processed = True

            with st.spinner("🔥 Processing uploaded databases..."):
                fet_data = fet_file.read()
                wb_data = wb_file.read() if wb_file else None

                checker = load_fet_checker(fet_data, wb_data)

            if checker:
                st.session_state.checker = checker
                st.session_state.database_loaded = True
                st.success("🎉 Databases loaded successfully!")
                st.rerun()
            else:
                st.session_state.upload_processed = False
                st.error("❌ Failed to process uploaded files")
                return False

        elif not fet_file:
            st.info("👆 Please upload at least the FET database Excel file to continue")
            st.caption("World Bank sanctions database is optional but recommended for complete coverage")
            return False

    # Safety check with better error handling
    if not st.session_state.database_loaded or st.session_state.checker is None:
        st.error("❌ Database not ready. Please refresh the page.")
        return False

    # Only show loading message once
    if st.session_state.database_loaded and 'load_success_shown' not in st.session_state:
        st.session_state.load_success_shown = True

    return True