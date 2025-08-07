# examples/basic_usage.py
"""
Basic usage examples for Web Page Analyzer
This file demonstrates how to get started with the analyzer
"""

import os
import sys
import time
from pathlib import Path

# Add the parent directory to Python path so we can import our analyzer
sys.path.append(str(Path(__file__).parent.parent))

from web_page_analyzer import WebPageAnalyzer

def example_1_simple_analysis():
    """Example 1: Simple page analysis"""
    print("=" * 60)
    print("EXAMPLE 1: Simple Page Analysis")
    print("=" * 60)
    
    # Initialize the analyzer
    analyzer = WebPageAnalyzer(headless=True)  # Set to False to see browser
    
    try:
        # Analyze a simple webpage
        print("Analyzing https://httpbin.org/forms/post...")
        analysis = analyzer.analyze_page("https://httpbin.org/forms/post")
        
        # Display basic information
        print(f"\nPage Title: {analysis.title}")
        print(f"URL: {analysis.url}")
        print(f"Total interactive elements found: {len(analysis.elements)}")
        
        # Show first few elements
        print("\nFirst 5 elements found:")
        print("-" * 40)
        for i, element in enumerate(analysis.elements[:5]):
            print(f"{i+1}. {element.tag_name.upper()}")
            print(f"   Text: '{element.text_content[:50]}...'" if len(element.text_content) > 50 else f"   Text: '{element.text_content}'")
            print(f"   Type: {element.element_type}")
            print(f"   XPath: {element.relative_xpath}")
            print(f"   Visible: {element.is_visible}")
            print()
        
        return analysis
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None
        
    finally:
        # Always close the browser
        analyzer.close()

def example_2_form_analysis():
    """Example 2: Analyze form elements specifically"""
    print("=" * 60)
    print("EXAMPLE 2: Form Elements Analysis")
    print("=" * 60)
    
    analyzer = WebPageAnalyzer(headless=True)
    
    try:
        # Analyze a page with forms
        print("Analyzing form at https://httpbin.org/forms/post...")
        analysis = analyzer.analyze_page("https://httpbin.org/forms/post")
        
        # Filter for form elements
        form_elements = [el for el in analysis.elements if el.element_type in ['inputs', 'buttons']]
        
        print(f"\nFound {len(form_elements)} form elements:")
        print("-" * 40)
        
        for element in form_elements:
            print(f"Element: {element.tag_name}")
            print(f"Type: {element.attributes.get('type', 'N/A')}")
            print(f"Name: {element.attributes.get('name', 'N/A')}")
            print(f"ID: {element.attributes.get('id', 'N/A')}")
            print(f"Placeholder: {element.attributes.get('placeholder', 'N/A')}")
            print(f"Label: {element.context.get('label', 'No label found')}")
            print(f"XPath: {element.relative_xpath}")
            print(f"Can interact: {element.is_interactable}")
            print("-" * 40)
        
        return form_elements
        
    except Exception as e:
        print(f"Error during form analysis: {e}")
        return None
        
    finally:
        analyzer.close()

def example_3_save_results():
    """Example 3: Save analysis results to file"""
    print("=" * 60)
    print("EXAMPLE 3: Save Analysis Results")
    print("=" * 60)
    
    analyzer = WebPageAnalyzer(headless=True)
    
    try:
        # Analyze page
        print("Analyzing page and saving results...")
        analysis = analyzer.analyze_page("https://httpbin.org/forms/post")
        
        # Create results directory if it doesn't exist
        results_dir = Path("analysis_results")
        results_dir.mkdir(exist_ok=True)
        
        # Save analysis to JSON file
        timestamp = int(time.time())
        filename = f"analysis_results/analysis_{timestamp}.json"
        analyzer.save_analysis(analysis, filename)
        
        print(f"Analysis saved to: {filename}")
        print(f"File size: {os.path.getsize(filename)} bytes")
        
        # Show what was saved
        print(f"\nSaved data includes:")
        print(f"- Page URL and title")
        print(f"- {len(analysis.elements)} interactive elements")
        print(f"- Element properties (XPath, attributes, context)")
        print(f"- Page structure information")
        print(f"- Analysis timestamp")
        
        return filename
        
    except Exception as e:
        print(f"Error saving analysis: {e}")
        return None
        
    finally:
        analyzer.close()

