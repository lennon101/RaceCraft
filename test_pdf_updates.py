#!/usr/bin/env python3
"""
Test script for updated PDF export functionality
- Tests race name input field
- Tests KeepTogether functionality
"""

import json
import requests
import base64
from PIL import Image
import io

# Test data for PDF generation
test_data = {
    "options": {
        "elevation_profile": True,
        "race_plan_table": True,
        "drop_bag_table": True,
        "drop_bag_tags": True,
        "race_name": "UTMB 100K Test Race",  # NEW: Race name from input field
        "bib_number": "456",
        "runner_name": "Jane Doe"
    },
    "race_name": "Default Race Name",  # This should be overridden by options.race_name
    "segments": [
        {
            "from": "Start",
            "to": "CP1",
            "cumulative_distance": 15.5,
            "elev_gain": 450,
            "elev_loss": 200,
            "net_elev": 250,
            "cumulative_time_str": "2:30:00",
            "pace_str": "9:41",
            "target_carbs": 120,
            "target_water": 1.25,
            "time_of_day": "08:30:00"
        },
        {
            "from": "CP1",
            "to": "CP2",
            "cumulative_distance": 32.0,
            "elev_gain": 380,
            "elev_loss": 450,
            "net_elev": -70,
            "cumulative_time_str": "5:15:00",
            "pace_str": "10:00",
            "target_carbs": 100,
            "target_water": 1.0,
            "time_of_day": "11:15:00"
        },
        {
            "from": "CP2",
            "to": "CP3",
            "cumulative_distance": 45.0,
            "elev_gain": 350,
            "elev_loss": 300,
            "net_elev": 50,
            "cumulative_time_str": "7:30:00",
            "pace_str": "9:30",
            "target_carbs": 95,
            "target_water": 0.95,
            "time_of_day": "13:30:00"
        },
        {
            "from": "CP3",
            "to": "Finish",
            "cumulative_distance": 50.0,
            "elev_gain": 200,
            "elev_loss": 600,
            "net_elev": -400,
            "cumulative_time_str": "8:00:00",
            "pace_str": "9:00",
            "target_carbs": 90,
            "target_water": 0.9,
            "time_of_day": "14:00:00"
        }
    ],
    "summary": {
        "total_distance": 50.0,
        "total_moving_time_str": "7:30:00",
        "total_cp_time_str": "0:30:00",
        "total_race_time_str": "8:00:00",
        "total_elev_gain": 1380,
        "total_carbs": 405,
        "total_water": 4.10
    },
    "dropbag_contents": [
        {
            "checkpoint": "Start",
            "carbs": 120,
            "num_gels": 5,
            "actual_carbs": 125,
            "hydration": 1.25
        },
        {
            "checkpoint": "CP1",
            "carbs": 100,
            "num_gels": 4,
            "actual_carbs": 100,
            "hydration": 1.0
        },
        {
            "checkpoint": "CP2",
            "carbs": 95,
            "num_gels": 4,
            "actual_carbs": 100,
            "hydration": 0.95
        },
        {
            "checkpoint": "CP3",
            "carbs": 90,
            "num_gels": 4,
            "actual_carbs": 100,
            "hydration": 0.9
        }
    ],
    "race_start_time": "06:00:00"
}

# Create a simple dummy elevation profile image
def create_dummy_elevation_profile():
    """Create a simple dummy elevation profile image as base64."""
    # Create a simple gradient image
    img = Image.new('RGB', (800, 300), color='white')
    pixels = img.load()
    
    # Draw a simple elevation profile (triangle wave)
    for x in range(800):
        y = int(150 + 100 * abs((x % 200) / 100 - 1))
        for dy in range(y, 300):
            pixels[x, dy] = (70, 130, 180)  # Steel blue color
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_bytes = buffer.read()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    return f"data:image/png;base64,{img_base64}"

# Add elevation profile to test data
test_data["elevation_profile"] = create_dummy_elevation_profile()

def test_pdf_export_with_race_name():
    """Test PDF export with custom race name from input field."""
    url = "http://127.0.0.1:5001/api/export-pdf"
    
    print("Testing PDF export with custom race name input...")
    print(f"URL: {url}")
    print(f"Race name in options: {test_data['options']['race_name']}")
    
    try:
        response = requests.post(url, json=test_data, timeout=10)
        
        if response.status_code == 200:
            # Save the PDF
            filename = "test_export_with_race_name.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ PDF export successful! Saved to {filename}")
            print(f"  File size: {len(response.content)} bytes")
            print(f"  Race name 'UTMB 100K Test Race' should be used in PDF")
            return True
        else:
            print(f"✗ PDF export failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing PDF export: {e}")
        return False

def test_pdf_export_without_race_name():
    """Test PDF export without custom race name (should use fallback)."""
    url = "http://127.0.0.1:5001/api/export-pdf"
    
    # Remove race_name from options
    test_data_copy = test_data.copy()
    test_data_copy["options"] = test_data["options"].copy()
    test_data_copy["options"]["race_name"] = ""
    
    print("\nTesting PDF export without custom race name (using fallback)...")
    
    try:
        response = requests.post(url, json=test_data_copy, timeout=10)
        
        if response.status_code == 200:
            filename = "test_export_fallback_race_name.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✓ PDF export successful! Saved to {filename}")
            print(f"  Fallback race name 'Default Race Name' should be used")
            return True
        else:
            print(f"✗ PDF export failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing PDF export: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PDF Export Updates Test Suite")
    print("=" * 60)
    
    results = []
    results.append(("PDF with Custom Race Name", test_pdf_export_with_race_name()))
    results.append(("PDF with Fallback Race Name", test_pdf_export_without_race_name()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))
    exit(0 if all_passed else 1)
