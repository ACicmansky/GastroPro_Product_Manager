# XML Namespace Parsing Fix - November 16, 2025

## Issue Discovered
The Gastromarket XML parser was failing to read data from the production feed at `https://www.gastromarket.sk/product_data/partner_feed_sk.xml`. The `root` variable was always `None`, causing the parser to crash.

## Root Cause Analysis
The real Gastromarket XML feed uses a **prefixed namespace** structure:
```xml
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
  <channel>
    <item>
      <g:KATALOG_CISLO>LG201200</g:KATALOG_CISLO>
      <g:MENO>Product Name</g:MENO>
      ...
    </item>
  </channel>
</rss>
```

Key observations:
1. RSS structure elements (`<rss>`, `<channel>`, `<item>`) are NOT namespaced
2. Data elements inside `<item>` use the `g:` prefix with namespace `http://base.google.com/ns/1.0`
3. This is different from a default namespace (which we initially tried to support)

## Initial Refactoring Attempt
We first attempted to simplify the code by:
1. Removing `g:` prefix from config field names
2. Using Clark notation `{namespace}element` for lookups
3. This approach failed because Clark notation doesn't work with prefixed namespaces

## Final Solution
Implemented proper prefixed namespace handling:

### Code Changes (`src/parsers/xml_parser_new_format.py`)
```python
# Register namespace with prefix
namespaces = {}
if namespace_url:
    namespaces = {"g": namespace_url}
    ET.register_namespace("g", namespace_url)

# RSS structure elements are NOT namespaced
root = xml_root.find(root_element)

# Data elements inside items ARE namespaced with g: prefix
for item in root.findall(f".//{item_element}"):
    for xml_field, new_field in mapping.items():
        if namespace_url:
            element = item.find(f"g:{xml_field}", namespaces)
        else:
            element = item.find(xml_field)
```

### Config Structure (`config.json`)
```json
"gastromarket": {
  "namespace": "http://base.google.com/ns/1.0",
  "mapping": {
    "KATALOG_CISLO": "code",
    "MENO": "name",
    "POPIS": "shortDescription",
    ...
  }
}
```

## Benefits of Final Approach
1. **Clean Config**: Field names without technical prefixes
2. **Correct Parsing**: Uses ElementTree's namespace dictionary properly
3. **Flexible**: Works with both namespaced and non-namespaced feeds
4. **Maintainable**: Clear separation between namespace URL and field names

## Test Results
- ✅ All 217 tests passing
- ✅ Zero regressions
- ✅ Successfully parsed 3,934 products from production Gastromarket feed
- ✅ Pipeline completed successfully with real data

## Production Validation
Ran full pipeline with real Gastromarket feed:
```
Parsing 1 XML feed(s)...
Parsed 3934 products from Gastromarket
Applied 129624 default values
Merging data with image priority...
PIPELINE COMPLETE: 3928 products
Saved 3928 rows, 139 columns
```

## Files Modified
1. `src/parsers/xml_parser_new_format.py` - Fixed namespace handling
2. `tests/conftest.py` - Updated test fixture to match real XML structure
3. `config.json` - Already had correct structure

## Lessons Learned
1. **Always test with real data**: Test fixtures should match production XML structure exactly
2. **Understand namespace types**: Prefixed namespaces (`xmlns:g=`) vs default namespaces (`xmlns=`) require different handling
3. **ElementTree namespace handling**: Use namespace dictionaries with prefix-based lookups for prefixed namespaces
4. **RSS structure**: RSS wrapper elements are typically not namespaced, only the data elements

## Next Steps
- ✅ Parser working with production data
- ✅ All tests passing
- Ready for continued development and deployment