def example_4_filter_elements():
    """Example 4: Filter elements by criteria"""
    print("=" * 60)
    print("EXAMPLE 4: Filter Elements by Criteria")
    print("=" * 60)
    
    analyzer = WebPageAnalyzer(headless=True)
    
    try:
        # Analyze page
        print("Analyzing page and applying filters...")
        analysis = analyzer.analyze_page("https://httpbin.org/forms/post")
        
        # Filter 1: Only clickable elements
        clickable_elements = [el for el in analysis.elements if el.is_clickable]
        print(f"\nClickable elements: {len(clickable_elements)}")
        
        for element in clickable_elements:
            print(f"- {element.tag_name}: '{element.text_content}' (XPath: {element.relative_xpath})")
        
        # Filter 2: Only elements with IDs
        elements_with_ids = [el for el in analysis.elements if el.attributes.get('id')]
        print(f"\nElements with IDs: {len(elements_with_ids)}")
        
        for element in elements_with_ids:
            print(f"- {element.tag_name}#{element.attributes['id']}: XPath: {element.relative_xpath}")
        
        # Filter 3: Only input elements
        input_elements = [el for el in analysis.elements if el.tag_name == 'input']
        print(f"\nInput elements: {len(input_elements)}")
        
        for element in input_elements:
            input_type = element.attributes.get('type', 'text')
            name = element.attributes.get('name', 'unnamed')
            print(f"- {input_type} input '{name}': XPath: {element.relative_xpath}")
        
        return {
            'clickable': clickable_elements,
            'with_ids': elements_with_ids,
            'inputs': input_elements
        }
        
    except Exception as e:
        print(f"Error filtering elements: {e}")
        return None
        
    finally:
        analyzer.close()

