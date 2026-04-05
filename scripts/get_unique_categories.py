import json
import os

def extract_unique_new_categories():
    """
    Loads categories.json, extracts all unique 'newCategory' values,
    and saves them (one per line) to unique_categories.txt.
    """
    # Define paths relative to the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'categories.json')
    output_path = os.path.join(base_dir, 'unique_categories.txt')
    
    if not os.path.exists(json_path):
        print(f"Error: Could not find {json_path}")
        return
        
    try:
        # Load the JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Extract unique newCategory values
        unique_categories = set()
        for entry in data:
            new_cat = entry.get("newCategory")
            if new_cat:
                unique_categories.add(new_cat)
                
        # Sort the categories alphabetically for easier reading
        sorted_categories = sorted(list(unique_categories))
        
        # Save to text file
        with open(output_path, 'w', encoding='utf-8') as f:
            for cat in sorted_categories:
                f.write(cat + '\n')
                
        print(f"Successfully saved {len(sorted_categories)} unique categories to {output_path}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    extract_unique_new_categories()
