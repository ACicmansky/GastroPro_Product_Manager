# GastroPro Product Manager - Project Brief

## Project Overview
GastroPro Product Manager is a Python desktop application designed to manipulate and merge product data for e-commerce. The application allows users to merge local CSV data with online XML feeds, optionally augment the catalog via multi-threaded web scraping, and enhance content with an AI agent (with web search grounding) to generate B2B-ready descriptions and SEO metadata, producing a structured output CSV file.

## Core Requirements
1. CSV Data Import: Allow users to upload a main CSV file containing product data
2. Category Selection: Enable users to select products from the main CSV by filtering categories (field: "Hlavna kategória")
3. XML Feed Processing: Load, parse, and process online XML feeds to enhance product data
4. Web Scraping: Multi-threaded scraping to download additional products and fill missing attributes (optional)
5. AI Enhancement: Improve or generate B2B short/long descriptions and SEO metadata (title/description/keywords) using an LLM with web search grounding
6. Output Generation: Create and save a final CSV file that maintains the structure of the local CSV but incorporates data from feeds/scraping/AI

## Project Goals
- Streamline product data management for e-shop operators
- Automate the merging process between local and online data sources
- Provide a user-friendly interface for product data manipulation
- Ensure data integrity throughout the process

## Core Functionality
- File import/export capabilities
- Data filtering by product categories
- XML feed integration
- Multi-threaded web scraping integration
- AI-generated B2B descriptions and SEO metadata with web search grounding
- Data transformation and merging

## Technical Requirements
- Python desktop application with PyQt5 GUI
- Support for CSV, XML, and web scraping data sources
- Configuration management
- Error handling and validation
- Parallel processing with ThreadPoolExecutor and API quota management (calls/tokens)
