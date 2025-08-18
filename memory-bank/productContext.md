# GastroPro Product Manager - Product Context

## Problem Statement
E-commerce businesses frequently need to manage product data from multiple sources. Maintaining consistent product information across both local inventory databases and online product feeds is challenging and time-consuming when done manually.

## Solution
GastroPro Product Manager provides an automated solution for merging and synchronizing product data from local CSV files with online XML product feeds, creating a unified output that maintains the structure of the original CSV while incorporating valuable data from external sources.

In addition to XML feeds and CSV, the system can augment the catalog via multi-threaded web scraping to download additional products and fill missing attributes. Scraping is integrated into the same processing pipeline and follows the Parallel Processing Pattern for performance.

To further enhance data quality, the app uses a web-search-enabled LLM agent to improve or generate B2B-ready short and long descriptions and SEO metadata (SEO titulka, SEO popis, SEO kľúčové slová). The agent leverages a web search tool to gather missing context when product details are sparse, and relies on robust prompt engineering and parallel batch execution for efficiency and consistency.

The system also includes advanced product variant detection and difference extraction, allowing users to automatically identify related product variants and extract their differences (dimensions, power, volume, etc.) based on configurable rules.

## User Experience Goals
- **Simplicity**: Users should be able to complete the entire workflow in a few clicks
- **Visibility**: Clear feedback about the data processing status and results
- **Control**: Allow users to select which categories of products to include in the final output
- **Reliability**: Ensure consistent data formatting and prevent data loss
- **Efficiency**: Reduce the time required to update product listings across platforms

## Workflow
1. User loads a primary CSV file containing product data
2. User selects product categories to include in the final output
3. System automatically loads and processes configured XML feeds
4. Optionally performs multi-threaded web scraping to augment the catalog and fill missing fields
5. System merges the selected local data with the feed and scraped data
6. System enhances data with AI: generates/improves B2B short and long descriptions and SEO meta (title, description, keywords) using a web-search-enabled LLM
7. System identifies product variants and extracts differences based on configuration
8. User reviews the detected variants and extracted differences
9. System generates detailed reports of variant groups and differences
10. User saves the final CSV output with variant relationships, differences, and enhanced content

## Target Users
- E-commerce store administrators
- Product catalog managers
- Online marketplace sellers
- Inventory management personnel

