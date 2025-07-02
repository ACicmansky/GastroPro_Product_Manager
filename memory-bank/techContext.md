# GastroPro Product Manager - Technical Context

## Technology Stack
- **Python 3.x**: Core programming language
- **PyQt5**: GUI framework for desktop application
- **Pandas**: Data manipulation library for CSV processing
- **Requests**: HTTP client for XML feed fetching
- **ElementTree**: XML parsing library (built into Python standard library)

## Development Setup
- **Environment**: Windows operating system
- **IDE**: Compatible with standard Python IDEs
- **Version Control**: Git repository

## Technical Constraints
- **Performance**: Must handle CSV files with potentially thousands of products
- **Memory Usage**: Efficient memory management for large datasets
- **Error Handling**: Robust error handling for network failures and malformed data
- **Encoding**: Support for UTF-8 and other encodings common in CSV files

## Dependencies
- Python 3.x
- PyQt5
- pandas
- requests

## Data Structures
1. **Configuration (JSON)**:
   - App settings
   - Data source configurations
   - Output settings

2. **Local CSV Structure**:
   - Product ID
   - Product name
   - Price
   - Description
   - "Hlavna kategória" (Main category) - used for filtering
   - Other product attributes

3. **XML Feed Structure** (Typical):
   - Product entries
   - Product identifiers
   - Product details (name, price, description, etc.)
   - Category information

4. **Internal Data Representation**:
   - Pandas DataFrames for both local and processed data
   - Dictionary mappings for configuration

## File Operations
- Reading/writing CSV files
- Parsing XML from URLs
- Managing configuration JSON

## Network Operations
- HTTP requests to XML feed URLs
- Error handling for network failures
- Timeout handling
