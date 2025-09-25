"""
World Bank Sanctions Database Handler
"""
import pandas as pd
import numpy as np
import pickle
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from fuzzywuzzy import fuzz
import re
import logging

from fet_utils import FETDataUtils

logger = logging.getLogger(__name__)


class WorldBankSanctionsHandler:
    """Handler for World Bank sanctions database"""

    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.sanctions_list = []
        self.normalized_sanctions = {}
        self.cache_dir = app_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        # Cache file for WB sanctions
        self.wb_cache_file = self.cache_dir / "wb_sanctions_v1.pkl"

    def load_wb_sanctions(self, file_data: bytes = None) -> bool:
        """Load World Bank sanctions database"""

        # Try to load from cache first
        if self._load_from_cache():
            return True

        try:
            # Load the Excel file
            if file_data:
                df = pd.read_excel(file_data, engine='openpyxl')
            else:
                # Try default location
                wb_file = self.app_dir / "Sanctioned individuals and firms.xlsx"
                if wb_file.exists():
                    df = pd.read_excel(wb_file, engine='openpyxl')
                else:
                    st.warning("📂 World Bank sanctions file not found")
                    return False

            # Extract firm names (skip metadata rows)
            firms = []
            for _, row in df.iterrows():
                if pd.notna(row.iloc[0]):
                    firm_name = str(row.iloc[0]).strip()
                    # Skip metadata and header rows
                    if (len(firm_name) > 3 and
                            'Downloaded' not in firm_name and
                            'Firm Name' not in firm_name and
                            firm_name != ''):
                        firms.append(firm_name)

            self.sanctions_list = firms

            # Create normalized lookup
            self.normalized_sanctions = {}
            for firm in firms:
                normalized = FETDataUtils.normalize_company_name(firm)
                if normalized:
                    self.normalized_sanctions[normalized] = firm

            # Save to cache
            self._save_to_cache()

            st.success(f"✅ Loaded {len(self.sanctions_list)} World Bank sanctioned entities")
            return True

        except Exception as e:
            st.error(f"❌ Failed to load World Bank sanctions: {e}")
            return False

    def _load_from_cache(self) -> bool:
        """Load from cache if available"""
        try:
            if self.wb_cache_file.exists():
                with open(self.wb_cache_file, 'rb') as f:
                    cache_data = pickle.load(f)

                self.sanctions_list = cache_data['sanctions_list']
                self.normalized_sanctions = cache_data['normalized_sanctions']

                logger.info(f"✅ Loaded {len(self.sanctions_list)} WB sanctions from cache")
                return True
        except Exception as e:
            logger.warning(f"Failed to load WB cache: {e}")

        return False

    def _save_to_cache(self):
        """Save to cache"""
        try:
            cache_data = {
                'sanctions_list': self.sanctions_list,
                'normalized_sanctions': self.normalized_sanctions,
                'created_at': datetime.now().timestamp()
            }

            with open(self.wb_cache_file, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info("💾 World Bank sanctions cached successfully")
        except Exception as e:
            logger.warning(f"Failed to cache WB sanctions: {e}")

    def check_wb_sanctions(self, company_name: str, fuzzy_threshold: int = 85) -> Dict:
        """Check if company is in World Bank sanctions list"""

        if not self.sanctions_list:
            return {
                'found': False,
                'matched_name': None,
                'match_type': None,
                'confidence': 0,
                'details': []
            }

        # Normalize the query
        normalized_query = FETDataUtils.normalize_company_name(company_name)

        # 1. Exact normalized match
        if normalized_query in self.normalized_sanctions:
            original_name = self.normalized_sanctions[normalized_query]
            return {
                'found': True,
                'matched_name': original_name,
                'match_type': 'exact',
                'confidence': 100,
                'details': [{
                    'sanctioned_entity': original_name,
                    'source': 'World Bank',
                    'sanction_type': 'World Bank Debarment',
                    'match_confidence': 100
                }]
            }

        # 2. Fuzzy matching
        best_match = None
        best_score = 0

        # Try fuzzy matching against original names
        for original_name in self.sanctions_list:
            # Compare with original name
            score1 = fuzz.token_sort_ratio(company_name.lower(), original_name.lower())
            score2 = fuzz.partial_ratio(company_name.lower(), original_name.lower())
            score = max(score1, score2)

            if score > best_score and score >= fuzzy_threshold:
                best_match = original_name
                best_score = score

        # Also try against normalized names
        for normalized_name, original_name in self.normalized_sanctions.items():
            score1 = fuzz.token_sort_ratio(normalized_query, normalized_name)
            score2 = fuzz.partial_ratio(normalized_query, normalized_name)
            score = max(score1, score2)

            if score > best_score and score >= fuzzy_threshold:
                best_match = original_name
                best_score = score

        if best_match:
            return {
                'found': True,
                'matched_name': best_match,
                'match_type': 'fuzzy',
                'confidence': best_score,
                'details': [{
                    'sanctioned_entity': best_match,
                    'source': 'World Bank',
                    'sanction_type': 'World Bank Debarment',
                    'match_confidence': best_score
                }]
            }

        return {
            'found': False,
            'matched_name': None,
            'match_type': None,
            'confidence': 0,
            'details': []
        }

    def search_similar_wb_sanctions(self, search_term: str, limit: int = 10) -> List[str]:
        """Search for similar sanctioned entities"""
        if not self.sanctions_list:
            return []

        search_words = [word.strip().lower() for word in search_term.split() if word.strip()]
        if not search_words:
            return []

        matches = []

        for entity in self.sanctions_list:
            entity_lower = entity.lower()
            entity_words = entity_lower.split()

            # Count word matches
            word_match_count = 0
            for search_word in search_words:
                if any(search_word == entity_word for entity_word in entity_words):
                    word_match_count += 1

            # Count partial matches
            partial_match_count = 0
            for search_word in search_words:
                if any(search_word in entity_word for entity_word in entity_words):
                    partial_match_count += 1

            if word_match_count > 0:
                score = word_match_count * 100 + partial_match_count * 10
                matches.append((entity, score, f"word matches: {word_match_count}"))
            elif partial_match_count > 0:
                score = partial_match_count * 10
                matches.append((entity, score, f"partial matches: {partial_match_count}"))

        # Sort by score
        matches.sort(key=lambda x: x[1], reverse=True)

        # Format results
        formatted_results = []
        for entity, score, match_type in matches[:limit]:
            formatted_results.append(f"{entity} ({match_type})")

        return formatted_results

    def get_stats(self) -> Dict:
        """Get statistics about the WB sanctions database"""
        return {
            'total_entities': len(self.sanctions_list),
            'cache_exists': self.wb_cache_file.exists(),
            'normalized_count': len(self.normalized_sanctions)
        }

    def clear_cache(self):
        """Clear WB sanctions cache"""
        try:
            if self.wb_cache_file.exists():
                self.wb_cache_file.unlink()
            logger.info("🗑️ World Bank sanctions cache cleared")
        except Exception as e:
            logger.warning(f"Failed to clear WB cache: {e}")