import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from bs4 import BeautifulSoup
import requests


@dataclass
class ElementInfo:
    """Data class to store information about a web element"""
    tag_name: str
    element_type: str
    xpath: str
    relative_xpath: str
    css_selector: str
    text_content: str
    attributes: Dict[str, str]
    is_visible: bool
    is_clickable: bool
    is_interactable: bool
    bounding_box: Dict[str, float]
    context: Dict[str, str]  # surrounding elements, labels, etc.
    screenshot_path: Optional[str] = None


@dataclass
class PageAnalysis:
    """Complete page analysis results"""
    url: str
    title: str
    elements: List[ElementInfo]
    page_structure: Dict[str, any]
    metadata: Dict[str, str]
    timestamp: str


class WebPageAnalyzer:
    """
    Comprehensive web page analyzer using Selenium and BeautifulSoup
    """
    
    # Interactive element selectors
    INTERACTIVE_SELECTORS = {
        'buttons': [
            'button',
            'input[type="button"]',
            'input[type="submit"]',
            'input[type="reset"]',
            '[role="button"]',
            'a[href]'
        ],
        'inputs': [
            'input[type="text"]',
            'input[type="email"]',
            'input[type="password"]',
            'input[type="number"]',
            'input[type="tel"]',
            'input[type="url"]',
            'input[type="search"]',
            'textarea',
            'select'
        ],
        'checkboxes': [
            'input[type="checkbox"]',
            'input[type="radio"]'
        ],
        'links': [
            'a[href]:not([role="button"])'
        ],
        'forms': [
            'form'
        ],
        'media': [
            'img[src]',
            'video',
            'audio'
        ]
    }

    def __init__(self, headless: bool = True, implicit_wait: int = 10):
        """
        Initialize the analyzer
        
        Args:
            headless: Run browser in headless mode
            implicit_wait: Implicit wait time for selenium
        """
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.driver = None
        self.soup = None
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with optimal settings"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Performance and stability options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')  # Faster loading
        
        # User agent to avoid bot detection
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(self.implicit_wait)
        
    def _create_soup(self):
        """Create BeautifulSoup object from current page source"""
        if self.driver:
            page_source = self.driver.page_source
            self.soup = BeautifulSoup(page_source, 'html.parser')
        
    def _generate_xpath(self, element) -> Tuple[str, str]:
        """
        Generate both absolute and relative XPath for an element
        
        Returns:
            Tuple of (absolute_xpath, relative_xpath)
        """
        try:
            # Get absolute XPath
            absolute_xpath = self.driver.execute_script(
                "function getXPath(element) {"
                "  if (element.id !== '') {"
                "    return '//*[@id=\"' + element.id + '\"]';"
                "  }"
                "  if (element === document.body) {"
                "    return '/html/body';"
                "  }"
                "  var ix = 0;"
                "  var siblings = element.parentNode.childNodes;"
                "  for (var i = 0; i < siblings.length; i++) {"
                "    var sibling = siblings[i];"
                "    if (sibling === element) {"
                "      return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';"
                "    }"
                "    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {"
                "      ix++;"
                "    }"
                "  }"
                "}"
                "return getXPath(arguments[0]);",
                element
            )
            
            # Generate relative XPath (more robust)
            relative_xpath = self._generate_relative_xpath(element)
            
            return absolute_xpath, relative_xpath
            
        except Exception as e:
            print(f"Error generating XPath: {e}")
            return "", ""
    
    def _generate_relative_xpath(self, element) -> str:
        """Generate a more robust relative XPath"""
        try:
            # Try to use unique attributes
            element_id = element.get_attribute('id')
            if element_id:
                return f"//*[@id='{element_id}']"
            
            # Try name attribute
            name = element.get_attribute('name')
            if name:
                return f"//*[@name='{name}']"
            
            # Try data attributes
            for attr_name in element.get_property('attributes') or []:
                if attr_name.startswith('data-'):
                    attr_value = element.get_attribute(attr_name)
                    if attr_value:
                        return f"//*[@{attr_name}='{attr_value}']"
            
            # Use text content for buttons and links
            text = element.text.strip()
            tag_name = element.tag_name.lower()
            
            if text and tag_name in ['button', 'a']:
                return f"//{tag_name}[normalize-space(text())='{text}']"
            
            # Use class as last resort
            class_name = element.get_attribute('class')
            if class_name:
                return f"//{tag_name}[@class='{class_name}']"
            
            # Fallback to tag name with position
            return f"//{tag_name}"
            
        except Exception as e:
            print(f"Error generating relative XPath: {e}")
            return ""
    
    def _get_element_context(self, element, soup_element) -> Dict[str, str]:
        """Get contextual information about an element"""
        context = {}
        
        try:
            # Get associated label
            label = self._find_associated_label(element, soup_element)
            if label:
                context['label'] = label
            
            # Get parent form information
            form_info = self._get_form_context(element)
            if form_info:
                context.update(form_info)
            
            # Get surrounding text
            surrounding_text = self._get_surrounding_text(soup_element)
            if surrounding_text:
                context['surrounding_text'] = surrounding_text
            
            # Get placeholder text
            placeholder = element.get_attribute('placeholder')
            if placeholder:
                context['placeholder'] = placeholder
            
            # Get title attribute
            title = element.get_attribute('title')
            if title:
                context['title'] = title
                
        except Exception as e:
            print(f"Error getting element context: {e}")
        
        return context
    
    def _find_associated_label(self, element, soup_element) -> Optional[str]:
        """Find label associated with form element"""
        try:
            # Check for label with 'for' attribute
            element_id = element.get_attribute('id')
            if element_id:
                label = self.soup.find('label', {'for': element_id})
                if label:
                    return label.get_text(strip=True)
            
            # Check for wrapping label
            parent_label = soup_element.find_parent('label')
            if parent_label:
                return parent_label.get_text(strip=True)
            
            # Check for nearby text
            prev_sibling = soup_element.find_previous_sibling(['label', 'span', 'div'])
            if prev_sibling and len(prev_sibling.get_text(strip=True)) < 100:
                return prev_sibling.get_text(strip=True)
                
        except Exception as e:
            print(f"Error finding label: {e}")
        
        return None
    
    def _get_form_context(self, element) -> Dict[str, str]:
        """Get form context for form elements"""
        try:
            form_element = element.find_element(By.XPATH, "./ancestor-or-self::form")
            if form_element:
                return {
                    'form_action': form_element.get_attribute('action') or '',
                    'form_method': form_element.get_attribute('method') or 'get',
                    'form_id': form_element.get_attribute('id') or '',
                    'form_class': form_element.get_attribute('class') or ''
                }
        except NoSuchElementException:
            pass
        except Exception as e:
            print(f"Error getting form context: {e}")
        
        return {}
    
    def _get_surrounding_text(self, soup_element, max_length: int = 200) -> str:
        """Get text content surrounding the element"""
        try:
            # Get parent element
            parent = soup_element.parent
            if parent:
                text = parent.get_text(strip=True)
                if len(text) <= max_length:
                    return text
                else:
                    return text[:max_length] + "..."
        except Exception as e:
            print(f"Error getting surrounding text: {e}")
        
        return ""
    
    def _is_element_visible(self, element) -> bool:
        """Check if element is visible"""
        try:
            return (element.is_displayed() and 
                   element.size['height'] > 0 and 
                   element.size['width'] > 0)
        except Exception:
            return False
    
    def _is_element_clickable(self, element) -> bool:
        """Check if element is clickable"""
        try:
            WebDriverWait(self.driver, 1).until(
                EC.element_to_be_clickable(element)
            )
            return True
        except TimeoutException:
            return False
        except Exception:
            return False
    
    def _is_element_interactable(self, element) -> bool:
        """Check if element can be interacted with"""
        try:
            return (element.is_enabled() and 
                   self._is_element_visible(element))
        except Exception:
            return False
    
    def _get_element_screenshot(self, element, filename: str) -> Optional[str]:
        """Take screenshot of specific element"""
        try:
            screenshot_path = f"screenshots/{filename}"
            element.screenshot(screenshot_path)
            return screenshot_path
        except Exception as e:
            print(f"Error taking element screenshot: {e}")
            return None
    
    def _analyze_element(self, element, element_type: str) -> ElementInfo:
        """Analyze a single web element comprehensively"""
        try:
            # Get corresponding BeautifulSoup element
            element_html = element.get_attribute('outerHTML')
            soup_element = BeautifulSoup(element_html, 'html.parser').find()
            
            # Generate XPaths
            abs_xpath, rel_xpath = self._generate_xpath(element)
            
            # Get CSS selector
            css_selector = self._generate_css_selector(element)
            
            # Get all attributes
            attributes = {}
            try:
                # Get all attributes using JavaScript
                attrs = self.driver.execute_script(
                    "var items = {}; "
                    "for (index = 0; index < arguments[0].attributes.length; ++index) { "
                    "  items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value; "
                    "} "
                    "return items;", 
                    element
                )
                attributes = attrs or {}
            except Exception:
                pass
            
            # Get bounding box
            location = element.location
            size = element.size
            bounding_box = {
                'x': location['x'],
                'y': location['y'],
                'width': size['width'],
                'height': size['height']
            }
            
            # Get context information
            context = self._get_element_context(element, soup_element)
            
            return ElementInfo(
                tag_name=element.tag_name.lower(),
                element_type=element_type,
                xpath=abs_xpath,
                relative_xpath=rel_xpath,
                css_selector=css_selector,
                text_content=element.text.strip(),
                attributes=attributes,
                is_visible=self._is_element_visible(element),
                is_clickable=self._is_element_clickable(element),
                is_interactable=self._is_element_interactable(element),
                bounding_box=bounding_box,
                context=context
            )
            
        except Exception as e:
            print(f"Error analyzing element: {e}")
            return None
    
    def _generate_css_selector(self, element) -> str:
        """Generate CSS selector for element"""
        try:
            return self.driver.execute_script(
                "function getCSSSelector(element) {"
                "  if (element.id) return '#' + element.id;"
                "  var path = [];"
                "  while (element.nodeType === Node.ELEMENT_NODE) {"
                "    var selector = element.nodeName.toLowerCase();"
                "    if (element.className) {"
                "      selector += '.' + element.className.split(' ').join('.');"
                "    }"
                "    path.unshift(selector);"
                "    element = element.parentNode;"
                "  }"
                "  return path.join(' > ');"
                "};"
                "return getCSSSelector(arguments[0]);",
                element
            )
        except Exception:
            return ""
    
    def analyze_page(self, url: str, take_screenshots: bool = False) -> PageAnalysis:
        """
        Perform comprehensive analysis of a web page
        
        Args:
            url: URL to analyze
            take_screenshots: Whether to take element screenshots
            
        Returns:
            PageAnalysis object with complete analysis
        """
        print(f"Starting analysis of: {url}")
        
        # Setup driver if not already done
        if not self.driver:
            self._setup_driver()
        
        try:
            # Navigate to page
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Create BeautifulSoup object
            self._create_soup()
            
            # Get page metadata
            title = self.driver.title
            current_url = self.driver.current_url
            
            metadata = {
                'page_load_time': str(time.time()),
                'viewport_size': str(self.driver.get_window_size()),
                'user_agent': self.driver.execute_script("return navigator.userAgent;")
            }
            
            # Analyze all interactive elements
            all_elements = []
            
            for element_type, selectors in self.INTERACTIVE_SELECTORS.items():
                print(f"Analyzing {element_type}...")
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for i, element in enumerate(elements):
                            element_info = self._analyze_element(element, element_type)
                            
                            if element_info and element_info.is_visible:
                                # Take screenshot if requested
                                if take_screenshots:
                                    screenshot_filename = f"{element_type}_{i}_{int(time.time())}.png"
                                    element_info.screenshot_path = self._get_element_screenshot(
                                        element, screenshot_filename
                                    )
                                
                                all_elements.append(element_info)
                                
                    except Exception as e:
                        print(f"Error analyzing {selector}: {e}")
                        continue
            
            # Analyze page structure
            page_structure = self._analyze_page_structure()
            
            # Create analysis result
            analysis = PageAnalysis(
                url=current_url,
                title=title,
                elements=all_elements,
                page_structure=page_structure,
                metadata=metadata,
                timestamp=str(time.time())
            )
            
            print(f"Analysis complete. Found {len(all_elements)} interactive elements.")
            return analysis
            
        except Exception as e:
            print(f"Error during page analysis: {e}")
            raise
    
    def _analyze_page_structure(self) -> Dict[str, any]:
        """Analyze overall page structure"""
        structure = {}
        
        try:
            # Get forms information
            forms = self.soup.find_all('form')
            structure['forms_count'] = len(forms)
            structure['forms'] = []
            
            for form in forms:
                form_info = {
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'id': form.get('id', ''),
                    'class': form.get('class', [])
                }
                structure['forms'].append(form_info)
            
            # Get navigation elements
            nav_elements = self.soup.find_all(['nav', 'header', 'footer'])
            structure['navigation_sections'] = len(nav_elements)
            
            # Get main content areas
            main_elements = self.soup.find_all(['main', 'article', 'section'])
            structure['content_sections'] = len(main_elements)
            
            # Get media elements
            images = self.soup.find_all('img')
            videos = self.soup.find_all('video')
            structure['media'] = {
                'images_count': len(images),
                'videos_count': len(videos)
            }
            
        except Exception as e:
            print(f"Error analyzing page structure: {e}")
        
        return structure
    
    def save_analysis(self, analysis: PageAnalysis, filename: str):
        """Save analysis results to JSON file"""
        try:
            # Convert to dictionary for JSON serialization
            analysis_dict = asdict(analysis)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_dict, f, indent=2, ensure_ascii=False)
            
            print(f"Analysis saved to {filename}")
            
        except Exception as e:
            print(f"Error saving analysis: {e}")
    
    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None


# Example usage and testing
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = WebPageAnalyzer(headless=False)  # Set to True for headless mode
    
    try:
        # Analyze a webpage
        url = "https://example.com"  # Replace with target URL
        analysis = analyzer.analyze_page(url)
        
        # Print summary
        print(f"\n=== Analysis Summary ===")
        print(f"URL: {analysis.url}")
        print(f"Title: {analysis.title}")
        print(f"Total elements found: {len(analysis.elements)}")
        
        # Print element details
        for element in analysis.elements[:5]:  # Show first 5 elements
            print(f"\nElement: {element.tag_name}")
            print(f"Type: {element.element_type}")
            print(f"Text: {element.text_content[:50]}...")
            print(f"XPath: {element.relative_xpath}")
            print(f"Visible: {element.is_visible}")
            print(f"Clickable: {element.is_clickable}")
        
        # Save results
        analyzer.save_analysis(analysis, "page_analysis.json")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
    
    finally:
        # Clean up
        analyzer.close()