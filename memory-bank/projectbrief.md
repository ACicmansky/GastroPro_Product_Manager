# GastroPro Product Manager - Project Brief

## Project Overview
GastroPro Product Manager is a Python desktop application designed to manipulate and merge product data for e-commerce. The application allows users to merge local CSV data with online XML feeds to create a structured output CSV file.

## Core Requirements
1. CSV Data Import: Allow users to upload a main CSV file containing product data
2. Category Selection: Enable users to select products from the main CSV by filtering categories (field: "Hlavna kategória")
3. XML Feed Processing: Load, parse, and process online XML feeds to enhance product data
4. Output Generation: Create and save a final CSV file that maintains the structure of the local CSV but incorporates data from XML feeds

## Project Goals
- Streamline product data management for e-shop operators
- Automate the merging process between local and online data sources
- Provide a user-friendly interface for product data manipulation
- Ensure data integrity throughout the process

## Core Functionality
- File import/export capabilities
- Data filtering by product categories
- XML feed integration
- Data transformation and merging

## Technical Requirements
- Python desktop application with PyQt5 GUI
- Support for CSV and XML data formats
- Configuration management
- Error handling and validation
