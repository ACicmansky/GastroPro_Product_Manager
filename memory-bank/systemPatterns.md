# GastroPro Product Manager - System Patterns

## Architecture Overview
GastroPro Product Manager follows a modular architecture with clear separation of concerns:

```
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  User         │     │  Data           │     │  Product         │     │  Output       │
│  Interface    │◄────┤  Processing     │◄────┤  Variant         │◄────┤  Generation   │
└───────────────┘     └─────────────────┘     └──────────────────┘     └───────────────┘
        │                     │                        │                       │
        ▼                     ▼                        ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  Input        │     │  Data           │     │  Variant         │     │  Config       │
│  Handling     │     │  Storage        │     │  Configuration   │     │  Management   │
└───────────────┘     └─────────────────┘     └──────────────────┘     └───────────────┘
```
```

## Design Patterns
1. **MVC Pattern**:
   - **Model**: Data structures for product information
   - **View**: PyQt5-based GUI components
   - **Controller**: Application logic in the MainWindow class

2. **Strategy Pattern**:
   - Used in variant detection with different similarity comparison strategies
   - Configurable extraction rules for different product categories

2. **Configuration Management Pattern**:
   - External JSON configuration file
   - Runtime config updates
   - Default configuration fallback

3. **Data Processing Pipeline**:
   - Input stage: CSV loading and preparation
   - Processing stage: Category filtering, mapping, and XML feed integration
   - Variant Detection: Product grouping and difference extraction
   - Output stage: CSV generation and report export

4. **Variant Detection System**:
   - Product similarity analysis using name patterns
   - Configurable extraction of differences (dimensions, power, etc.)
   - Category-specific extraction rules
   - Human-readable reporting of variant groups

4. **Category Mapping System**:
   - Universal JSON array format for mapping definitions
   - Centralized mapping functions for consistent application
   - User-controlled application at export time
   - Detailed logging of mapping operations

## Component Relationships
- **MainWindow Class**: Core controller that manages the application flow
- **ProductVariantMatcher**: Handles variant detection and difference extraction
- **Utils Module**: Handles file operations, configuration, and external data fetching
- **Data Models**: Pandas DataFrames for data manipulation
- **Config Files**: External configurations for app settings, data sources, and variant extraction rules

## Technical Decisions
1. **PyQt5 for GUI**: Provides robust desktop application interface
2. **Pandas for Data Manipulation**: Efficient handling of tabular data
3. **JSON for Configuration**: Human-readable and easily modifiable
4. **ElementTree for XML Parsing**: Standard library solution for XML processing

## Future Considerations
- Potential for plugin architecture to support additional data formats
- Database integration for persistent storage
- Caching mechanism for XML feeds to reduce network requests
