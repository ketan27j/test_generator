# Web Action Analyzer Tool
# A comprehensive tool to track browser actions and analyze webpage changes

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import time
import json
import hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import difflib
import os

class WebActionAnalyzer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Web Action Analyzer")
        self.root.geometry("1200x800")
        
        # Browser and tracking variables
        self.driver = None
        self.is_monitoring = False
        self.previous_state = {}
        self.action_log = []
        self.current_url = ""
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the main GUI interface"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # URL input section
        ttk.Label(main_frame, text="Website URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value="https://example.com")
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(button_frame, text="Force Refresh Check", command=self.check_for_changes, state=tk.DISABLED)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(button_frame, text="Save Log", command=self.save_log)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Monitoring interval
        ttk.Label(settings_frame, text="Check Interval (seconds):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="2")
        interval_spinbox = ttk.Spinbox(settings_frame, from_=1, to=30, width=5, textvariable=self.interval_var)
        interval_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Headless mode
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Headless Mode", variable=self.headless_var).pack(side=tk.LEFT, padx=20)
        
        # Auto-save
        self.autosave_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Auto-save on changes", variable=self.autosave_var).pack(side=tk.LEFT, padx=20)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready to start monitoring...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Log display with tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Action log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Action Log")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Changes tab
        changes_frame = ttk.Frame(notebook)
        notebook.add(changes_frame, text="Detected Changes")
        
        self.changes_text = scrolledtext.ScrolledText(changes_frame, wrap=tk.WORD, height=20)
        self.changes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # XPath finder tab
        xpath_frame = ttk.Frame(notebook)
        notebook.add(xpath_frame, text="XPath Finder")
        
        ttk.Label(xpath_frame, text="Click on elements in the browser to get their XPath:").pack(anchor=tk.W, padx=5, pady=5)
        self.xpath_text = scrolledtext.ScrolledText(xpath_frame, wrap=tk.WORD, height=15)
        self.xpath_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def start_monitoring(self):
        """Start the web monitoring process"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL")
            return
            
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_var.set(url)
        
        try:
            self.setup_driver()
            self.driver.get(url)
            self.current_url = url
            
            # Store initial state
            self.previous_state = self.capture_page_state()
            
            # Update GUI
            self.is_monitoring = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.refresh_btn.config(state=tk.NORMAL)
            
            self.log_action("SYSTEM", f"Started monitoring: {url}")
            self.status_var.set("Monitoring active...")
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitoring_thread.start()
            
            # Setup click tracking
            self.setup_click_tracking()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start monitoring: {str(e)}")
            self.stop_monitoring()
    
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        if self.headless_var.get():
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            raise Exception(f"Chrome driver not found. Please install ChromeDriver: {str(e)}")
    
    def setup_click_tracking(self):
        """Inject JavaScript to track clicks and interactions"""
        click_script = """
        window.actionTracker = {
            actions: [],
            addAction: function(action) {
                this.actions.push(action);
            }
        };
        
        // Track clicks
        document.addEventListener('click', function(e) {
            var xpath = getXPath(e.target);
            var action = {
                type: 'CLICK',
                element: e.target.tagName + (e.target.id ? '#' + e.target.id : '') + 
                        (e.target.className ? '.' + e.target.className.replace(/\s+/g, '.') : ''),
                xpath: xpath,
                text: e.target.textContent ? e.target.textContent.slice(0, 50) : '',
                timestamp: new Date().toISOString()
            };
            window.actionTracker.addAction(action);
        });
        
        // Track form inputs
        document.addEventListener('input', function(e) {
            if (e.target.type !== 'password') {
                var xpath = getXPath(e.target);
                var action = {
                    type: 'INPUT',
                    element: e.target.tagName + (e.target.id ? '#' + e.target.id : '') + 
                            (e.target.className ? '.' + e.target.className.replace(/\s+/g, '.') : ''),
                    xpath: xpath,
                    value: e.target.value.slice(0, 20) + (e.target.value.length > 20 ? '...' : ''),
                    timestamp: new Date().toISOString()
                };
                window.actionTracker.addAction(action);
            }
        });
        
        // XPath generator function
        function getXPath(element) {
            if (element.id) {
                return '//*[@id="' + element.id + '"]';
            }
            
            var xpath = '';
            while (element && element.nodeType === 1) {
                var index = 0;
                var siblings = element.parentNode ? element.parentNode.children : [];
                
                for (var i = 0; i < siblings.length; i++) {
                    var sibling = siblings[i];
                    if (sibling === element) {
                        xpath = '/' + element.tagName.toLowerCase() + '[' + (index + 1) + ']' + xpath;
                        break;
                    }
                    if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                        index++;
                    }
                }
                element = element.parentNode;
            }
            return xpath;
        }
        """
        
        try:
            self.driver.execute_script(click_script)
        except Exception as e:
            self.log_action("ERROR", f"Failed to setup click tracking: {str(e)}")
    
    def monitor_loop(self):
        """Main monitoring loop running in separate thread"""
        while self.is_monitoring:
            try:
                time.sleep(float(self.interval_var.get()))
                
                if not self.is_monitoring:
                    break
                
                # Check for user actions
                self.check_user_actions()
                
                # Check for page changes
                self.check_for_changes()
                
            except Exception as e:
                self.log_action("ERROR", f"Monitoring error: {str(e)}")
                time.sleep(5)  # Wait before retrying
    
    def check_user_actions(self):
        """Check for user actions tracked by JavaScript"""
        try:
            actions = self.driver.execute_script("return window.actionTracker ? window.actionTracker.actions.splice(0) : [];")
            
            for action in actions:
                self.log_user_action(action)
                
        except Exception as e:
            pass  # Silently handle JavaScript errors
    
    def log_user_action(self, action):
        """Log user action with XPath information"""
        action_type = action.get('type', 'UNKNOWN')
        element = action.get('element', 'Unknown element')
        xpath = action.get('xpath', 'No XPath')
        
        if action_type == 'CLICK':
            text = action.get('text', '').strip()
            description = f"Clicked on {element}"
            if text:
                description += f" with text '{text[:30]}...'" if len(text) > 30 else f" with text '{text}'"
        elif action_type == 'INPUT':
            value = action.get('value', '')
            description = f"Entered text in {element}: '{value}'"
        else:
            description = f"{action_type} on {element}"
        
        self.log_action(action_type, description, xpath)
    
    def check_for_changes(self):
        """Check for changes in the webpage"""
        if not self.driver:
            return
            
        try:
            current_state = self.capture_page_state()
            changes = self.compare_states(self.previous_state, current_state)
            
            if changes:
                self.log_action("CHANGE", f"Detected {len(changes)} page changes")
                self.log_changes(changes)
                self.previous_state = current_state
                
                if self.autosave_var.get():
                    self.auto_save_log()
            
            # Check for URL changes (navigation)
            current_url = self.driver.current_url
            if current_url != self.current_url:
                self.log_action("NAVIGATION", f"Page navigated from {self.current_url} to {current_url}")
                self.current_url = current_url
                self.previous_state = current_state  # Reset state on navigation
                
        except Exception as e:
            self.log_action("ERROR", f"Error checking for changes: {str(e)}")
    
    def capture_page_state(self):
        """Capture current state of the webpage"""
        try:
            # Get page source and basic info
            html = self.driver.page_source
            title = self.driver.title
            url = self.driver.current_url
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract key elements with their XPaths
            elements = {}
            
            # Find all interactive elements
            interactive_tags = ['a', 'button', 'input', 'select', 'textarea', 'form']
            for tag in interactive_tags:
                for i, element in enumerate(soup.find_all(tag)):
                    key = f"{tag}_{i}"
                    elements[key] = {
                        'tag': tag,
                        'text': element.get_text().strip()[:100],
                        'attrs': dict(element.attrs),
                        'xpath': self.generate_xpath_for_element(element, soup)
                    }
            
            # Create content hash for change detection
            content_hash = hashlib.md5(html.encode()).hexdigest()
            
            return {
                'html': html,
                'title': title,
                'url': url,
                'content_hash': content_hash,
                'elements': elements,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Error capturing page state: {str(e)}")
            return {}
    
    def generate_xpath_for_element(self, element, soup):
        """Generate XPath for a BeautifulSoup element"""
        try:
            if element.get('id'):
                return f'//*[@id="{element["id"]}"]'
            
            path_parts = []
            current = element
            
            while current and current.name:
                siblings = [s for s in current.parent.children if hasattr(s, 'name') and s.name == current.name] if current.parent else [current]
                if len(siblings) > 1:
                    index = siblings.index(current) + 1
                    path_parts.append(f"{current.name}[{index}]")
                else:
                    path_parts.append(current.name)
                current = current.parent
            
            return '/' + '/'.join(reversed(path_parts)) if path_parts else '//*'
            
        except:
            return '//*'
    
    def compare_states(self, old_state, new_state):
        """Compare two page states and return list of changes"""
        if not old_state or not new_state:
            return []
        
        changes = []
        
        # Check for content changes
        if old_state.get('content_hash') != new_state.get('content_hash'):
            changes.append({
                'type': 'CONTENT_CHANGE',
                'description': 'Page content has changed',
                'old_hash': old_state.get('content_hash'),
                'new_hash': new_state.get('content_hash')
            })
        
        # Check for title changes
        if old_state.get('title') != new_state.get('title'):
            changes.append({
                'type': 'TITLE_CHANGE',
                'description': f'Title changed from "{old_state.get("title")}" to "{new_state.get("title")}"'
            })
        
        # Check for element changes
        old_elements = old_state.get('elements', {})
        new_elements = new_state.get('elements', {})
        
        # Find removed elements
        for key in old_elements:
            if key not in new_elements:
                element = old_elements[key]
                changes.append({
                    'type': 'ELEMENT_REMOVED',
                    'description': f'{element["tag"].upper()} element removed',
                    'xpath': element.get('xpath', 'No XPath'),
                    'text': element.get('text', '')
                })
        
        # Find added elements
        for key in new_elements:
            if key not in old_elements:
                element = new_elements[key]
                changes.append({
                    'type': 'ELEMENT_ADDED',
                    'description': f'{element["tag"].upper()} element added',
                    'xpath': element.get('xpath', 'No XPath'),
                    'text': element.get('text', '')
                })
        
        # Find modified elements
        for key in set(old_elements.keys()) & set(new_elements.keys()):
            old_elem = old_elements[key]
            new_elem = new_elements[key]
            
            if old_elem.get('text') != new_elem.get('text'):
                changes.append({
                    'type': 'ELEMENT_MODIFIED',
                    'description': f'{new_elem["tag"].upper()} element text changed',
                    'xpath': new_elem.get('xpath', 'No XPath'),
                    'old_text': old_elem.get('text', ''),
                    'new_text': new_elem.get('text', '')
                })
        
        return changes
    
    def log_action(self, action_type, description, xpath=""):
        """Log an action to the display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {action_type}: {description}"
        
        if xpath:
            log_entry += f"\n    XPath: {xpath}"
        
        log_entry += "\n" + "-" * 80 + "\n"
        
        # Update GUI in main thread
        self.root.after(0, self._update_log_display, log_entry)
        
        # Store in memory
        self.action_log.append({
            'timestamp': timestamp,
            'type': action_type,
            'description': description,
            'xpath': xpath
        })
    
    def log_changes(self, changes):
        """Log detected changes to the changes tab"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        change_text = f"[{timestamp}] CHANGES DETECTED:\n"
        
        for i, change in enumerate(changes, 1):
            change_text += f"\n{i}. {change['type']}: {change['description']}"
            if 'xpath' in change:
                change_text += f"\n   XPath: {change['xpath']}"
            if 'text' in change and change['text']:
                change_text += f"\n   Text: {change['text'][:100]}..."
            change_text += "\n"
        
        change_text += "\n" + "=" * 80 + "\n"
        
        # Update changes display in main thread
        self.root.after(0, self._update_changes_display, change_text)
    
    def _update_log_display(self, text):
        """Update log display (called from main thread)"""
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
    
    def _update_changes_display(self, text):
        """Update changes display (called from main thread)"""
        self.changes_text.insert(tk.END, text)
        self.changes_text.see(tk.END)
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.is_monitoring = False
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        # Update GUI
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.refresh_btn.config(state=tk.DISABLED)
        
        self.status_var.set("Monitoring stopped.")
        self.log_action("SYSTEM", "Monitoring stopped")
    
    def save_log(self):
        """Save the action log to a file"""
        if not self.action_log:
            messagebox.showwarning("Warning", "No actions logged yet.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Action Log"
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.action_log, f, indent=2, ensure_ascii=False)
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write("Web Action Analyzer Log\n")
                        f.write("=" * 50 + "\n\n")
                        
                        for action in self.action_log:
                            f.write(f"[{action['timestamp']}] {action['type']}: {action['description']}\n")
                            if action.get('xpath'):
                                f.write(f"    XPath: {action['xpath']}\n")
                            f.write("-" * 80 + "\n")
                
                messagebox.showinfo("Success", f"Log saved to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {str(e)}")
    
    def auto_save_log(self):
        """Auto-save log with timestamp"""
        if not self.action_log:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"web_action_log_{timestamp}.txt"
            
            # Create logs directory if it doesn't exist
            if not os.path.exists("logs"):
                os.makedirs("logs")
            
            filepath = os.path.join("logs", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Web Action Analyzer Log\n")
                f.write("=" * 50 + "\n\n")
                
                for action in self.action_log:
                    f.write(f"[{action['timestamp']}] {action['type']}: {action['description']}\n")
                    if action.get('xpath'):
                        f.write(f"    XPath: {action['xpath']}\n")
                    f.write("-" * 80 + "\n")
            
            self.status_var.set(f"Auto-saved to {filepath}")
            
        except Exception as e:
            self.log_action("ERROR", f"Auto-save failed: {str(e)}")
    
    def clear_log(self):
        """Clear the action log"""
        if messagebox.askyesno("Confirm", "Clear all logged actions?"):
            self.action_log.clear()
            self.log_text.delete(1.0, tk.END)
            self.changes_text.delete(1.0, tk.END)
            self.xpath_text.delete(1.0, tk.END)
            self.status_var.set("Log cleared.")
    
    def run(self):
        """Start the GUI application"""
        # Add cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start the GUI loop
        self.root.mainloop()
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_monitoring:
            if messagebox.askokcancel("Quit", "Monitoring is active. Do you want to quit?"):
                self.stop_monitoring()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """Main function to run the Web Action Analyzer"""
    print("Web Action Analyzer")
    print("===================")
    print("This tool requires ChromeDriver to be installed.")
    print("Download from: https://chromedriver.chromium.org/")
    print("Make sure ChromeDriver is in your PATH or in the same directory as this script.")
    print()
    
    try:
        app = WebActionAnalyzer()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
    except Exception as e:
        print(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()