import json
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
import re
from collections import defaultdict
import os
import requests
import time

# Configure logging
logger = logging.getLogger(__name__)


class TranslationManager:
    """
    Seamless translator for Motivation / Category fields with:
    - Heuristic language check (no extra deps)
    - Optional DeepL / Google backends if API keys exist
    - Local JSON cache to avoid repeated calls
    """

    def __init__(self, app_dir: Path):
        self.cache_path = app_dir / "motivation_translation_cache.json"
        self.cache = self._load_cache()

        # Backends: decide what's available from env
        self.use_deepl = bool(os.environ.get("DEEPL_API_KEY"))
        self.use_google = bool(os.environ.get("GOOGLE_TRANSLATE_API_KEY"))

        # Add rate limiting
        self.last_api_call = 0
        self.min_interval = 0.1  # Minimum seconds between API calls

        # Enhanced error tracking
        self.api_errors = 0
        self.max_errors = 5  # Stop after 5 consecutive errors

        # Optional: limit external calls
        self.max_calls = int(os.environ.get("FET_TRANSLATE_MAX", "500"))
        self.calls_made = 0

        # Enhanced seed dictionary for frequent phrases (extend as you learn your data)
        self.seed_map = {
            # Norwegian/Danish/Swedish
            "menneskerettigheter": "human rights",
            "korrupsjon": "corruption",
            "arbeidsrettigheter": "labour rights",
            "barnearbeid": "child labour",
            "tvangsarbeid": "forced labour",
            "termisk kul": "thermal coal",
            "fossile brensler": "fossil fuels",
            "olje og gass": "oil and gas",
            "klimaendringer": "climate change",
            "våpen": "weapons",
            "tobakk": "tobacco",

            # French
            "droits de l'homme": "human rights",
            "corruption": "corruption",
            "travail des enfants": "child labour",
            "travail forcé": "forced labour",
            "charbon thermique": "thermal coal",
            "charbon": "coal",
            "pétrole et gaz": "oil and gas",
            "pétrole": "oil",
            "gaz": "gas",
            "changement climatique": "climate change",
            "armes": "weapons",
            "tabac": "tobacco",

            # German
            "menschenrechte": "human rights",
            "korruption": "corruption",
            "kinderarbeit": "child labour",
            "zwangsarbeit": "forced labour",
            "thermische kohle": "thermal coal",
            "kohle": "coal",
            "öl und gas": "oil and gas",
            "erdöl": "oil",
            "klimawandel": "climate change",
            "waffen": "weapons",
            "tabak": "tobacco",

            # Dutch
            "mensenrechten": "human rights",
            "corruptie": "corruption",
            "kinderarbeid": "child labour",
            "gedwongen arbeid": "forced labour",
            "thermische kolen": "thermal coal",
            "steenkool": "coal",
            "kolen": "coal",
            "olie en gas": "oil and gas",
            "klimaatverandering": "climate change",
            "wapens": "weapons",
            "tabak": "tobacco",

            # Spanish
            "derechos humanos": "human rights",
            "corrupción": "corruption",
            "trabajo infantil": "child labour",
            "trabajo forzoso": "forced labour",
            "carbón térmico": "thermal coal",
            "carbón": "coal",
            "petróleo y gas": "oil and gas",
            "cambio climático": "climate change",
            "armas": "weapons",
            "tabaco": "tobacco",

            # Italian
            "diritti umani": "human rights",
            "corruzione": "corruption",
            "lavoro minorile": "child labour",
            "lavoro forzato": "forced labour",
            "carbone termico": "thermal coal",
            "carbone": "coal",
            "petrolio e gas": "oil and gas",
            "cambiamento climatico": "climate change",
            "armi": "weapons",
            "tabacco": "tobacco",

            # Common abbreviations and mixed cases
            "co2": "carbon dioxide",
            "ghg": "greenhouse gas",
            "esg": "environmental social governance",
        }

    # ----------------- Public API -----------------
    def translate_series(self, s: pd.Series) -> pd.Series:
        """Translate a pandas Series of text values"""
        return s.astype(str).fillna("").apply(self.translate_text)

    def translate_text(self, text: str) -> str:
        """Translate a single text value"""
        t = str(text).strip()
        if not t or t.lower() in ['nan', 'none', '']:
            return ""

        # 1) Cached?
        if t in self.cache:
            return self.cache[t]

        # Check if we've hit too many errors
        if self.api_errors >= self.max_errors:
            logger.warning("Translation API temporarily disabled due to errors")
            return t

        # Apply rate limiting
        time_since_last = time.time() - self.last_api_call
        if time_since_last < self.min_interval:
            time.sleep(self.min_interval - time_since_last)

        # 2) Seed dictionary (case-insensitive contains)
        mapped = self._seed_lookup(t)
        if mapped:
            self.cache[t] = mapped
            self._persist()
            return mapped

        # 3) Heuristic: looks English-ish? then return as is
        if not self._looks_foreign(t):
            self.cache[t] = t
            self._persist()
            return t

        # 4) Online translation (optional)
        translated = self._translate_online(t)
        if translated and translated != t:
            self.cache[t] = translated
            self._persist()
            return translated

        # 5) Fallback: return original
        self.cache[t] = t
        self._persist()
        return t

    # ----------------- Helper Methods -----------------
    def _looks_foreign(self, s: str) -> bool:
        """Heuristic to detect if text looks foreign"""
        # Check for non-ASCII characters (accented characters, etc.)
        if any(ord(ch) > 127 for ch in s):
            return True

        # Check for common non-English function words
        tokens = re.findall(r"[A-Za-zÀ-ÿ']+", s.lower())

        # Common function words from major European languages
        NON_EN = {
            # German
            "und", "der", "die", "das", "mit", "für", "gegen", "wegen", "von", "zu", "im", "am",
            # French
            "et", "la", "le", "des", "aux", "pour", "contre", "de", "du", "dans", "sur", "avec",
            # Spanish
            "y", "de", "el", "los", "las", "por", "con", "en", "del", "al", "para",
            # Italian
            "e", "di", "il", "la", "lo", "gli", "le", "per", "con", "in", "del", "alla",
            # Dutch
            "en", "van", "het", "de", "voor", "met", "op", "aan", "door", "bij",
            # Norwegian/Danish/Swedish
            "og", "av", "til", "for", "med", "på", "i", "som", "det", "er"
        }

        return any(tok in NON_EN for tok in tokens)

    def _seed_lookup(self, s: str) -> str:
        """Look up text in seed dictionary (case-insensitive substring matching)"""
        s_lower = s.lower()

        # First try exact matches
        if s_lower in self.seed_map:
            return self.seed_map[s_lower]

        # Then try substring matches (for compound phrases)
        for foreign_key, english_value in self.seed_map.items():
            if foreign_key in s_lower:
                return english_value

        return ""

    def _translate_online(self, s: str) -> str:
        """Enhanced online translation with better error handling"""
        if self.calls_made >= self.max_calls or self.api_errors >= self.max_errors:
            return ""

        try:
            self.last_api_call = time.time()

            if self.use_deepl:
                result = self._translate_deepl(s)
                if result:
                    self.api_errors = 0  # Reset error counter on success
                    return result
            elif self.use_google:
                result = self._translate_google(s)
                if result:
                    self.api_errors = 0  # Reset error counter on success
                    return result

        except Exception as e:
            self.api_errors += 1
            logger.warning(f"Translation API error #{self.api_errors}: {e}")

        return ""

    def _translate_deepl(self, text: str) -> str:
        """Translate using DeepL API with retry logic"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                auth_key = os.environ["DEEPL_API_KEY"]
                is_free = auth_key.endswith(":fx")
                base_url = "https://api-free.deepl.com" if is_free else "https://api.deepl.com"

                response = requests.post(
                    f"{base_url}/v2/translate",
                    data={
                        "text": text,
                        "target_lang": "EN",
                        "source_lang": "auto"
                    },
                    headers={"Authorization": f"DeepL-Auth-Key {auth_key}"},
                    timeout=10
                )

                if response.ok:
                    self.calls_made += 1
                    data = response.json()
                    translated = data["translations"][0]["text"]
                    return translated.strip()
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"DeepL API error: {response.status_code} - {response.text}")
                    break

            except requests.exceptions.Timeout:
                logger.warning(f"DeepL timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    continue
            except Exception as e:
                logger.warning(f"DeepL translation error on attempt {attempt + 1}: {e}")
                break

        return ""

    def _translate_google(self, text: str) -> str:
        """Translate using Google Translate API"""
        try:
            api_key = os.environ["GOOGLE_TRANSLATE_API_KEY"]

            response = requests.post(
                f"https://translation.googleapis.com/language/translate/v2?key={api_key}",
                json={
                    "q": text,
                    "target": "en",
                    "format": "text"
                },
                timeout=10
            )

            if response.ok:
                self.calls_made += 1
                data = response.json()
                translated = data["data"]["translations"][0]["translatedText"]
                return translated.strip()

        except Exception as e:
            logger.warning(f"Google Translate error: {e}")

        return ""

    def _load_cache(self) -> dict:
        """Load translation cache from disk"""
        try:
            if self.cache_path.exists():
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load translation cache: {e}")
        return {}

    def _persist(self):
        """Persist translation cache to disk"""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist translation cache: {e}")

    def get_stats(self) -> dict:
        """Get translation statistics for debugging"""
        total_cached = len(self.cache)
        foreign_detected = sum(1 for k, v in self.cache.items() if k != v)

        return {
            'total_cached': total_cached,
            'foreign_translations': foreign_detected,
            'api_calls_made': self.calls_made,
            'api_calls_remaining': max(0, self.max_calls - self.calls_made),
            'deepl_available': self.use_deepl,
            'google_available': self.use_google,
            'seed_terms': len(self.seed_map)
        }