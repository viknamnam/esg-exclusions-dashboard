"""
Cache Management UI Component
"""
import streamlit as st
from datetime import datetime
from pathlib import Path


def render_cache_management_sidebar():
    """Render cache management controls in sidebar"""
    if not hasattr(st.session_state, 'checker') or st.session_state.checker is None:
        return

    checker = st.session_state.checker

    with st.sidebar:
        st.markdown("---")
        st.subheader("💾 Cache Management")

        # Get cache info
        cache_info = checker.get_cache_info()

        if cache_info['cache_exists']:
            st.success(f"✅ Cache loaded ({cache_info['total_size_mb']:.1f}MB)")

            # Show cache details in expander
            with st.expander("📊 Cache Details"):
                for name, info in cache_info['cache_files'].items():
                    st.write(f"**{name}**: {info['size_mb']:.1f}MB")
                    st.caption(f"Modified: {info['modified']}")

            # Clear cache button
            if st.button("🗑️ Clear Cache", help="Force rebuild on next run"):
                checker.clear_cache()
                st.rerun()

        else:
            st.warning("⚠️ No cache found")
            st.caption("Will build cache on next data load")



def render_cache_status_info():
    """Render cache status information in main area with World Bank info"""
    if not hasattr(st.session_state, 'checker') or st.session_state.checker is None:
        return

    checker = st.session_state.checker
    cache_info = checker.get_cache_info()

    if cache_info['cache_exists']:
        col1, col2, col3, col4 = st.columns(4)  # NEW: Added 4th column

        with col1:
            st.metric("Cache Status", "Active", help="Preprocessing results are cached")

        with col2:
            st.metric("Cache Size", f"{cache_info['total_size_mb']:.1f}MB",
                      help="Total size of cached files")

        with col3:
            # Get newest file modification time
            newest_time = max([
                datetime.fromisoformat(info['modified'])
                for info in cache_info['cache_files'].values()
            ])
            days_old = (datetime.now() - newest_time).days
            st.metric("Cache Age", f"{days_old} days",
                      help="Days since cache was created")

        # NEW: World Bank status
        with col4:
            wb_stats = cache_info.get('wb_stats', {})
            wb_entities = wb_stats.get('total_entities', 0)
            wb_status = "Active" if wb_entities > 0 else "Not loaded"
            st.metric("World Bank DB", wb_status,
                      help=f"{wb_entities} sanctioned entities" if wb_entities > 0 else "World Bank sanctions not loaded")

        if days_old > 30:
            st.info("💡 Cache is over 30 days old. Consider updating with fresh data.")

        # NEW: World Bank status info
        if wb_entities == 0:
            st.info("🏛️ World Bank sanctions database not loaded. Upload the sanctions file for complete coverage.")
        else:
            st.success(f"🏛️ World Bank sanctions active: {wb_entities:,} entities monitored")


def show_cache_explanation():
    """Show explanation of caching system"""
    st.info("""
    **🚀 Performance Optimization Active**

    This application caches all preprocessing results (company normalization, translations, 
    risk calculations) to disk. This means:

    - **First run**: Takes 1-2 minutes to process your data
    - **Subsequent runs**: Loads instantly from cache  
    - **Cache validity**: Automatically rebuilds if data changes
    - **Annual updates**: Simply replace your Excel file - cache will auto-rebuild
    """)