def example_5_local_html():
    """Example 5: Analyze local HTML file"""
    print("=" * 60)
    print("EXAMPLE 5: Analyze Local HTML File")
    print("=" * 60)
    
    # Create a sample HTML file for testing
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sample Test Page</title>
    </head>
    <body>
        <h1>Test Form</h1>
        <form id="test-form" action="/submit" method="post">
            <div>
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" placeholder="Enter your username" required>
            </div>
            
            <div>
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" placeholder="your@email.com">
            </div>
            
            <div>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <div>
                <input type="checkbox" id="remember" name="remember">
                <label for="remember">Remember me</label>
            </div>
            
            <div>
                <button type="submit" id="submit-btn">Submit</button>
                <button type="button" id="cancel-btn">Cancel</button>
            </div>
        </form>
        
        <div>
            <a href="https://example.com" id="external-link">External Link</a>
        </div>
    </body>
    </html>
    """
    
    # Save sample HTML to temporary file
    temp_html_path = "temp_test.html"
    
    try:
        with open(temp_html_path, 'w', encoding='utf-8') as f:
            f.write(sample_html)
        
        print(f"Created temporary HTML file: {temp_html_path}")
        
        # Analyze the local file
        analyzer = WebPageAnalyzer(headless=True)
        
        try:
            file_url = f"file://{os.path.abspath(temp_html_path)}"
            print(f"Analyzing local file: {file_url}")
            
            analysis = analyzer.analyze_page(file_url)
            
            print(f"\nAnalysis Results:")
            print(f"Title: {analysis.title}")
            print(f"Elements found: {len(analysis.elements)}")
            
            # Show detailed breakdown
            element_types = {}
            for element in analysis.elements:
                elem_type = element.element_type
                element_types[elem_type] = element_types.get(elem_type, 0) + 1
            
            print(f"\nElement breakdown:")
            for elem_type, count in element_types.items():
                print(f"- {elem_type}: {count}")
            
            # Show form elements with labels
            print(f"\nForm elements with their labels:")
            form_elements = [el for el in analysis.elements if el.element_type in ['inputs', 'buttons']]
            
            for element in form_elements:
                label = element.context.get('label', 'No label')
                elem_id = element.attributes.get('id', 'No ID')
                elem_name = element.attributes.get('name', 'No name')
                
                print(f"- {element.tag_name} (ID: {elem_id}, Name: {elem_name})")
                print(f"  Label: {label}")
                print(f"  XPath: {element.relative_xpath}")
                print()
            
            return analysis
            
        finally:
            analyzer.close()
    
    except Exception as e:
        print(f"Error in local HTML analysis: {e}")
        return None
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
            print(f"Cleaned up temporary file: {temp_html_path}")

def example_6_performance_monitoring():
    """Example 6: Monitor analysis performance"""
    print("=" * 60)
    print("EXAMPLE 6: Performance Monitoring")
    print("=" * 60)
    
    analyzer = WebPageAnalyzer(headless=True)
    
    try:
        # Monitor analysis time
        start_time = time.time()
        print("Starting analysis with performance monitoring...")
        
        analysis = analyzer.analyze_page("https://httpbin.org/forms/post")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate performance metrics
        elements_per_second = len(analysis.elements) / total_time if total_time > 0 else 0
        
        print(f"\n=== Performance Metrics ===")
        print(f"Total analysis time: {total_time:.2f} seconds")
        print(f"Elements analyzed: {len(analysis.elements)}")
        print(f"Analysis rate: {elements_per_second:.2f} elements/second")
        
        # Element distribution
        visible_elements = sum(1 for el in analysis.elements if el.is_visible)
        clickable_elements = sum(1 for el in analysis.elements if el.is_clickable)
        interactable_elements = sum(1 for el in analysis.elements if el.is_interactable)
        
        print(f"\n=== Element Statistics ===")
        print(f"Visible elements: {visible_elements}/{len(analysis.elements)} ({visible_elements/len(analysis.elements)*100:.1f}%)")
        print(f"Clickable elements: {clickable_elements}/{len(analysis.elements)} ({clickable_elements/len(analysis.elements)*100:.1f}%)")
        print(f"Interactable elements: {interactable_elements}/{len(analysis.elements)} ({interactable_elements/len(analysis.elements)*100:.1f}%)")
        
        return {
            'total_time': total_time,
            'elements_count': len(analysis.elements),
            'elements_per_second': elements_per_second,
            'visible_percent': visible_elements/len(analysis.elements)*100,
            'clickable_percent': clickable_elements/len(analysis.elements)*100
        }
        
    except Exception as e:
        print(f"Error in performance monitoring: {e}")
        return None
        
    finally:
        analyzer.close()

def main():
    """Run all basic usage examples"""
    print("Web Page Analyzer - Basic Usage Examples")
    print("=" * 80)
    print("This script demonstrates basic usage of the Web Page Analyzer")
    print("Make sure you have installed all requirements: pip install -r requirements.txt")
    print("=" * 80)
    
    # Create necessary directories
    Path("analysis_results").mkdir(exist_ok=True)
    Path("screenshots").mkdir(exist_ok=True)
    
    # Run examples
    examples = [
        ("Simple Analysis", example_1_simple_analysis),
        ("Form Analysis", example_2_form_analysis),
        ("Save Results", example_3_save_results),
        ("Filter Elements", example_4_filter_elements),
        ("Local HTML", example_5_local_html),
        ("Performance Monitoring", example_6_performance_monitoring)
    ]
    
    results = {}
    
    for name, example_func in examples:
        print(f"\n{'='*80}")
        print(f"Running: {name}")
        print(f"{'='*80}")
        
        try:
            result = example_func()
            results[name] = result
            print(f"✓ {name} completed successfully")
            
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            results[name] = None
        
        # Small delay between examples
        time.sleep(1)
    
    # Summary
    print(f"\n{'='*80}")
    print("EXAMPLES SUMMARY")
    print(f"{'='*80}")
    
    for name, result in results.items():
        status = "✓ SUCCESS" if result is not None else "✗ FAILED"
        print(f"{name}: {status}")
    
    print(f"\nAll examples completed!")
    print(f"Check the 'analysis_results' directory for saved files.")

if __name__ == "__main__":
    main()