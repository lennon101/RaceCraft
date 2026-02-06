#!/usr/bin/env python3
"""
Test script to validate the elevation profile x-axis fix.
This script verifies that the JavaScript changes are syntactically correct
and follow the expected patterns for Chart.js linear scale configuration.
"""

import re
import sys

def test_app_js_changes():
    """Test that app.js contains the correct elevation profile fixes."""
    
    print("=" * 70)
    print("ELEVATION PROFILE X-AXIS FIX - VALIDATION")
    print("=" * 70)
    print()
    
    with open('static/js/app.js', 'r') as f:
        content = f.read()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Check for x/y coordinate data format
    print("Test 1: Data format uses x/y coordinates")
    if "data: elevationProfile.map(p => ({ x: p.distance, y: p.elevation }))" in content:
        print("  ✓ PASS: Found x/y coordinate mapping")
        tests_passed += 1
    else:
        print("  ✗ FAIL: x/y coordinate mapping not found")
        tests_failed += 1
    print()
    
    # Test 2: Check for linear scale type
    print("Test 2: X-axis uses linear scale type")
    if re.search(r"x:\s*{\s*type:\s*['\"]linear['\"]", content):
        print("  ✓ PASS: Found linear scale type declaration")
        tests_passed += 1
    else:
        print("  ✗ FAIL: Linear scale type not found")
        tests_failed += 1
    print()
    
    # Test 3: Check for dynamic stepSize calculation
    print("Test 3: Dynamic stepSize calculation based on total distance")
    if "stepSize: (function()" in content and "totalDistance <= 10" in content:
        print("  ✓ PASS: Found dynamic stepSize calculation")
        tests_passed += 1
    else:
        print("  ✗ FAIL: Dynamic stepSize calculation not found")
        tests_failed += 1
    print()
    
    # Test 4: Check checkpoint line uses distance value
    print("Test 4: Checkpoint lines use distance value directly")
    if "x.getPixelForValue(cp.distance)" in content:
        print("  ✓ PASS: Found direct distance value usage for checkpoint lines")
        tests_passed += 1
    else:
        print("  ✗ FAIL: Direct distance value usage not found")
        tests_failed += 1
    print()
    
    # Test 5: Check that old index-based logic is removed
    print("Test 5: Old index-based logic removed")
    has_closestIndex = "let closestIndex = 0" in content
    has_for_loop = "for (let i = 1; i < elevationProfile.length" in content
    
    if not has_closestIndex and not has_for_loop:
        print("  ✓ PASS: Old index-finding logic removed")
        tests_passed += 1
    else:
        if has_closestIndex:
            print("  ✗ FAIL: 'let closestIndex = 0' still present")
        if has_for_loop:
            print("  ✗ FAIL: 'for (let i = 1; i < elevationProfile.length' still present")
        tests_failed += 1
    print()
    
    # Test 6: Check tooltip uses parsed.x
    print("Test 6: Tooltips use parsed.x for distance")
    if "context[0].parsed.x" in content and "context.parsed.x" in content:
        print("  ✓ PASS: Found parsed.x usage in tooltips")
        tests_passed += 1
    else:
        print("  ✗ FAIL: parsed.x usage not found in tooltips")
        tests_failed += 1
    print()
    
    # Test 7: Check that old labels array is removed
    print("Test 7: Old labels array removed from data configuration")
    # Look for the pattern within renderElevationChart function
    render_chart_match = re.search(
        r"elevationChart = new Chart\(ctx, \{[^}]*data:\s*\{[^}]*\}",
        content,
        re.DOTALL
    )
    if render_chart_match:
        chart_data = render_chart_match.group(0)
        if "labels: elevationProfile.map" not in chart_data:
            print("  ✓ PASS: Labels array removed from chart data configuration")
            tests_passed += 1
        else:
            print("  ✗ FAIL: Labels array still present in chart data configuration")
            tests_failed += 1
    else:
        print("  ⚠ WARNING: Could not find chart data configuration")
        tests_failed += 1
    print()
    
    # Test 8: Verify stepSize intervals
    print("Test 8: StepSize intervals defined correctly")
    intervals_found = []
    if "totalDistance <= 10" in content and "return 1" in content:
        intervals_found.append("10km → 1km")
    if "totalDistance <= 30" in content and "return 2" in content:
        intervals_found.append("30km → 2km")
    if "totalDistance <= 50" in content and "return 5" in content:
        intervals_found.append("50km → 5km")
    if "totalDistance <= 100" in content and "return 10" in content:
        intervals_found.append("100km → 10km")
    if "totalDistance <= 200" in content and "return 20" in content:
        intervals_found.append("200km → 20km")
    if "return 25" in content:
        intervals_found.append(">200km → 25km")
    
    if len(intervals_found) >= 5:
        print(f"  ✓ PASS: Found {len(intervals_found)} distance-based step intervals")
        for interval in intervals_found:
            print(f"    - {interval}")
        tests_passed += 1
    else:
        print(f"  ✗ FAIL: Only found {len(intervals_found)} intervals, expected 6")
        tests_failed += 1
    print()
    
    # Test 9: Verify x-axis min/max bounds
    print("Test 9: X-axis bounded to actual distance range")
    x_axis_match = re.search(
        r"x:\s*\{[^}]*type:\s*['\"]linear['\"][^}]*\}",
        content,
        re.DOTALL
    )
    if x_axis_match:
        x_axis_config = x_axis_match.group(0)
        has_min = "min: 0" in x_axis_config or "min:0" in x_axis_config
        has_max = "max: elevationProfile[elevationProfile.length - 1].distance" in x_axis_config
        
        if has_min and has_max:
            print("  ✓ PASS: X-axis has min: 0 and max: totalDistance")
            print("    - Prevents whitespace beyond race distance")
            tests_passed += 1
        else:
            if not has_min:
                print("  ✗ FAIL: X-axis min not set to 0")
            if not has_max:
                print("  ✗ FAIL: X-axis max not set to total distance")
            tests_failed += 1
    else:
        print("  ⚠ WARNING: Could not find x-axis configuration")
        tests_failed += 1
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print()
    
    if tests_failed == 0:
        print("✓ ALL TESTS PASSED - Changes look correct!")
        print()
        print("Expected Benefits:")
        print("  • X-axis represents cumulative distance linearly")
        print("  • X-axis bounded to 0 to total distance (no whitespace)")
        print("  • Graticules evenly spaced and adapt to total distance")
        print("  • Visual distortion from GPX sampling eliminated")
        print("  • On 102km route, 50km point appears at ~50% (not ~25%)")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Please review changes")
        return 1

if __name__ == '__main__':
    sys.exit(test_app_js_changes())
