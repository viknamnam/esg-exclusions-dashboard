# 🛡️ FET Risk Intelligence Dashboard

A comprehensive ESG risk assessment platform that analyzes institutional investor exclusions to provide actionable business intelligence for engagement decisions.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Configuration](#configuration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

The FET (Financial Exclusion Tracker) Risk Intelligence Dashboard helps organizations assess ESG (Environmental, Social, Governance) risks by analyzing patterns in institutional investor exclusions. It provides risk scoring, operational recommendations, and detailed reporting to support informed business engagement decisions.

### Key Capabilities

- **Multi-factor risk scoring** with consensus analysis (40%), issue severity (30%), recent activity (20%), and scope impact (10%)
- **Intelligent company matching** with fuzzy search and partial name support
- **Operational playbooks** aligned with DNV's risk management framework
- **Automated translations** for foreign-language exclusion reasons
- **Comprehensive reporting** with PDF export capabilities
- **Real-time dashboard** with interactive data exploration

## ✨ Features

### 🔍 Advanced Search & Matching
- **Fuzzy matching** for company names with confidence scoring
- **Word-by-word search** for partial company name matching
- **Normalization engine** handling legal suffixes and variations
- **Debug tools** for search troubleshooting

### 📊 Enhanced Risk Assessment
- **Multi-factor scoring model** with transparent breakdowns
- **Three-tier risk levels**: Low Risk, Medium Risk, High Risk
- **Consensus strength analysis** across investors and countries
- **Historical trend analysis** with recency weighting
- **Sector vs. company-level scope detection**

### 💼 Business Intelligence
- **Operational playbooks** with specific guidance for each risk level
- **Compliance requirements** mapped to risk categories
- **Contract scope recommendations** with acceptable/restricted activities
- **Monitoring approaches** tailored to risk profiles

### 📈 Reporting & Export
- **Interactive dashboards** with filtering and drill-down capabilities
- **PDF report generation** with executive summaries
- **CSV data export** for further analysis
- **Translation summaries** and data quality indicators

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    FET Risk Intelligence System                  │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Layer (Streamlit)                                    │
│  ├── main_dashboard.py        (Entry point & search)           │
│  ├── dashboard_display.py     (UI components & rendering)      │
│  └── dashboard_config.py      (Styling & configuration)        │
├─────────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                          │
│  ├── risk_scoring.py          (Multi-factor risk assessment)   │
│  ├── report_generation.py     (PDF & export functionality)     │
│  └── data_utils.py           (Data processing utilities)       │
├─────────────────────────────────────────────────────────────────┤
│  Core Engine Layer                                             │
│  ├── fet_core3.py            (Main analysis engine)            │
│  ├── fet_recommendations.py   (DNV operational playbook)       │
│  ├── fet_translation.py       (Multi-language support)         │
│  └── fet_utils.py            (Foundational calculations)       │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                    │
│  └── Excel Database          (Standardized FET dataset)        │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Raw Excel Data → fet_utils.py → fet_core3.py → risk_scoring.py → dashboard_display.py
                      ↓              ↓              ↓                    ↓
              Normalization   Analysis Engine  Enhanced Scoring    User Interface
              Translation     Risk Assessment  Business Logic      Reporting
```

## 🚀 Installation

### Prerequisites

- **Python 3.8+**
- **pip** package manager
- **8GB+ RAM** (for large dataset processing)
- **Internet connection** (for translation services - optional)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fet-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   streamlit run main_dashboard.py
   ```

4. **Upload your FET dataset**
   - Use the file uploader in the web interface
   - Or place your Excel file as: `2024-095 FET - 2024 standardized dataset 241210.xlsx`

### Dependencies

```txt
streamlit>=1.28.0
pandas>=1.5.0
plotly>=5.15.0
openpyxl>=3.1.0
reportlab>=4.0.0
requests>=2.31.0
fuzzywuzzy[speedup]>=0.18.0
numpy>=1.24.0
```

### Optional Dependencies

For enhanced functionality:

```bash
# Translation services
export DEEPL_API_KEY="your-deepl-key"
export GOOGLE_TRANSLATE_API_KEY="your-google-key"

# API rate limiting
export FET_TRANSLATE_MAX="500"
```

## 📖 Usage

### Basic Workflow

1. **Launch the application**
   ```bash
   streamlit run main_dashboard.py
   ```

2. **Upload your dataset** (if not already present)
   - Click "Upload FET Excel Dataset"
   - Select your standardized FET Excel file
   - Wait for processing completion

3. **Search for companies**
   - Enter company name in the search box
   - Select from suggested matches
   - View comprehensive risk assessment

4. **Analyze results**
   - Review risk level and scoring breakdown
   - Read operational recommendations
   - Export reports as needed

### Advanced Features

#### Search Tips
- Use partial names: `"Shell"` instead of `"Royal Dutch Shell plc"`
- Try different spellings or abbreviations
- Remove legal suffixes for better matching
- Use the debug panel for troubleshooting

#### Risk Analysis
- **Enhanced scoring breakdown** shows factor contributions
- **Warning flags** highlight specific concerns
- **Historical analysis** shows exclusion patterns over time
- **Consensus analysis** reveals geographic and institutional breadth

#### Export Options
- **PDF reports** for executive summaries
- **CSV exports** for data analysis
- **JSON exports** for system integration

## 📁 File Structure

### Core Application Files

```
fet-dashboard/
├── main_dashboard.py              # 🚪 Main application entry point
├── dashboard_config.py            # ⚙️  UI configuration and styling
├── dashboard_display.py           # 🖥️  Dashboard components and rendering
├── risk_scoring.py               # 📊 Enhanced risk assessment logic
├── data_utils.py                 # 🔧 Data loading and processing utilities
├── report_generation.py          # 📋 PDF and export functionality
├── fet_core3.py                  # 🎯 Core FET analysis engine
├── fet_recommendations.py         # 💼 DNV operational playbook
├── fet_translation.py            # 🌍 Multi-language translation support
├── fet_utils.py                  # 🔨 Foundational calculations and utilities
├── fet_dashboard5.py             # 📜 Original monolithic dashboard (deprecated)
└── requirements.txt              # 📦 Python dependencies
```

### Data and Cache Files

```
fet-dashboard/
├── 2024-095 FET - 2024 standardized dataset 241210.xlsx  # 📊 Main dataset
├── cache/                        # 💾 Application cache directory
│   ├── company_lookup.pkl        # 🏢 Preprocessed company data
│   └── percentile_thresholds.pkl # 📈 Risk scoring thresholds
└── motivation_translation_cache.json  # 🌐 Translation cache
```

### Generated Files

```
fet-dashboard/
├── .streamlit/                   # 🎨 Streamlit configuration
│   └── config.toml              
├── logs/                        # 📝 Application logs
│   └── fet_dashboard.log        
└── exports/                     # 💾 Generated reports
    ├── company_risk_report.pdf  
    └── company_exclusions.csv   
```

## ⚙️ Configuration

### Application Settings

Key configuration options in `dashboard_config.py`:

- **Page layout**: Wide layout with collapsed sidebar
- **Caching**: Streamlit caching for performance
- **Styling**: Custom CSS for professional appearance
- **Session state**: Persistent application state management

### Risk Scoring Configuration

Risk thresholds in `fet_utils.py`:

```python
CATEGORY_WEIGHTS = {
    'climate': 3.0,
    'human rights': 2.5,
    'governance': 2.5,
    'business practices': 1.5,
    'cannabis': 0.8,
    'unspecified': 1.0
}
```

### Translation Configuration

Optional translation services in `fet_translation.py`:

- **DeepL API**: High-quality translation for European languages
- **Google Translate**: Broad language support
- **Local cache**: Prevents redundant API calls
- **Rate limiting**: Prevents API quota exhaustion

## 🔧 Development

### Module Organization

#### **Frontend Layer**
- `main_dashboard.py`: Application orchestration and search interface
- `dashboard_display.py`: UI components and data visualization  
- `dashboard_config.py`: Styling, configuration, and session management

#### **Business Logic Layer**  
- `risk_scoring.py`: Multi-factor risk assessment with dashboard enhancements
- `report_generation.py`: PDF generation and export functionality
- `data_utils.py`: Data loading, caching, and utility functions

#### **Core Engine Layer**
- `fet_core3.py`: Main analysis engine with company matching and risk calculation
- `fet_recommendations.py`: DNV operational playbook and recommendation logic
- `fet_translation.py`: Translation management with multiple backend support
- `fet_utils.py`: Foundational data processing and calculation utilities

### Key Design Patterns

#### **Layered Architecture**
```python
# Clean separation of concerns
UI Layer → Business Logic → Core Engine → Data Layer
```

#### **Caching Strategy**
```python
# Multiple caching levels
@st.cache_resource  # Application-level caching
@st.cache_data      # Data-level caching
Local JSON cache    # Translation caching
```

#### **Error Handling**
```python
# Graceful degradation
try:
    # Advanced functionality
except ImportError:
    # Fallback to basic functionality
```

### Adding New Features

#### **New Risk Factors**
1. Add factor calculation in `risk_scoring.py`
2. Update scoring weights and thresholds
3. Add UI components in `dashboard_display.py`
4. Update documentation and tests

#### **New Data Sources**
1. Add loading logic in `data_utils.py`
2. Update column mappings in `fet_utils.py`
3. Add data validation and processing
4. Update cache invalidation logic

#### **New Export Formats**
1. Add generation logic in `report_generation.py`
2. Update UI buttons in `dashboard_display.py`
3. Add format-specific configuration options
4. Update file handling and downloads

### Testing

#### **Manual Testing Checklist**
- [ ] Database loading (local file and upload)
- [ ] Company search (exact, fuzzy, partial matches)
- [ ] Risk assessment (all three risk levels)
- [ ] PDF report generation
- [ ] CSV export functionality
- [ ] Translation services (if configured)
- [ ] Error handling (invalid files, network issues)

#### **Performance Testing**
- [ ] Large dataset loading (10k+ records)
- [ ] Search response time (<2 seconds)
- [ ] Dashboard rendering performance
- [ ] Memory usage with concurrent users
- [ ] Cache effectiveness

## 🚨 Troubleshooting

### Common Issues

#### **Database Loading Errors**

**Problem**: "Failed to load database" error
```
❌ Failed to load database: Missing required columns
```

**Solutions**:
1. Verify Excel file format matches expected structure
2. Check column names match `fet_utils.COLUMNS` mapping
3. Ensure file is not corrupted or password-protected
4. Try uploading file via web interface instead of local placement

#### **Search Not Finding Companies**

**Problem**: Known companies not appearing in search results

**Solutions**:
1. Use shorter search terms (e.g., "Shell" vs "Royal Dutch Shell")
2. Try removing legal suffixes (Inc, Corp, Ltd)
3. Check spelling and try alternative company names
4. Use the debug panel to see search processing details

#### **Risk Scoring Inconsistencies**

**Problem**: Risk scores seem incorrect or inconsistent

**Solutions**:
1. Check data quality and completeness
2. Verify translation services are working correctly
3. Review category and motivation mappings
4. Check for data preprocessing issues

#### **Performance Issues**

**Problem**: Slow loading or search response times

**Solutions**:
1. Clear Streamlit cache: Delete `.streamlit/` and `cache/` directories
2. Restart the application
3. Check system memory usage
4. Reduce dataset size for testing

#### **Translation Errors**

**Problem**: Foreign language content not translating

**Solutions**:
1. Check API keys are set correctly
2. Verify internet connectivity
3. Review rate limiting settings
4. Check translation cache for errors

### Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `DB_LOAD_FAIL` | Database loading failed | Check file format and permissions |
| `SEARCH_TIMEOUT` | Search operation timed out | Reduce search complexity or restart |
| `TRANSLATION_ERROR` | Translation service error | Check API keys and connectivity |
| `EXPORT_FAIL` | Report export failed | Check disk space and permissions |
| `CACHE_CORRUPT` | Cache corruption detected | Clear cache directory |

### Debug Mode

Enable detailed logging by setting environment variable:

```bash
export FET_DEBUG=true
streamlit run main_dashboard.py
```

This enables:
- Detailed search debugging
- Performance timing information
- Translation service diagnostics
- Cache operation logging

### Performance Optimization

#### **For Large Datasets (50k+ records)**:
1. Increase system memory allocation
2. Enable database indexing
3. Use data sampling for development
4. Consider database backend migration

#### **For Multiple Users**:
1. Deploy with proper WSGI server
2. Configure Redis for shared caching
3. Load balance across multiple instances
4. Monitor resource usage

## 🤝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```
4. **Make changes and test thoroughly**
5. **Submit a pull request**

### Code Standards

- **Python**: Follow PEP 8 style guidelines
- **Documentation**: Include docstrings for all functions
- **Type hints**: Use type annotations where appropriate
- **Error handling**: Implement graceful error handling
- **Testing**: Include unit tests for new functionality

### Pull Request Process

1. **Update documentation** for any new features
2. **Add tests** covering new functionality
3. **Ensure all tests pass**
4. **Update README** if necessary
5. **Request review** from maintainers

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For questions, issues, or feature requests:

1. **Check the troubleshooting section** above
2. **Search existing issues** in the repository
3. **Create a new issue** with detailed description
4. **Include relevant error messages** and logs
5. **Provide system information** (OS, Python version, etc.)

## 🙏 Acknowledgments

- **DNV** for the operational playbook framework
- **FET Initiative** for the exclusion database
- **Streamlit Community** for the excellent web framework
- **Contributors** who have helped improve this system

---

**Version**: 2.1.0  
**Last Updated**: December 2024  
**Maintainer**: FET Dashboard Team