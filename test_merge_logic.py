import pandas as pd
from utils import merge_dataframes

def test_conditional_merge():
    # Create test data
    main_df = pd.DataFrame({
        'Kat. číslo': ['001', '002', '003'],
        'Názov tovaru': ['Product A', 'Product B', 'Product C'],
        'Krátky popis': ['', 'AI enhanced description', ''],
        'Dlhý popis': ['', 'AI enhanced long description', ''],
        'Spracovane AI': ['', 'TRUE', 'FALSE']
    })
    
    feed_df = pd.DataFrame({
        'Kat. číslo': ['001', '002', '003'],
        'Krátky popis': ['Feed description for A', 'Feed description for B', 'Feed description for C'],
        'Dlhý popis': ['Feed long description for A', 'Feed long description for B', 'Feed long description for C']
    })
    
    final_cols = ['Kat. číslo', 'Názov tovaru', 'Krátky popis', 'Dlhý popis', 'Spracovane AI']
    
    # Test merge
    result_df = merge_dataframes(main_df, [feed_df], final_cols)
    
    print("Result DataFrame:")
    print(result_df)
    
    # Verify results
    # Product A (not AI enhanced) should get feed descriptions
    assert result_df[result_df['Kat. číslo'] == '001']['Krátky popis'].iloc[0] == 'Feed description for A'
    assert result_df[result_df['Kat. číslo'] == '001']['Dlhý popis'].iloc[0] == 'Feed long description for A'
    
    # Product B (AI enhanced) should keep AI descriptions
    assert result_df[result_df['Kat. číslo'] == '002']['Krátky popis'].iloc[0] == 'AI enhanced description'
    assert result_df[result_df['Kat. číslo'] == '002']['Dlhý popis'].iloc[0] == 'AI enhanced long description'
    
    # Product C (not AI enhanced) should get feed descriptions
    assert result_df[result_df['Kat. číslo'] == '003']['Krátky popis'].iloc[0] == 'Feed description for C'
    assert result_df[result_df['Kat. číslo'] == '003']['Dlhý popis'].iloc[0] == 'Feed long description for C'
    
    print("All tests passed!")

if __name__ == "__main__":
    test_conditional_merge()
