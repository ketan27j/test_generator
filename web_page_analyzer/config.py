# config.py - Configuration file for Web Page Analyzer

import os
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class AnalyzerConfig:
    """Configuration settings for Web Page Analyzer"""
    
    # Browser settings
    headless: bool = True
    window_size: tuple = (1920, 1080)
    implicit_wait: int = 10
    page_load_timeout: int = 30
    
    # Chrome options
    chrome_options: List[str] = None
    
    # Analysis settings
    take_screenshots: bool = False
    screenshot_dir: str = "screenshots"
    analyze_invisible_elements: bool = False
    max_elements_per_type: int = 100
    
    # XPath generation settings
    prefer_relative_xpath: bool = True
    use_text_in_xpath: bool = True
    max_xpath_length: int = 200
    
    # Context extraction settings
    max_surrounding_text_length: int = 200
    extract_form_context: bool = True
    extract_label_associations: bool = True
    
    # Performance settings
    disable_images: bool = True
    disable_javascript: bool = False
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Output settings
    output_dir: str = "analysis_results"
    save_raw_html: bool = False
    save_page_screenshot: bool = True
    
    # Custom selectors
    custom_selectors: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.chrome_options is None:
            self.chrome_options = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-plugins'
            ]
        
        if self.custom_selectors is None:
            self.custom_selectors = {}
        
        # Create directories
        os.makedirs(self.screenshot_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

# Default configurations for different use cases
CONFIGS = {
    'development': AnalyzerConfig(
        headless=False,
        take_screenshots=True,
        save_page_screenshot=True,
        implicit_wait=5
    ),
    
    'production': AnalyzerConfig(
        headless=True,
        take_screenshots=False,
        disable_images=True,
        implicit_wait=10
    ),
    
    'testing': AnalyzerConfig(
        headless=True,
        take_screenshots=True,
        analyze_invisible_elements=True,
        max_elements_per_type=50
    ),
    
    'performance': AnalyzerConfig(
        headless=True,
        disable_images=True,
        disable_javascript=False,
        implicit_wait=5,
        page_load_timeout=15
    )
}

# Environment-specific settings
def get_config(env: str = 'development') -> AnalyzerConfig:
    """Get configuration for specific environment"""
    return CONFIGS.get(env, CONFIGS['development'])
