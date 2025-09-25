import pandas as pd
import numpy as np
import streamlit as st
import hashlib
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
import logging

from fet_translation import TranslationManager
from fet_utils import FETDataUtils
from wb_sanctions import WorldBankSanctionsHandler  # NEW IMPORT

# Enhanced fuzzy matching (optional)
try:
    from fuzzywuzzy import fuzz, process

    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    st.warning("⚠️ fuzzywuzzy not available - fuzzy matching disabled")

# Import recommendation engine
try:
    from fet_recommendations import RecommendationEngine
except ImportError:
    st.error("❌ fet_recommendations.py not found")
    st.stop()

logger = logging.getLogger(__name__)


class FETCoreEngine:
    """
    Enhanced FET exclusion analysis engine with World Bank sanctions integration.
    """

    def __init__(self, app_dir: Path):
        """Initialize with proper cache structure and World Bank integration."""
        self.app_dir = app_dir
        self.df_master = None
        self.company_lookup = {}
        self.percentile_thresholds = {'50th': 1.0, '80th': 2.0}
        self.preprocessing_done = False

        # Initialize recommendation engine
        self.recommendation_engine = RecommendationEngine()

        # Initialize translation manager
        self.translator = TranslationManager(app_dir)

        # NEW: Initialize World Bank sanctions handler
        self.wb_sanctions = WorldBankSanctionsHandler(app_dir)

        # Cache management
        self.cache_dir = app_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Cache versioning (increment when data structure changes)
        self.CACHE_VERSION = "v2.3"  # Updated version for dual database

        # Cache file paths
        self.cache_files = {
            'df_master': self.cache_dir / f"df_master_{self.CACHE_VERSION}.pkl",
            'company_lookup': self.cache_dir / f"company_lookup_{self.CACHE_VERSION}.pkl",
            'percentile_thresholds': self.cache_dir / f"percentiles_{self.CACHE_VERSION}.pkl",
            'metadata': self.cache_dir / f"cache_metadata_{self.CACHE_VERSION}.pkl"
        }

    def _get_source_file_info(self, file_path: str = None, file_data: bytes = None) -> Dict:
        """Get source file information for cache validation."""
        if file_path and Path(file_path).exists():
            file_path_obj = Path(file_path)
            return {
                'source_type': 'file',
                'file_path': str(file_path_obj),
                'file_size': file_path_obj.stat().st_size,
                'file_mtime': file_path_obj.stat().st_mtime,
                'data_hash': None
            }
        elif file_data:
            return {
                'source_type': 'uploaded',
                'file_path': 'uploaded_file',
                'file_size': len(file_data),
                'file_mtime': datetime.now().timestamp(),
                'data_hash': hashlib.md5(file_data).hexdigest()
            }
        else:
            return {
                'source_type': 'unknown',
                'file_path': None,
                'file_size': 0,
                'file_mtime': 0,
                'data_hash': None
            }

    def _is_cache_valid(self, source_info: Dict) -> bool:
        """Check if persistent cache is valid for the current data sources (FET + Sanctioned)."""
        try:
            # Check if all cache files exist
            if not all(cache_file.exists() for cache_file in self.cache_files.values()):
                logger.info("Cache files missing - will rebuild")
                return False

            # Load cache metadata
            with open(self.cache_files['metadata'], 'rb') as f:
                cached_metadata = pickle.load(f)

            # Check cache version
            if cached_metadata.get('cache_version') != self.CACHE_VERSION:
                logger.info(f"Cache version mismatch: {cached_metadata.get('cache_version')} != {self.CACHE_VERSION}")
                return False

            # Check source file info for both datasets
            cached_source = cached_metadata.get('source_info', {})

            # Validate FET file info
            fet_info_changed = self._check_file_info_changed(
                cached_source.get('fet_file_info', {}),
                source_info.get('fet_file_info', {}),
                'FET'
            )

            if fet_info_changed:
                return False

            # Validate sanctioned file info (if it exists)
            sanctioned_info_changed = self._check_file_info_changed(
                cached_source.get('sanctioned_file_info', {}),
                source_info.get('sanctioned_file_info', {}),
                'Sanctioned'
            )

            if sanctioned_info_changed:
                return False

            # Check if cache is not too old (safety check - max 1 year)
            cache_age_days = (datetime.now().timestamp() - cached_metadata.get('created_at', 0)) / 86400
            if cache_age_days > 365:
                logger.info(f"Cache is too old ({cache_age_days:.1f} days) - will rebuild")
                return False

            logger.info("✅ Persistent cache is valid for combined datasets - loading from disk")
            return True

        except Exception as e:
            logger.warning(f"Cache validation failed: {e}")
            return False

    def _load_from_cache(self) -> bool:
        """Load all preprocessing results from persistent cache."""
        try:
            logger.info("📂 Loading preprocessed data from persistent cache...")

            # Load main dataframe
            with open(self.cache_files['df_master'], 'rb') as f:
                self.df_master = pickle.load(f)

            # Load company lookup
            with open(self.cache_files['company_lookup'], 'rb') as f:
                self.company_lookup = pickle.load(f)

            # Load percentile thresholds
            with open(self.cache_files['percentile_thresholds'], 'rb') as f:
                self.percentile_thresholds = pickle.load(f)

            logger.info(f"✅ Loaded {len(self.df_master):,} records from cache")
            return True

        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")
            return False

    def _save_to_cache(self, source_info: Dict):
        """Save all preprocessing results to persistent cache."""
        try:
            logger.info("💾 Saving preprocessed data to persistent cache...")

            # Save main dataframe
            with open(self.cache_files['df_master'], 'wb') as f:
                pickle.dump(self.df_master, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Save company lookup
            with open(self.cache_files['company_lookup'], 'wb') as f:
                pickle.dump(self.company_lookup, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Save percentile thresholds
            with open(self.cache_files['percentile_thresholds'], 'wb') as f:
                pickle.dump(self.percentile_thresholds, f, protocol=pickle.HIGHEST_PROTOCOL)

            # Save cache metadata
            cache_metadata = {
                'cache_version': self.CACHE_VERSION,
                'created_at': datetime.now().timestamp(),
                'source_info': source_info,
                'record_count': len(self.df_master),
                'company_count': len(self.company_lookup)
            }

            with open(self.cache_files['metadata'], 'wb') as f:
                pickle.dump(cache_metadata, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info("✅ Persistent cache saved successfully")

            # Show cache info to user
            cache_size_mb = sum(f.stat().st_size for f in self.cache_files.values() if f.exists()) / 1024 / 1024
            st.success(f"💾 Preprocessing results cached ({cache_size_mb:.1f}MB) - next startup will be much faster!")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            st.warning(f"⚠️ Could not save cache: {e}")

    def _clear_old_cache_files(self):
        """Remove old cache files with different versions."""
        try:
            cache_pattern = f"*_v*.pkl"
            old_files = list(self.cache_dir.glob(cache_pattern))
            current_files = set(self.cache_files.values())

            for old_file in old_files:
                if old_file not in current_files:
                    old_file.unlink()
                    logger.info(f"Removed old cache file: {old_file.name}")

        except Exception as e:
            logger.warning(f"Failed to clean old cache files: {e}")

    def _get_data_hash(self, df: pd.DataFrame) -> str:
        """Generate hash of dataframe for cache validation."""
        return hashlib.md5(
            f"{len(df)}_{df.columns.tolist()}_{df.iloc[0:3].to_string()}".encode()
        ).hexdigest()[:12]

    def _load_and_preprocess_database_instance(self, file_path: str = None, file_data: bytes = None,
                                               source_url: str = None, wb_file_data: bytes = None):
        """Load AND fully preprocess the FET database (instance method to avoid __file__ issues)."""
        try:
            # Step 1: Load raw FET data
            df_loaded = None
            source_info = ""

            if file_path and Path(file_path).exists():
                try:
                    df_loaded = FETDataUtils.load_dataframe_from_file(file_path=file_path)
                    source_info = f"✅ Loaded {len(df_loaded):,} exclusion records from local Excel file"
                except Exception as e:
                    st.warning(f"⚠️ Local file load failed: {e}")

            if df_loaded is None and source_url:
                try:
                    df_loaded = FETDataUtils.load_dataframe_from_file(source_url=source_url)
                    source_info = f"✅ Loaded {len(df_loaded):,} exclusion records from remote source"
                except Exception as e:
                    st.warning(f"⚠️ Remote load failed: {e}")

            if df_loaded is None and file_data:
                try:
                    df_loaded = FETDataUtils.load_dataframe_from_file(file_data=file_data)
                    source_info = f"✅ Loaded {len(df_loaded):,} exclusion records from uploaded file"
                except Exception as e:
                    st.error(f"❌ Failed to process uploaded file: {e}")
                    return None

            if df_loaded is None:
                return None

            # Step 1.5: Load World Bank sanctions
            wb_loaded = self.wb_sanctions.load_wb_sanctions(wb_file_data)
            wb_stats = self.wb_sanctions.get_stats()

            # Step 2: Full preprocessing (the expensive part that we want to cache!)
            st.info("🔥 Running full preprocessing - company normalization, translations, risk calculations...")

            # Initialize columns reference
            COLUMNS = FETDataUtils.COLUMNS

            # Normalize company names
            company_col = COLUMNS['company_group']
            df_loaded[f'{company_col}_normalized'] = (
                df_loaded[company_col]
                .astype(str)
                .apply(FETDataUtils.normalize_company_name)
            )

            # Create display-friendly date column
            date_col = COLUMNS['exclusion_date']
            df_loaded['exclusion_date_display'] = df_loaded[date_col].apply(
                FETDataUtils.format_date_for_display
            )

            # FIXED: Use the instance's translation manager instead of creating new one
            # Preserve original columns
            motivation_col = COLUMNS['motivation']
            main_category_col = COLUMNS['main_category']
            sub_category_col = COLUMNS['sub_category']

            df_loaded['motivation_original'] = df_loaded[motivation_col].astype(str)
            df_loaded['main_category_original'] = df_loaded[main_category_col].astype(str)
            df_loaded['sub_category_original'] = df_loaded[sub_category_col].astype(str)

            # Translate fields (expensive!) - Use existing translator instance
            df_loaded['motivation_en'] = self.translator.translate_series(df_loaded[motivation_col])
            df_loaded['main_category_en'] = self.translator.translate_series(df_loaded[main_category_col])
            df_loaded['sub_category_en'] = self.translator.translate_series(df_loaded[sub_category_col])

            # Parse years
            year_col = COLUMNS['year']
            df_loaded['year_parsed'] = df_loaded.apply(
                lambda row: (
                        FETDataUtils.parse_year_from_date(row[year_col]) or
                        FETDataUtils.parse_year_from_date(row[date_col])
                ), axis=1
            )

            # Normalize sector/company exclusion
            sector_col = COLUMNS['sector_company']
            df_loaded['scope_normalized'] = (
                df_loaded[sector_col]
                .astype(str)
                .str.lower()
                .str.strip()
                .replace({'sector': 'sector', 'company': 'company'})
                .fillna('company')
            )

            # Canonicalize motivations and categories (expensive!)
            df_loaded['motivation_canonical'] = df_loaded.apply(
                lambda row: FETDataUtils.canonicalize_motivation(
                    row['motivation_en'],
                    row['main_category_en'],
                    row['sub_category_en'],
                    row[COLUMNS['source']]
                ), axis=1
            )

            df_loaded['category_canonical'] = df_loaded.apply(
                lambda row: FETDataUtils.canonicalize_category(
                    row['main_category_en'],
                    row['motivation_en']
                ), axis=1
            )

            # Calculate recency
            current_year = datetime.now().year
            df_loaded['years_ago'] = current_year - df_loaded['year_parsed'].fillna(current_year)

            # Create company lookup (expensive!)
            company_lookup = defaultdict(list)
            normalized_col = f'{company_col}_normalized'

            for idx, row in df_loaded.iterrows():
                normalized_name = row[normalized_col]
                if pd.notna(normalized_name) and normalized_name.strip():
                    company_lookup[normalized_name].append(idx)

            # Calculate percentiles (expensive!)
            percentile_thresholds = FETDataUtils.calculate_percentiles(df_loaded)

            # Get translation stats
            translation_stats = self.translator.get_stats()

            # Return everything preprocessed
            preprocessed_result = {
                'df_master': df_loaded,
                'source_info': source_info,
                'company_lookup': dict(company_lookup),
                'percentile_thresholds': percentile_thresholds,
                'translation_stats': translation_stats,
                'wb_loaded': wb_loaded,
                'wb_stats': wb_stats,
                'preprocessing_complete': True
            }

            return preprocessed_result

        except Exception as e:
            st.error(f"❌ Failed to load and preprocess database: {e}")
            logger.exception("Full error details:")
            return None

    def clear_cache(self):
        """Clear all persistent cache files (use when data structure changes)."""
        try:
            files_removed = 0
            for cache_file in self.cache_files.values():
                if cache_file.exists():
                    cache_file.unlink()
                    files_removed += 1

            # Also clear WB cache
            self.wb_sanctions.clear_cache()

            # Also clear any old cache files
            self._clear_old_cache_files()

            st.success(f"🗑️ Cleared {files_removed} cache files. Next run will rebuild from scratch.")
            logger.info(f"Manually cleared {files_removed} cache files")

        except Exception as e:
            st.error(f"Failed to clear cache: {e}")

    def get_cache_info(self) -> Dict:
        """Get information about the current cache state."""
        cache_info = {
            'cache_exists': all(f.exists() for f in self.cache_files.values()),
            'cache_files': {},
            'total_size_mb': 0,
            'wb_stats': self.wb_sanctions.get_stats()
        }

        for name, path in self.cache_files.items():
            if path.exists():
                size = path.stat().st_size
                cache_info['cache_files'][name] = {
                    'size_mb': size / 1024 / 1024,
                    'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                }
                cache_info['total_size_mb'] += size / 1024 / 1024

        return cache_info

    def load_database(self, uploaded_file_data: bytes = None, dataset_url: str = None) -> bool:
        """Load the FET exclusion database with PERSISTENT caching AND sanctioned individuals data."""

        # Try multiple possible file locations for FET dataset
        possible_files = [
            self.app_dir / "2024-095 FET - 2024 standardized dataset 241210.xlsx",
            self.app_dir / "2024095 FET  2024 standardized dataset 241210.xlsx",  # Alternative filename
            Path("2024-095 FET - 2024 standardized dataset 241210.xlsx"),
            Path("2024095 FET  2024 standardized dataset 241210.xlsx"),
            Path.cwd() / "2024-095 FET - 2024 standardized dataset 241210.xlsx",
            Path.cwd() / "2024095 FET  2024 standardized dataset 241210.xlsx"
        ]

        # Try multiple possible locations for sanctioned individuals
        sanctioned_files = [
            self.app_dir / "Sanctioned individuals and firms.xlsx",
            Path("Sanctioned individuals and firms.xlsx"),
            Path.cwd() / "Sanctioned individuals and firms.xlsx"
        ]

        database_file = None
        sanctioned_file = None

        # Find FET dataset
        for file_path in possible_files:
            if file_path.exists():
                database_file = file_path
                st.info(f"🔍 Found FET database file: {database_file}")
                break

        # Find sanctioned individuals file
        for file_path in sanctioned_files:
            if file_path.exists():
                sanctioned_file = file_path
                st.info(f"📋 Found World Bank sanctioned individuals file: {sanctioned_file}")
                break

        if database_file is None:
            st.warning(f"📂 FET Database file not found in expected locations:")
            for file_path in possible_files[:3]:  # Show first few paths
                st.write(f"  - {file_path}")

        # Get source file information (include both files for cache validation)
        source_info = self._get_combined_source_info(
            fet_file=str(database_file) if database_file else None,
            sanctioned_file=str(sanctioned_file) if sanctioned_file else None,
            file_data=uploaded_file_data
        )

        # Check if we can use persistent cache
        if self._is_cache_valid(source_info):
            if self._load_from_cache():
                self.preprocessing_done = True

                unique_companies = self.df_master[FETDataUtils.COLUMNS['company_group']].nunique()
                unique_investors = self.df_master[FETDataUtils.COLUMNS['excluded_by']].nunique()

                st.success(
                    f"⚡ Loaded from cache: {len(self.df_master):,} total records, {unique_companies:,} companies, {unique_investors:,} investors/authorities")
                st.info("🎯 Combined database ready - FET exclusions + World Bank sanctions!")
                return True

        # Cache not valid - need to do full preprocessing
        st.info(
            "🔄 Cache invalid or missing - performing full preprocessing on combined datasets (this may take a minute)...")

        # Use enhanced loading method that handles multiple datasets
        result = self._load_and_preprocess_multiple_datasets(
            fet_file_path=str(database_file) if database_file else None,
            sanctioned_file_path=str(sanctioned_file) if sanctioned_file else None,
            file_data=uploaded_file_data,
            source_url=dataset_url
        )

        if result is None:
            return False

        # Extract all preprocessed data
        self.df_master = result['df_master']
        self.company_lookup = result['company_lookup']
        self.percentile_thresholds = result['percentile_thresholds']

        # Mark as fully done
        self.preprocessing_done = True

        # Save everything to persistent cache for next time
        self._save_to_cache(source_info)

        # Clean up old cache files
        self._clear_old_cache_files()

        st.success(result['source_info'])

        # Validate required columns
        missing_cols = [col for col in FETDataUtils.COLUMNS.values() if col not in self.df_master.columns]
        if missing_cols:
            st.error(f"❌ Missing required columns: {missing_cols}")
            return False

        unique_companies = self.df_master[FETDataUtils.COLUMNS['company_group']].nunique()
        unique_investors = self.df_master[FETDataUtils.COLUMNS['excluded_by']].nunique()

        st.info(
            f"📈 Combined database contains {unique_companies:,} unique companies from {unique_investors:,} investors/authorities")

        if result['translation_stats']['foreign_translations'] > 0:
            st.info(
                f"🌐 Translation Summary: {result['translation_stats']['foreign_translations']} foreign terms translated, "
                f"{result['translation_stats']['api_calls_made']} API calls used")

        st.success("🚀 Ready to analyze companies from both FET exclusions AND World Bank sanctions!")
        return True

    def _fuzzy_match_company(self, query_name: str, threshold: int = 85) -> Optional[Tuple[str, int]]:
        """Enhanced fuzzy matching with multiple algorithms"""
        if not FUZZY_AVAILABLE or not query_name.strip():
            return None

        normalized_query = FETDataUtils.normalize_company_name(query_name)
        company_names = list(self.company_lookup.keys())

        if not company_names:
            return None

        # Try multiple fuzzy matching approaches
        methods = [
            (fuzz.token_sort_ratio, "token_sort"),
            (fuzz.token_set_ratio, "token_set"),
            (fuzz.partial_ratio, "partial")
        ]

        best_match = None
        best_score = 0

        for scorer, method_name in methods:
            try:
                match = process.extractOne(normalized_query, company_names, scorer=scorer)
                if match and match[1] > best_score and match[1] >= threshold:
                    best_match = match
                    best_score = match[1]
            except Exception as e:
                logger.warning(f"Fuzzy matching error with {method_name}: {e}")
                continue

        if best_match:
            matched_rows = self.company_lookup[best_match[0]]
            if matched_rows:
                original_name = self.df_master.iloc[matched_rows[0]][FETDataUtils.COLUMNS['company_group']]
                return original_name, best_match[1]

        return None

    def search_similar_companies(self, search_term: str, limit: int = 10) -> List[str]:
        """Search for companies with similar names using word-by-word matching."""
        search_words = [word.strip().lower() for word in search_term.split() if word.strip()]

        if not search_words:
            return []

        # Get all unique company names from FET database
        all_companies = self.df_master[FETDataUtils.COLUMNS['company_group']].unique()

        matches = []
        word_matches = []

        for company in all_companies:
            if pd.notna(company):
                company_str = str(company)
                company_lower = company_str.lower()
                company_words = company_lower.split()

                # Method 1: Check if any search word appears as a complete word
                word_match_count = 0
                for search_word in search_words:
                    if any(search_word == company_word for company_word in company_words):
                        word_match_count += 1

                # Method 2: Check if any search word appears as substring in any company word
                partial_match_count = 0
                for search_word in search_words:
                    if any(search_word in company_word for company_word in company_words):
                        partial_match_count += 1

                # Prioritize exact word matches
                if word_match_count > 0:
                    score = word_match_count * 100 + partial_match_count * 10
                    matches.append((company_str, score, f"FET exact words: {word_match_count}"))
                elif partial_match_count > 0:
                    score = partial_match_count * 10
                    word_matches.append((company_str, score, f"FET partial matches: {partial_match_count}"))

        # NEW: Also search World Bank sanctions
        wb_matches = self.wb_sanctions.search_similar_wb_sanctions(search_term, limit)
        for wb_match in wb_matches:
            # wb_match is already formatted like "COMPANY NAME (word matches: 1)"
            matches.append((wb_match, 50, "World Bank match"))

        # Sort by score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        word_matches.sort(key=lambda x: x[1], reverse=True)

        # Combine results - exact word matches first, then partial matches
        all_results = matches + word_matches

        # Format results
        formatted_results = []
        for company, score, match_type in all_results[:limit]:
            # If it's already formatted (from WB), use as-is
            if "(" in company and match_type == "World Bank match":
                formatted_results.append(company)
            else:
                formatted_results.append(f"{company} ({match_type})")

        return formatted_results

    def analyze_company(self, company_name: str, use_fuzzy: bool = True) -> Dict:
        """Analyze a single company with enhanced word-by-word matching and World Bank check."""

        # Try exact match first in FET database
        normalized_query = FETDataUtils.normalize_company_name(company_name)

        matched_company = None
        match_confidence = 0
        company_data = pd.DataFrame()
        fet_found = False

        if normalized_query in self.company_lookup:
            # Exact normalized match found in FET
            row_indices = self.company_lookup[normalized_query]
            company_data = self.df_master.iloc[row_indices]
            matched_company = company_data.iloc[0][FETDataUtils.COLUMNS['company_group']]
            match_confidence = 100
            fet_found = True

        elif use_fuzzy and FUZZY_AVAILABLE:
            # Try fuzzy matching on the original search in FET
            fuzzy_result = self._fuzzy_match_company(company_name)
            if fuzzy_result:
                matched_company, match_confidence = fuzzy_result
                company_data = self.df_master[
                    self.df_master[FETDataUtils.COLUMNS['company_group']] == matched_company
                    ]
                fet_found = True

        # If still no match in FET, try word-by-word search as backup
        if company_data.empty and len(company_name.split()) == 1:
            # For single word searches, look for exact word matches
            search_word = company_name.lower().strip()

            # Find companies where the search word appears as a complete word
            all_companies = self.df_master[FETDataUtils.COLUMNS['company_group']].unique()
            potential_matches = []

            for company in all_companies:
                if pd.notna(company):
                    company_words = str(company).lower().split()
                    if search_word in company_words:
                        potential_matches.append(company)

            # If we found word matches, use the first one
            if potential_matches:
                matched_company = potential_matches[0]
                match_confidence = 85  # High confidence for word match
                company_data = self.df_master[
                    self.df_master[FETDataUtils.COLUMNS['company_group']] == matched_company
                    ]
                fet_found = True

        # NEW: Check World Bank sanctions separately
        wb_result = self.wb_sanctions.check_wb_sanctions(company_name)
        wb_found = wb_result['found']

        # If we have a match from FET, use that name for WB check too
        if fet_found and matched_company:
            wb_result_alt = self.wb_sanctions.check_wb_sanctions(matched_company)
            if wb_result_alt['found'] and not wb_found:
                wb_result = wb_result_alt
                wb_found = True

        # Calculate risk level from FET data
        risk_level, risk_factors = self._calculate_risk_score(company_data)

        # NEW: Enhance risk factors with World Bank information
        if wb_found:
            risk_factors['wb_sanctions'] = wb_result
            # Upgrade risk level if World Bank sanctioned
            if risk_level == "Low Risk":
                risk_level = "Medium Risk"
                risk_factors['reason'] = f"World Bank sanctions detected. {risk_factors['reason']}"
        else:
            risk_factors['wb_sanctions'] = {'found': False}

        # Collect FET details
        exclusion_details = []
        if not company_data.empty:
            for _, row in company_data.iterrows():
                detail = {}
                for key, col_name in FETDataUtils.COLUMNS.items():
                    value = row.get(col_name)
                    if pd.notna(value):
                        detail[key] = value
                exclusion_details.append(detail)

        # NEW: Add World Bank details if found
        wb_details = []
        if wb_found:
            wb_details = wb_result.get('details', [])

        # Determine overall match status
        overall_found = fet_found or wb_found
        if fet_found:
            final_matched_company = matched_company
            final_confidence = match_confidence
        elif wb_found:
            final_matched_company = wb_result['matched_name']
            final_confidence = wb_result['confidence']
        else:
            final_matched_company = None
            final_confidence = 0

        # Categorize exclusions and generate recommendations
        exclusion_category = self.recommendation_engine.categorize_exclusion(exclusion_details)
        recommendations = self.recommendation_engine.generate_recommendations(risk_level, exclusion_category)

        return {
            "query": {"company_name": company_name},
            "match": {
                "found": overall_found,
                "matched_company": final_matched_company,
                "confidence": final_confidence,
                "fet_found": fet_found,
                "wb_found": wb_found
            },
            "risk_assessment": {
                "level": risk_level,
                "factors": risk_factors,
                "category": exclusion_category
            },
            "recommendations": recommendations,
            "exclusion_details": exclusion_details,
            "wb_details": wb_details  # NEW: Separate WB details
        }

    def _calculate_risk_score(self, company_data: pd.DataFrame) -> Tuple[str, Dict]:
        """Calculate comprehensive risk score using new methodology."""

        if company_data.empty:
            return "Low Risk", {
                "reason": "Company not found in FET exclusion database - No investor exclusions identified",
                "unique_investors": 0,
                "total_exclusions": 0,
                "recent_exclusions": 0,
                "consensus_adjusted_score": 0.0,
                "confidence_score": 1.0,
                "percentile": 0.0,
                "status": "Not Excluded"
            }

        # Make a copy to avoid modifying original data
        company_data = company_data.copy()

        # Calculate row scores
        company_data['row_score'] = company_data.apply(FETDataUtils.calculate_row_score, axis=1)
        base_score = company_data['row_score'].sum()

        # Calculate consensus multipliers
        investor_mult, geo_mult = FETDataUtils.calculate_consensus_multipliers(company_data)
        consensus_adjusted_score = base_score * investor_mult * geo_mult

        # Calculate confidence
        confidence_score = FETDataUtils.calculate_confidence_score(company_data)

        # Core metrics
        unique_investors = company_data[FETDataUtils.COLUMNS['excluded_by']].dropna().nunique()
        unique_countries = company_data[FETDataUtils.COLUMNS['investor_country']].dropna().nunique()
        total_exclusions = len(company_data)

        # Recent exclusions (≤24 months)
        recent_exclusions = (company_data['years_ago'] <= 2).sum()

        # Determine risk level using new tiering system
        high_risk_override = self._check_high_risk_overrides(company_data, unique_investors, unique_countries)

        if (consensus_adjusted_score >= self.percentile_thresholds['80th']) or high_risk_override:
            risk_level = "High Risk"
            reason = f"Score: {consensus_adjusted_score:.1f} (≥80th percentile) or high-risk criteria met"
        elif consensus_adjusted_score >= self.percentile_thresholds['50th']:
            risk_level = "Medium Risk"
            reason = f"Score: {consensus_adjusted_score:.1f} (50-80th percentile)"
        else:
            risk_level = "Low Risk"
            reason = f"Score: {consensus_adjusted_score:.1f} (<50th percentile)"

        # Calculate percentile more precisely
        if consensus_adjusted_score >= self.percentile_thresholds['80th']:
            percentile = 80.0 + min(19.9, (consensus_adjusted_score - self.percentile_thresholds['80th']) * 5)
        elif consensus_adjusted_score >= self.percentile_thresholds['50th']:
            percentile = 50.0 + ((consensus_adjusted_score - self.percentile_thresholds['50th']) /
                                 (self.percentile_thresholds['80th'] - self.percentile_thresholds['50th'])) * 30
        else:
            percentile = (consensus_adjusted_score / self.percentile_thresholds['50th']) * 50 if \
                self.percentile_thresholds['50th'] > 0 else 0

        risk_factors = {
            "reason": reason,
            "unique_investors": int(unique_investors),
            "unique_countries": int(unique_countries),
            "total_exclusions": int(total_exclusions),
            "recent_exclusions": int(recent_exclusions),
            "base_score": float(base_score),
            "investor_multiplier": float(investor_mult),
            "geographic_multiplier": float(geo_mult),
            "consensus_adjusted_score": float(consensus_adjusted_score),
            "confidence_score": float(confidence_score),
            "percentile": float(percentile),
            "status": "Excluded"
        }

        return risk_level, risk_factors

    def _check_high_risk_overrides(self, company_data: pd.DataFrame, unique_investors: int,
                                   unique_countries: int) -> bool:
        """Check for high-risk override conditions."""

        # Sector-level fossil/coal exclusions
        sector_fossil = (
                (company_data['scope_normalized'] == 'sector') &
                (company_data['category_canonical'] == 'climate')
        ).any()

        # Multiple investors/countries
        breadth_override = unique_investors >= 5 or unique_countries >= 3

        # Multiple severe categories
        category_override = len(company_data['category_canonical'].unique()) >= 2

        # Persistence (≥3 years)
        if not company_data.empty and 'years_ago' in company_data.columns:
            min_years_ago = company_data['years_ago'].min()
            max_years_ago = company_data['years_ago'].max()
            persistence_override = (max_years_ago - min_years_ago) >= 3
        else:
            persistence_override = False

        # Forced/child labour confirmed by multiple sources
        forced_child_labour = company_data['motivation_canonical'].isin(['forced labour', 'child labour'])
        serious_labour_override = (
                forced_child_labour.any() and
                (unique_investors >= 3 or unique_countries >= 3)
        )

        return (sector_fossil or breadth_override or category_override or
                persistence_override or serious_labour_override)

    def _load_and_preprocess_multiple_datasets(self, fet_file_path: str = None, sanctioned_file_path: str = None,
                                               file_data: bytes = None, source_url: str = None):
        """Load and preprocess FET dataset + sanctioned individuals dataset."""
        try:
            # Step 1: Load main FET dataset
            df_fet = None
            source_info = ""

            if fet_file_path and Path(fet_file_path).exists():
                try:
                    df_fet = FETDataUtils.load_dataframe_from_file(file_path=fet_file_path)
                    source_info = f"✅ Loaded {len(df_fet):,} FET exclusion records from local Excel file"
                except Exception as e:
                    st.warning(f"⚠️ FET file load failed: {e}")

            if df_fet is None and file_data:
                try:
                    df_fet = FETDataUtils.load_dataframe_from_file(file_data=file_data)
                    source_info = f"✅ Loaded {len(df_fet):,} FET exclusion records from uploaded file"
                except Exception as e:
                    st.error(f"❌ Failed to process uploaded FET file: {e}")
                    return None

            if df_fet is None:
                st.error("❌ No FET dataset found")
                return None

            # Step 2: Load sanctioned individuals dataset (if available)
            df_merged = df_fet  # Start with FET data

            if sanctioned_file_path and Path(sanctioned_file_path).exists():
                try:
                    # Load sanctioned individuals file
                    df_sanctioned_raw = pd.read_excel(sanctioned_file_path, engine='openpyxl')
                    st.info(f"📋 Loaded {len(df_sanctioned_raw):,} rows from World Bank sanctions file")

                    # Transform sanctioned data to match FET structure
                    df_sanctioned_mapped = self._map_sanctioned_to_fet_structure(df_sanctioned_raw)

                    if len(df_sanctioned_mapped) > 0:
                        # Merge datasets
                        df_merged = pd.concat([df_fet, df_sanctioned_mapped], ignore_index=True)

                        source_info += f"\n📋 Added {len(df_sanctioned_mapped):,} World Bank sanctioned entities"
                        source_info += f"\n🔗 Total merged records: {len(df_merged):,}"

                        st.success(
                            f"🔗 Successfully merged datasets: {len(df_fet):,} FET + {len(df_sanctioned_mapped):,} sanctioned = {len(df_merged):,} total")

                except Exception as e:
                    st.warning(f"⚠️ Failed to load World Bank sanctions file: {e}")
                    st.info("📊 Continuing with FET data only...")

            # Step 3: Apply full preprocessing to merged dataset
            st.info("🔄 Running full preprocessing - company normalization, translations, risk calculations...")

            # Initialize columns reference
            COLUMNS = FETDataUtils.COLUMNS

            # Normalize company names
            company_col = COLUMNS['company_group']
            df_merged[f'{company_col}_normalized'] = (
                df_merged[company_col]
                .astype(str)
                .apply(FETDataUtils.normalize_company_name)
            )

            # Create display-friendly date column
            date_col = COLUMNS['exclusion_date']
            df_merged['exclusion_date_display'] = df_merged[date_col].apply(
                FETDataUtils.format_date_for_display
            )

            # Preserve original columns and translate
            motivation_col = COLUMNS['motivation']
            main_category_col = COLUMNS['main_category']
            sub_category_col = COLUMNS['sub_category']

            df_merged['motivation_original'] = df_merged[motivation_col].astype(str)
            df_merged['main_category_original'] = df_merged[main_category_col].astype(str)
            df_merged['sub_category_original'] = df_merged[sub_category_col].astype(str)

            # Translate fields using existing translator instance
            df_merged['motivation_en'] = self.translator.translate_series(df_merged[motivation_col])
            df_merged['main_category_en'] = self.translator.translate_series(df_merged[main_category_col])
            df_merged['sub_category_en'] = self.translator.translate_series(df_merged[sub_category_col])

            # Parse years
            year_col = COLUMNS['year']
            df_merged['year_parsed'] = df_merged.apply(
                lambda row: (
                        FETDataUtils.parse_year_from_date(row[year_col]) or
                        FETDataUtils.parse_year_from_date(row[date_col])
                ), axis=1
            )

            # Normalize sector/company exclusion
            sector_col = COLUMNS['sector_company']
            df_merged['scope_normalized'] = (
                df_merged[sector_col]
                .astype(str)
                .str.lower()
                .str.strip()
                .replace({'sector': 'sector', 'company': 'company'})
                .fillna('company')
            )

            # Canonicalize motivations and categories
            df_merged['motivation_canonical'] = df_merged.apply(
                lambda row: FETDataUtils.canonicalize_motivation(
                    row['motivation_en'],
                    row['main_category_en'],
                    row['sub_category_en'],
                    row[COLUMNS['source']]
                ), axis=1
            )

            df_merged['category_canonical'] = df_merged.apply(
                lambda row: FETDataUtils.canonicalize_category(
                    row['main_category_en'],
                    row['motivation_en']
                ), axis=1
            )

            # Calculate recency
            current_year = datetime.now().year
            df_merged['years_ago'] = current_year - df_merged['year_parsed'].fillna(current_year)

            # Create company lookup
            company_lookup = defaultdict(list)
            normalized_col = f'{company_col}_normalized'

            for idx, row in df_merged.iterrows():
                normalized_name = row[normalized_col]
                if pd.notna(normalized_name) and normalized_name.strip():
                    company_lookup[normalized_name].append(idx)

            # Calculate percentiles
            percentile_thresholds = FETDataUtils.calculate_percentiles(df_merged)

            # Get translation stats
            translation_stats = self.translator.get_stats()

            # Return everything preprocessed
            preprocessed_result = {
                'df_master': df_merged,
                'source_info': source_info,
                'company_lookup': dict(company_lookup),
                'percentile_thresholds': percentile_thresholds,
                'translation_stats': translation_stats,
                'preprocessing_complete': True
            }

            return preprocessed_result

        except Exception as e:
            st.error(f"❌ Failed to load and preprocess datasets: {e}")
            logger.exception("Full error details:")
            return None

    def _map_sanctioned_to_fet_structure(self, df_sanctioned):
        """Map sanctioned individuals data to FET dataset structure."""
        try:
            # First, let's see what columns we have in the sanctioned file
            st.info(f"📊 Sanctioned file columns: {list(df_sanctioned.columns)}")

            # Expected columns: Firm Name, Additional Firm Info, Address, Country, Ineligibility Period, From Date, To Date, Grounds
            expected_columns = ['Firm Name', 'Additional Firm Info', 'Address', 'Country', 'Ineligibility Period',
                                'From Date', 'To Date', 'Grounds']

            # Clean and prepare the data
            df_clean = df_sanctioned.copy()

            # Find the header row that contains these expected columns
            header_row = None
            for idx, row in df_clean.iterrows():
                row_values = [str(cell).strip() for cell in row.values if pd.notna(cell)]
                if any('Firm Name' in val for val in row_values):
                    header_row = idx
                    break

            if header_row is not None:
                # Set the header row and clean the data
                df_clean.columns = df_clean.iloc[header_row]
                df_clean = df_clean.iloc[header_row + 1:].reset_index(drop=True)
                st.info(f"📋 Found header row at index {header_row}")

            # Remove empty rows
            df_clean = df_clean.dropna(subset=['Firm Name']).reset_index(drop=True)
            df_clean = df_clean[df_clean['Firm Name'].astype(str).str.strip() != ''].reset_index(drop=True)

            num_entities = len(df_clean)
            st.info(f"📋 Found {num_entities} sanctioned entities after cleaning")

            if num_entities == 0:
                st.warning("⚠️ No valid sanctioned entities found in the file")
                return pd.DataFrame(columns=list(FETDataUtils.COLUMNS.values()))

            # Create new dataframe with FET structure
            fet_columns = FETDataUtils.COLUMNS
            df_mapped = pd.DataFrame(index=range(num_entities))

            # Map the available columns to FET structure

            # 1. Company identification
            df_mapped[fet_columns['company_group']] = df_clean['Firm Name'].astype(str)
            df_mapped[fet_columns['subsidiary_name']] = df_clean['Firm Name'].astype(str)  # Same as parent

            # 2. Country information (use actual country data if available)
            if 'Country' in df_clean.columns:
                df_mapped[fet_columns['company_country']] = df_clean['Country'].fillna('Various').astype(str)
                df_mapped[fet_columns['subsidiary_country']] = df_clean['Country'].fillna('Various').astype(str)
            else:
                df_mapped[fet_columns['company_country']] = 'Various'
                df_mapped[fet_columns['subsidiary_country']] = 'Various'

            # 3. Motivation and grounds (use actual grounds if available)
            base_motivation = 'World Bank Sanctions'
            if 'Grounds' in df_clean.columns:
                # Use the actual grounds but clean them up
                grounds_cleaned = df_clean['Grounds'].fillna('Unspecified').astype(str)
                df_mapped[fet_columns['motivation']] = grounds_cleaned
                df_mapped[fet_columns['further_sub_category']] = grounds_cleaned
            else:
                df_mapped[fet_columns['motivation']] = base_motivation
                df_mapped[fet_columns['further_sub_category']] = 'Debarment/Sanctions List'

            # 4. Categories
            df_mapped[fet_columns['main_category']] = 'Sanctions'
            df_mapped[fet_columns['sub_category']] = 'World Bank Sanctions'

            # 5. Authority information
            df_mapped[fet_columns['financial_institution']] = 'World Bank'
            df_mapped[fet_columns['excluded_by']] = 'World Bank Group'
            df_mapped[fet_columns['investor_country']] = 'International'

            # 6. Date information (use From Date if available)
            if 'From Date' in df_clean.columns:
                # Try to parse the From Date
                try:
                    from_dates = pd.to_datetime(df_clean['From Date'], errors='coerce')
                    # Convert to Excel date format for consistency with FET data
                    excel_dates = []
                    for date_val in from_dates:
                        if pd.notna(date_val):
                            excel_date = (date_val - datetime(1900, 1, 1)).days + 1
                            excel_dates.append(excel_date)
                        else:
                            # Default to current date if parsing fails
                            excel_date = (datetime.now() - datetime(1900, 1, 1)).days + 1
                            excel_dates.append(excel_date)

                    df_mapped[fet_columns['exclusion_date']] = excel_dates

                    # Extract years for the year column
                    years = []
                    for date_val in from_dates:
                        if pd.notna(date_val):
                            years.append(date_val.year)
                        else:
                            years.append(datetime.now().year)
                    df_mapped[fet_columns['year']] = years

                except Exception as e:
                    st.warning(f"⚠️ Failed to parse From Date, using current date: {e}")
                    current_date = datetime.now()
                    excel_date = (current_date - datetime(1900, 1, 1)).days + 1
                    df_mapped[fet_columns['exclusion_date']] = excel_date
                    df_mapped[fet_columns['year']] = current_date.year
            else:
                # Use current date as fallback
                current_date = datetime.now()
                excel_date = (current_date - datetime(1900, 1, 1)).days + 1
                df_mapped[fet_columns['exclusion_date']] = excel_date
                df_mapped[fet_columns['year']] = current_date.year

            # 7. Source and website
            df_mapped[fet_columns['source']] = 'World Bank Sanctions and Debarments'
            df_mapped[
                fet_columns['website']] = 'https://www.worldbank.org/en/projects-operations/procurement/debarred-firms'

            # 8. Exclusion scope
            df_mapped[fet_columns['sector_company']] = 'company'  # Individual company/entity level

            # Reorder columns to match FET structure exactly
            df_mapped = df_mapped.reindex(columns=list(fet_columns.values()), fill_value='N/A')

            st.success(f"✅ Successfully mapped {len(df_mapped)} World Bank sanctioned entities to FET structure")

            # Show a sample of the mapped data with more details
            if len(df_mapped) > 0:
                st.info("📋 Sample of mapped sanctioned entities:")
                sample_size = min(5, len(df_mapped))
                for i in range(sample_size):
                    entity_name = df_mapped.iloc[i][fet_columns['company_group']]
                    country = df_mapped.iloc[i][fet_columns['company_country']]
                    grounds = df_mapped.iloc[i][fet_columns['motivation']]
                    st.write(f"  {i + 1}. **{entity_name}** ({country}) - {grounds}")

                if len(df_mapped) > 5:
                    st.write(f"  ... and {len(df_mapped) - 5} more entities")

            return df_mapped

        except Exception as e:
            st.error(f"❌ Failed to map sanctioned data: {e}")
            import traceback
            st.error(f"📄 Full error: {traceback.format_exc()}")

            # Return empty dataframe with correct structure if mapping fails
            empty_df = pd.DataFrame(columns=list(FETDataUtils.COLUMNS.values()))
            return empty_df

    def _get_combined_source_info(self, fet_file: str = None, sanctioned_file: str = None,
                                  file_data: bytes = None) -> Dict:
        """Get source file information for both datasets for cache validation."""
        info = {
            'source_type': 'combined',
            'fet_file_info': {},
            'sanctioned_file_info': {},
            'data_hash': None
        }

        # Get FET file info
        if fet_file and Path(fet_file).exists():
            fet_path = Path(fet_file)
            info['fet_file_info'] = {
                'file_path': str(fet_path),
                'file_size': fet_path.stat().st_size,
                'file_mtime': fet_path.stat().st_mtime,
            }
        elif file_data:
            info['fet_file_info'] = {
                'file_path': 'uploaded_file',
                'file_size': len(file_data),
                'file_mtime': datetime.now().timestamp(),
                'data_hash': hashlib.md5(file_data).hexdigest()
            }

        # Get sanctioned file info
        if sanctioned_file and Path(sanctioned_file).exists():
            sanctioned_path = Path(sanctioned_file)
            info['sanctioned_file_info'] = {
                'file_path': str(sanctioned_path),
                'file_size': sanctioned_path.stat().st_size,
                'file_mtime': sanctioned_path.stat().st_mtime,
            }

        return info

    def _check_file_info_changed(self, cached_info: Dict, current_info: Dict, file_type: str) -> bool:
        """Check if file information has changed for cache validation."""

        # If no current info, file doesn't exist (that's okay for sanctioned file)
        if not current_info:
            if file_type == 'Sanctioned':
                # Sanctioned file is optional - if it wasn't cached and still doesn't exist, that's fine
                return not cached_info
            else:
                # FET file is required
                logger.info(f"{file_type} file info missing - will rebuild cache")
                return True

        # If cached info exists but current doesn't match
        if cached_info:
            if current_info.get('file_path') != cached_info.get('file_path'):
                logger.info(f"{file_type} file path changed - will rebuild cache")
                return True

            if current_info.get('file_mtime') != cached_info.get('file_mtime'):
                logger.info(f"{file_type} file modification time changed - will rebuild cache")
                return True

            if current_info.get('file_size') != cached_info.get('file_size'):
                logger.info(f"{file_type} file size changed - will rebuild cache")
                return True

            # Check data hash for uploaded files
            if 'data_hash' in current_info and current_info.get('data_hash') != cached_info.get('data_hash'):
                logger.info(f"{file_type} uploaded file hash changed - will rebuild cache")
                return True
        else:
            # No cached info but current info exists - file was added
            logger.info(f"New {file_type} file detected - will rebuild cache")
            return True

    def debug_company_search_streamlit(self, company_name: str) -> None:
        """Debug company search with Streamlit UI."""
        st.subheader(f"🔍 Debug Search: '{company_name}'")

        # Show search words
        search_words = [word.strip().lower() for word in company_name.split() if word.strip()]
        st.write(f"**Search words:** {search_words}")

        # Show normalization for exact matching
        normalized = FETDataUtils.normalize_company_name(company_name)
        st.write(f"**Normalized for exact match:** '{normalized}'")

        # Check if exact match exists in FET
        if normalized in self.company_lookup:
            st.success("✅ Exact normalized match found in FET!")
            indices = self.company_lookup[normalized]
            original_names = [self.df_master.iloc[i][FETDataUtils.COLUMNS['company_group']] for i in indices[:3]]
            st.write(f"**Matched companies:** {original_names}")
        else:
            st.error("❌ No exact normalized match found in FET")

        # Word-by-word search in FET
        st.write("### 🔎 Word-by-word search results (FET):")
        similar = self.search_similar_companies(company_name, 20)

        if similar:
            st.success(f"Found {len(similar)} companies containing your search words:")
            for i, match in enumerate(similar, 1):
                st.write(f"{i:2d}. {match}")
        else:
            st.error("❌ No companies found containing any of your search words in FET")

        # NEW: World Bank search
        st.write("### 🏛️ World Bank sanctions check:")
        wb_result = self.wb_sanctions.check_wb_sanctions(company_name)

        if wb_result['found']:
            st.success(f"✅ Found in World Bank sanctions: {wb_result['matched_name']}")
            st.write(f"**Match type:** {wb_result['match_type']}")
            st.write(f"**Confidence:** {wb_result['confidence']}%")
        else:
            st.info("❌ Not found in World Bank sanctions")

        # Try fuzzy matching if available
        if FUZZY_AVAILABLE:
            st.write("### 🎯 Fuzzy matching results (FET):")
            try:
                all_companies = [str(c) for c in self.df_master[FETDataUtils.COLUMNS['company_group']].unique() if
                                 pd.notna(c)]
                fuzzy_matches = process.extract(company_name, all_companies, limit=5, scorer=fuzz.partial_ratio)

                if fuzzy_matches:
                    for match, score in fuzzy_matches:
                        if score >= 60:
                            st.write(f"- {match} (similarity: {score}%)")
                else:
                    st.write("No good fuzzy matches found in FET")
            except Exception as e:
                st.error(f"Fuzzy matching error: {e}")