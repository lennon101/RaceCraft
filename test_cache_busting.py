#!/usr/bin/env python3
"""
Test script for Cache Busting and Client State Versioning system.

This script validates that the cache busting implementation is working correctly:
1. Version extraction from app.py docstring
2. Version passing to templates
3. Query strings on static assets
4. Version variables in HTML
"""

import sys
import re
import os

def test_version_extraction():
    """Test that version can be extracted from app.py docstring."""
    print("Testing version extraction from app.py...")
    
    # Import the extract function
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import extract_app_version, APP_VERSION
    
    version = extract_app_version()
    print(f"  ✓ Extracted version: {version}")
    
    # Check version format
    if not re.match(r'v?\d+\.\d+\.\d+', version):
        print(f"  ✗ WARNING: Version format unexpected: {version}")
        print(f"    Expected format: v1.2.3 or 1.2.3")
    else:
        print(f"  ✓ Version format is valid")
    
    print(f"  ✓ APP_VERSION constant: {APP_VERSION}")
    return version

def test_template_rendering():
    """Test that templates receive version and render correctly."""
    print("\nTesting template rendering...")
    
    # Start Flask app
    from app import app
    
    with app.test_client() as client:
        # Test index page
        response = client.get('/')
        html = response.data.decode('utf-8')
        
        # Check for version in window variables
        if 'window.APP_VERSION' in html:
            print(f"  ✓ APP_VERSION injected in index.html")
            # Extract the version value
            match = re.search(r"window\.APP_VERSION = '([^']+)'", html)
            if match:
                version_in_html = match.group(1)
                print(f"    Value: {version_in_html}")
        else:
            print(f"  ✗ ERROR: APP_VERSION not found in index.html")
            return False
        
        # Check for CLIENT_STORAGE_VERSION
        if 'window.CLIENT_STORAGE_VERSION' in html:
            print(f"  ✓ CLIENT_STORAGE_VERSION injected in index.html")
            match = re.search(r"window\.CLIENT_STORAGE_VERSION = '([^']+)'", html)
            if match:
                storage_version = match.group(1)
                print(f"    Value: {storage_version}")
        else:
            print(f"  ✗ ERROR: CLIENT_STORAGE_VERSION not found in index.html")
            return False
        
        # Check for version query strings on static assets
        css_matches = re.findall(r'href="[^"]*\.css\?v=([^"]+)"', html)
        js_matches = re.findall(r'src="[^"]*\.js\?v=([^"]+)"', html)
        
        if css_matches:
            print(f"  ✓ CSS files have cache-busting query strings: {len(css_matches)} files")
            print(f"    Example: style.css?v={css_matches[0]}")
        else:
            print(f"  ✗ WARNING: No CSS files found with version query strings")
        
        if js_matches:
            print(f"  ✓ JS files have cache-busting query strings: {len(js_matches)} files")
            print(f"    Example: app.js?v={js_matches[0]}")
        else:
            print(f"  ✗ WARNING: No JS files found with version query strings")
        
        # Test about page
        response = client.get('/about')
        html = response.data.decode('utf-8')
        
        if 'window.APP_VERSION' in html:
            print(f"  ✓ APP_VERSION injected in about.html")
        else:
            print(f"  ✗ ERROR: APP_VERSION not found in about.html")
            return False
        
        # Test docs page
        response = client.get('/docs')
        html = response.data.decode('utf-8')
        
        if 'window.APP_VERSION' in html:
            print(f"  ✓ APP_VERSION injected in docs.html")
        else:
            print(f"  ✗ ERROR: APP_VERSION not found in docs.html")
            return False
    
    return True

def test_javascript_functions():
    """Test that JavaScript functions exist in app.js."""
    print("\nTesting JavaScript implementation...")
    
    with open('static/js/app.js', 'r') as f:
        js_content = f.read()
    
    # Check for required functions
    required_functions = [
        'initializeCacheBusting',
        'logVersionInfo',
        'unregisterServiceWorkers',
        'checkClientStorageVersion'
    ]
    
    for func_name in required_functions:
        if f'function {func_name}' in js_content:
            print(f"  ✓ Found function: {func_name}()")
        else:
            print(f"  ✗ ERROR: Function not found: {func_name}()")
            return False
    
    # Check that initializeCacheBusting is called
    if 'initializeCacheBusting()' in js_content:
        print(f"  ✓ initializeCacheBusting() is called")
    else:
        print(f"  ✗ ERROR: initializeCacheBusting() not called")
        return False
    
    return True

def test_documentation():
    """Test that documentation files exist."""
    print("\nTesting documentation...")
    
    docs = [
        ('copilot-instructions.md', 'Copilot Instructions'),
        ('docs/deployment/CACHE_BUSTING.md', 'Cache Busting Documentation')
    ]
    
    for doc_path, doc_name in docs:
        if os.path.exists(doc_path):
            with open(doc_path, 'r') as f:
                content = f.read()
            
            # Check for key sections
            if 'APP_VERSION' in content and 'CLIENT_STORAGE_VERSION' in content:
                print(f"  ✓ {doc_name} exists and contains version documentation")
            else:
                print(f"  ✗ WARNING: {doc_name} missing version information")
        else:
            print(f"  ✗ WARNING: {doc_name} not found at {doc_path}")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Cache Busting & Client State Versioning - Test Suite")
    print("=" * 60)
    
    try:
        version = test_version_extraction()
        template_ok = test_template_rendering()
        js_ok = test_javascript_functions()
        docs_ok = test_documentation()
        
        print("\n" + "=" * 60)
        print("Test Results Summary")
        print("=" * 60)
        
        if template_ok and js_ok and docs_ok:
            print("✅ ALL TESTS PASSED")
            print(f"\nCache busting system is operational with version: {version}")
            print("\nNext steps:")
            print("  1. Test in browser at http://localhost:5000")
            print("  2. Check browser console for version logs")
            print("  3. Test localStorage migration by setting old version")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            print("\nPlease review the errors above and fix the implementation.")
            return 1
    
    except Exception as e:
        print(f"\n❌ TEST SUITE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
