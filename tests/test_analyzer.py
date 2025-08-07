import unittest
import tempfile
import os
from web_page_analyzer import WebPageAnalyzer
from web_page_analyzer.config import get_config

class TestWebPageAnalyzer(unittest.TestCase):
    """Test cases for WebPageAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config('testing')
        self.analyzer = WebPageAnalyzer(
            headless=self.config.headless,
            implicit_wait=self.config.implicit_wait
        )
    
    def tearDown(self):
        """Clean up after tests"""
        if self.analyzer:
            self.analyzer.close()
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.headless, self.config.headless)
    
    def test_simple_page_analysis(self):
        """Test basic page analysis"""
        # Use a simple HTML page for testing
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <button id="test-btn">Click Me</button>
            <input type="text" name="username" placeholder="Enter username">
            <a href="/link">Test Link</a>
        </body>
        </html>
        """
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_file = f.name
        
        try:
            # Analyze the temporary file
            file_url = f"file://{os.path.abspath(temp_file)}"
            analysis = self.analyzer.analyze_page(file_url)
            
            # Assertions
            self.assertEqual(analysis.title, "Test Page")
            self.assertGreater(len(analysis.elements), 0)
            
            # Check for specific elements
            button_elements = [el for el in analysis.elements if el.tag_name == 'button']
            self.assertGreater(len(button_elements), 0)
            
            input_elements = [el for el in analysis.elements if el.tag_name == 'input']
            self.assertGreater(len(input_elements), 0)
            
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_xpath_generation(self):
        """Test XPath generation functionality"""
        html_content = """
        <html>
        <body>
            <div id="unique-id">Test Content</div>
            <button class="btn">Click</button>
        </body>
        </html>
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_file = f.name
        
        try:
            file_url = f"file://{os.path.abspath(temp_file)}"
            analysis = self.analyzer.analyze_page(file_url)
            
            # Find element with ID
            id_elements = [el for el in analysis.elements 
                          if el.attributes.get('id') == 'unique-id']
            
            if id_elements:
                element = id_elements[0]
                self.assertIn('unique-id', element.relative_xpath)
            
        finally:
            os.unlink(temp_file)

if __name__ == '__main__':
    unittest.main()