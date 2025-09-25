import pandas as pd
import numpy as np
import re
import io
import requests
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class FETDataUtils:
    """Utility class for FET data processing operations."""

    # Column names from FET dataset
    COLUMNS = {
        'company_group': 'Company group',
        'company_country': 'Company group country',
        'subsidiary_name': 'Standardized subsidiary name',
        'subsidiary_country': 'Standardized subsidiary country',
        'motivation': 'FI Motivation for exclusion',
        'main_category': 'Main category',
        'sub_category': 'Sub-category',
        'further_sub_category': 'Further sub category',
        'financial_institution': 'Financial institution',
        'excluded_by': 'Excluded by investor',
        'investor_country': 'Investor parent country',
        'exclusion_date': 'Date of FI Exclusion list',
        'source': 'Source',
        'website': 'Website',
        'sector_company': 'Sector/company exclusion',
        'year': 'Year'
    }

    # Category weights for risk scoring
    CATEGORY_WEIGHTS = {
        'climate': 3.0,
        'human rights': 2.5,
        'governance': 2.5,
        'business practices': 1.5,
        'cannabis': 0.8,
        'unspecified': 1.0
    }

    # Motivation weights (multipliers to base weight)
    MOTIVATION_WEIGHTS = {
        'thermal coal': 1.30,
        'corruption': 1.30,
        'forced labour': 1.30,
        'child labour': 1.30,
        'shale': 1.20,
        'fossil expansion': 1.20,
        'oil & gas': 1.10,
        'human rights': 1.10,
        'labour rights': 1.10,
        'norms-based': 1.0,
        'controversial behaviour': 0.9,
        'unspecified': 1.0
    }

    # Category mapping for canonicalization
    CATEGORY_MAPPING = {
        'climate': [
            'climate', 'fossil', 'coal', 'oil', 'gas', 'carbon', 'emission',
            'environmental', 'deforestation', 'palm oil', 'renewable',
            'sustainability', 'energy transition', 'fossil expansion', 'thermal coal',
            'shale', 'tar sands', 'arctic drilling'
        ],
        'human rights': [
            'human rights', 'child labor', 'child labour', 'forced labor', 'forced labour',
            'labor rights', 'labour rights', 'workplace rights', 'social issues',
            'indigenous rights', 'community rights', 'worker rights'
        ],
        'governance': [
            'corruption', 'bribery', 'fraud', 'governance', 'compliance',
            'money laundering', 'tax evasion', 'regulatory', 'ethics',
            'integrity', 'transparency', 'anti-corruption'
        ],
        'business practices': [
            'business practices', 'controversial behaviour', 'norms-based',
            'conduct', 'violations', 'breaches'
        ],
        'cannabis': [
            'cannabis', 'marijuana', 'hemp'
        ]
    }

    # Motivation mapping for canonicalization
    MOTIVATION_MAPPING = {
        'thermal coal': ['thermal coal', 'coal mining', 'coal power', 'coal-fired'],
        'corruption': ['corruption', 'bribery', 'corrupt practices'],
        'forced labour': ['forced labour', 'forced labor', 'slave labor', 'slavery'],
        'child labour': ['child labour', 'child labor', 'child work'],
        'shale': ['shale', 'fracking', 'hydraulic fracturing'],
        'fossil expansion': ['fossil expansion', 'fossil fuel expansion', 'new fossil'],
        'oil & gas': ['oil', 'gas', 'petroleum', 'lng', 'oil & gas'],
        'human rights': ['human rights violations', 'human rights'],
        'labour rights': ['labour rights', 'labor rights', 'worker rights'],
        'norms-based': ['norms-based', 'norms based', 'global compact'],
        'controversial behaviour': ['controversial behaviour', 'controversial behavior']
    }

    @staticmethod
    @st.cache_data(ttl=3600)
    def load_dataframe_from_file(file_path: str = None, file_data: bytes = None,
                                 source_url: str = None) -> pd.DataFrame:
        """
        Load dataframe from file with date columns preserved as strings
        """
        # Force date columns to be read as strings to preserve Excel formatting
        dtype_spec = {
            'Date of FI Exclusion list': 'str',
            'Year': 'str'
        }

        if file_path and Path(file_path).exists():
            try:
                df = pd.read_excel(
                    file_path,
                    engine='openpyxl',
                    dtype=dtype_spec
                )
                return df
            except Exception as e:
                raise Exception(f"Failed to load local file: {e}")

        elif source_url:
            try:
                response = requests.get(source_url, timeout=120)
                response.raise_for_status()
                df = pd.read_excel(
                    io.BytesIO(response.content),
                    engine='openpyxl',
                    dtype=dtype_spec
                )
                return df
            except Exception as e:
                raise Exception(f"Failed to load remote file: {e}")

        elif file_data:
            try:
                df = pd.read_excel(
                    io.BytesIO(file_data),
                    engine='openpyxl',
                    dtype=dtype_spec
                )
                return df
            except Exception as e:
                raise Exception(f"Failed to load uploaded file: {e}")

        else:
            raise Exception("No valid data source provided")

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Normalize company name for matching."""
        if pd.isna(name):
            return ""

        name = str(name).strip().lower()

        legal_suffixes = [
            'inc', 'incorporated', 'corp', 'corporation', 'ltd', 'limited',
            'llc', 'plc', 'sa', 'ag', 'gmbh', 'bv', 'nv', 'spa', 'srl',
            'co', 'company', 'group', 'holding', 'holdings', 'international',
            'global', 'worldwide', 'enterprises', 'solutions'
        ]

        for suffix in legal_suffixes:
            pattern = rf'\b{re.escape(suffix)}\.?\s*$'
            name = re.sub(pattern, '', name)

        name = re.sub(r'[^\w\s&-]', ' ', name)
        name = re.sub(r'\s+', ' ', name)

        return name.strip()

    @staticmethod
    def format_date_for_display(date_value) -> str:
        """Format date value for display."""
        if pd.isna(date_value) or not str(date_value).strip():
            return "N/A"

        date_str = str(date_value).strip()

        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str

        if ';' in date_str:
            dates = [d.strip() for d in date_str.split(';') if d.strip()]
            if dates and re.match(r'^\d{4}-\d{2}-\d{2}$', dates[0]):
                if len(dates) > 1:
                    return f"{dates[0]} (+{len(dates) - 1} more)"
                else:
                    return dates[0]

        year_match = re.search(r'\b(20\d{2})\b', date_str)
        if year_match:
            return str(year_match.group())

        if date_str.isdigit() and len(date_str) == 4:
            year = int(date_str)
            if 2000 <= year <= 2030:
                return str(year)

        return "N/A"

    @staticmethod
    def parse_year_from_date(date_value) -> Optional[int]:
        """Parse year from date value."""
        if pd.isna(date_value) or not str(date_value).strip():
            return None

        date_str = str(date_value).strip()

        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return int(date_str[:4])

        if ';' in date_str:
            first_date = date_str.split(';')[0].strip()
            if re.match(r'^\d{4}-\d{2}-\d{2}$', first_date):
                return int(first_date[:4])

        year_match = re.search(r'\b(20\d{2})\b', date_str)
        if year_match:
            return int(year_match.group())

        if date_str.isdigit() and len(date_str) == 4:
            year = int(date_str)
            if 2000 <= year <= 2030:
                return year

        return None

    @staticmethod
    def canonicalize_motivation(motivation_text: str, category_text: str = '',
                                sub_category_text: str = '', source_text: str = '') -> str:
        """Canonicalize motivation text."""
        if pd.isna(motivation_text):
            motivation_text = ''

        # Combine all text for analysis
        combined_text = f"{motivation_text} {category_text} {sub_category_text} {source_text}".lower()

        # Try to match known motivations
        for canonical_motivation, keywords in FETDataUtils.MOTIVATION_MAPPING.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return canonical_motivation

        # If no specific motivation found but text exists
        if motivation_text.strip():
            return motivation_text.lower().strip()

        return 'unspecified'

    @staticmethod
    def canonicalize_category(category_text: str, motivation_text: str = '') -> str:
        """Canonicalize category text."""
        if pd.isna(category_text):
            category_text = ''

        combined_text = f"{category_text} {motivation_text}".lower()

        # Try to match known categories
        for canonical_category, keywords in FETDataUtils.CATEGORY_MAPPING.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return canonical_category

        return 'unspecified'

    @staticmethod
    def calculate_percentiles(df_master: pd.DataFrame) -> Dict:
        """Calculate percentile thresholds for risk scoring."""
        # Default thresholds
        percentile_thresholds = {
            '50th': 1.0,
            '80th': 2.0
        }

        try:
            company_scores = {}
            companies = df_master[FETDataUtils.COLUMNS['company_group']].unique()

            for company in companies:
                if pd.notna(company):
                    company_data = df_master[df_master[FETDataUtils.COLUMNS['company_group']] == company].copy()

                    # Calculate row scores
                    def calculate_row_score(row):
                        category = row.get('category_canonical', 'unspecified')
                        category_weight = FETDataUtils.CATEGORY_WEIGHTS.get(category, 1.0)

                        motivation = row.get('motivation_canonical', 'unspecified')
                        motivation_weight = FETDataUtils.MOTIVATION_WEIGHTS.get(motivation, 1.0)

                        scope = row.get('scope_normalized', 'company')
                        scope_mult = 1.15 if scope == 'sector' else 1.0

                        years_ago = row.get('years_ago', 0)
                        if years_ago <= 1:
                            recency_mult = 1.0
                        elif years_ago <= 2:
                            recency_mult = 0.9
                        elif years_ago <= 5:
                            recency_mult = 0.8
                        else:
                            recency_mult = 0.7

                        return category_weight * motivation_weight * scope_mult * recency_mult

                    company_data['row_score'] = company_data.apply(calculate_row_score, axis=1)
                    base_score = company_data['row_score'].sum()

                    # Calculate consensus multipliers
                    unique_investors = company_data[FETDataUtils.COLUMNS['excluded_by']].dropna().nunique()
                    unique_countries = company_data[FETDataUtils.COLUMNS['investor_country']].dropna().nunique()

                    if unique_investors >= 20:
                        investor_mult = 1.30
                    elif unique_investors >= 10:
                        investor_mult = 1.20
                    elif unique_investors >= 5:
                        investor_mult = 1.10
                    elif unique_investors >= 2:
                        investor_mult = 1.05
                    else:
                        investor_mult = 1.0

                    if unique_countries >= 8:
                        geo_mult = 1.25
                    elif unique_countries >= 5:
                        geo_mult = 1.15
                    elif unique_countries >= 3:
                        geo_mult = 1.10
                    elif unique_countries >= 2:
                        geo_mult = 1.05
                    else:
                        geo_mult = 1.0

                    final_score = base_score * investor_mult * geo_mult
                    company_scores[company] = final_score

            # Calculate percentiles
            scores = [score for score in company_scores.values() if
                      isinstance(score, (int, float)) and not np.isnan(score)]

            if len(scores) >= 2:
                percentile_thresholds = {
                    '50th': float(np.percentile(scores, 50)),
                    '80th': float(np.percentile(scores, 80))
                }

            return percentile_thresholds

        except Exception as e:
            logger.warning(f"Error calculating percentiles: {e}")
            return percentile_thresholds

    @staticmethod
    def calculate_consensus_multipliers(company_data: pd.DataFrame) -> Tuple[float, float]:
        """Calculate consensus multipliers based on investor and geographic breadth."""
        unique_investors = company_data[FETDataUtils.COLUMNS['excluded_by']].dropna().nunique()
        unique_countries = company_data[FETDataUtils.COLUMNS['investor_country']].dropna().nunique()

        # Investor breadth multiplier
        if unique_investors >= 20:
            investor_mult = 1.30
        elif unique_investors >= 10:
            investor_mult = 1.20
        elif unique_investors >= 5:
            investor_mult = 1.10
        elif unique_investors >= 2:
            investor_mult = 1.05
        else:
            investor_mult = 1.0

        # Geographic breadth multiplier
        if unique_countries >= 8:
            geo_mult = 1.25
        elif unique_countries >= 5:
            geo_mult = 1.15
        elif unique_countries >= 3:
            geo_mult = 1.10
        elif unique_countries >= 2:
            geo_mult = 1.05
        else:
            geo_mult = 1.0

        return investor_mult, geo_mult

    @staticmethod
    def calculate_row_score(row: pd.Series) -> float:
        """Calculate score for individual exclusion record."""
        # Category weight
        category = row.get('category_canonical', 'unspecified')
        category_weight = FETDataUtils.CATEGORY_WEIGHTS.get(category, 1.0)

        # Motivation weight
        motivation = row.get('motivation_canonical', 'unspecified')
        motivation_weight = FETDataUtils.MOTIVATION_WEIGHTS.get(motivation, 1.0)

        # Scope multiplier
        scope = row.get('scope_normalized', 'company')
        scope_mult = 1.15 if scope == 'sector' else 1.0

        # Recency multiplier
        years_ago = row.get('years_ago', 0)
        if years_ago <= 1:
            recency_mult = 1.0
        elif years_ago <= 2:
            recency_mult = 0.9
        elif years_ago <= 5:
            recency_mult = 0.8
        else:
            recency_mult = 0.7

        row_score = category_weight * motivation_weight * scope_mult * recency_mult
        return row_score

    @staticmethod
    def calculate_confidence_score(company_data: pd.DataFrame) -> float:
        """Calculate confidence score based on data completeness."""
        if company_data.empty:
            return 1.0

        total_records = len(company_data)
        unspecified_motivations = (company_data['motivation_canonical'] == 'unspecified').sum()
        unspecified_pct = (unspecified_motivations / total_records) * 100

        confidence = 1 - min(0.5, unspecified_pct / 200)
        return confidence