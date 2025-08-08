#!/usr/bin/env python3
"""
Web Action Analyzer - Capture browser actions and generate automation tests
Designed for BrowserStack integration
"""

import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import threading
import queue
import re
from typing import List, Dict, Any
import openai  # You'll need to install: pip install openai
from dataclasses import dataclass


@dataclass
class ActionRecord:
    """Data class to store captured actions"""
    timestamp: str
    action_type: str
    element_xpath: str
    element_text: str
    element_tag: str
    element_attributes: dict
    page_url: str
    description: str
    screenshot_path: str = None


class XPathGenerator:
    """Utility class to generate robust XPath selectors"""
    
    @staticmethod
    def generate_xpath(element):
        """Generate multiple XPath options for an element"""
        xpaths = []
        
        # Get element attributes
        tag_name = element.tag_name
        element_id = element.get_attribute('id')
        class_name = element.get_attribute('class')
        name = element.get_attribute('name')
        text = element.text.strip() if element.text else ''
        
        # ID-based XPath (most reliable)
        if element_id:
            xpaths.append(f"//*[@id='{element_id}']")
        
        # Name-based XPath
        if name:
            xpaths.append(f"//{tag_name}[@name='{name}']")
        
        # Class-based XPath
        if class_name:
            classes = class_name.split()
            if len(classes) == 1:
                xpaths.append(f"//{tag_name}[@class='{class_name}']")
            else:
                # Use contains for multiple classes
                class_conditions = " and ".join([f"contains(@class, '{cls}')" for cls in classes])
                xpaths.append(f"//{tag_name}[{class_conditions}]")
        
        # Text-based XPath
        if text and len(text) < 50:
            xpaths.append(f"//{tag_name}[text()='{text}']")
            xpaths.append(f"//{tag_name}[contains(text(), '{text[:20]}')]")
        
        # Generate relative XPath
        try:
            relative_xpath = XPathGenerator._generate_relative_xpath(element)
            if relative_xpath:
                xpaths.append(relative_xpath)
        except:
            pass
        
        return xpaths[0] if xpaths else f"//{tag_name}"
    
    @staticmethod
    def _generate_relative_xpath(element):
        """Generate relative XPath based on element hierarchy"""
        driver = element._parent
        script = """
        function getXPath(element) {
            if (element.id !== '') {
                return "//*[@id='" + element.id + "']";
            }
            if (element === document.body) {
                return '/html/body';
            }
            
            var ix = 0;
            var siblings = element.parentNode.childNodes;
            for (var i = 0; i < siblings.length; i++) {
                var sibling = siblings[i];
                if (sibling === element) {
                    return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                }
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                    ix++;
                }
            }
        }
        return getXPath(arguments[0]);
        """
        return driver.execute_script(script, element)


class LLMAnalyzer:
    """Analyze captured actions using LLM and convert to natural language"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        if api_key:
            openai.api_key = api_key
    
    def analyze_action(self, action: ActionRecord) -> str:
        """Convert action to natural language description"""
        if not self.api_key:
            return self._fallback_analysis(action)
        
        try:
            prompt = f"""
            Convert this web browser action to natural language for test documentation:
            
            Action Type: {action.action_type}
            Element: {action.element_tag} with text "{action.element_text}"
            XPath: {action.element_xpath}
            URL: {action.page_url}
            Attributes: {json.dumps(action.element_attributes, indent=2)}
            
            Provide a clear, concise description suitable for automation testing documentation.
            Focus on user intent and business logic rather than technical details.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Analysis failed: {e}")
            return self._fallback_analysis(action)
    
    def _fallback_analysis(self, action: ActionRecord) -> str:
        """Fallback analysis without LLM"""
        if action.action_type == 'click':
            if action.element_text:
                return f"Click on '{action.element_text}' button/link"
            else:
                return f"Click on {action.element_tag} element"
        elif action.action_type == 'input':
            return f"Enter text in {action.element_text or action.element_tag} field"
        elif action.action_type == 'navigate':
            return f"Navigate to {action.page_url}"
        elif action.action_type == 'scroll':
            return "Scroll page"
        else:
            return f"Perform {action.action_type} action"
    
    def generate_test_script(self, actions: List[ActionRecord]) -> str:
        """Generate complete test script from actions"""
        script_lines = [
            "from selenium import webdriver",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait",
            "from selenium.webdriver.support import expected_conditions as EC",
            "import time",
            "",
            "def test_recorded_actions():",
            "    \"\"\"Generated test case from recorded actions\"\"\"",
            "    driver = webdriver.Chrome()",
            "    wait = WebDriverWait(driver, 10)",
            "    ",
            "    try:"
        ]
        
        for i, action in enumerate(actions):
            comment = f"        # Step {i+1}: {self.analyze_action(action)}"
            script_lines.append(comment)
            
            if action.action_type == 'navigate':
                script_lines.append(f"        driver.get('{action.page_url}')")
            elif action.action_type == 'click':
                script_lines.append(f"        element = wait.until(EC.element_to_be_clickable((By.XPATH, \"{action.element_xpath}\")))")
                script_lines.append("        element.click()")
            elif action.action_type == 'input':
                script_lines.append(f"        element = wait.until(EC.presence_of_element_located((By.XPATH, \"{action.element_xpath}\")))")
                script_lines.append("        element.clear()")
                script_lines.append(f"        element.send_keys('TEST_INPUT')")  # Placeholder
            
            script_lines.append("        time.sleep(1)")
            script_lines.append("")
        
        script_lines.extend([
            "    except Exception as e:",
            "        print(f'Test failed: {e}')",
            "        raise",
            "    finally:",
            "        driver.quit()",
            "",
            "if __name__ == '__main__':",
            "    test_recorded_actions()"
        ])
        
        return "\n".join(script_lines)


class ActionRecorder:
    """Core class to record browser actions"""
    
    def __init__(self):
        self.driver = None
        self.actions = []
        self.is_recording = False
        self.action_queue = queue.Queue()
        self.screenshot_counter = 0
    
    def setup_driver(self, browser_type="chrome"):
        """Initialize WebDriver"""
        try:
            if browser_type == "chrome":
                options = Options()
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                self.driver = webdriver.Chrome(options=options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Inject JavaScript to monitor actions
            self._inject_monitoring_script()
            return True
        except Exception as e:
            print(f"Driver setup failed: {e}")
            return False
    
    def _inject_monitoring_script(self):
        """Inject JavaScript to monitor user interactions"""
        monitoring_script = """
        window.recordedActions = [];
        
        // Monitor clicks
        document.addEventListener('click', function(event) {
            window.recordedActions.push({
                type: 'click',
                element: event.target,
                timestamp: Date.now(),
                x: event.clientX,
                y: event.clientY
            });
        }, true);
        
        // Monitor input changes
        document.addEventListener('input', function(event) {
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                window.recordedActions.push({
                    type: 'input',
                    element: event.target,
                    value: event.target.value,
                    timestamp: Date.now()
                });
            }
        }, true);
        
        // Monitor form submissions
        document.addEventListener('submit', function(event) {
            window.recordedActions.push({
                type: 'submit',
                element: event.target,
                timestamp: Date.now()
            });
        }, true);
        
        // Monitor navigation
        let currentUrl = location.href;
        setInterval(function() {
            if (location.href !== currentUrl) {
                window.recordedActions.push({
                    type: 'navigate',
                    url: location.href,
                    timestamp: Date.now()
                });
                currentUrl = location.href;
            }
        }, 1000);
        """
        
        self.driver.execute_script(monitoring_script)
    
    def start_recording(self):
        """Start recording actions"""
        if not self.driver:
            return False
        
        self.is_recording = True
        self.actions = []
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_actions)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        return True
    
    def stop_recording(self):
        """Stop recording actions"""
        self.is_recording = False
        time.sleep(1)  # Wait for last actions to be captured
        return self.actions
    
    def _monitor_actions(self):
        """Monitor and capture actions in background thread"""
        while self.is_recording:
            try:
                # Get actions from JavaScript
                js_actions = self.driver.execute_script("return window.recordedActions.splice(0);")
                
                for js_action in js_actions:
                    action_record = self._create_action_record(js_action)
                    if action_record:
                        self.actions.append(action_record)
                        self.action_queue.put(action_record)
                
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                print(f"Monitoring error: {e}")
                break
    
    def _create_action_record(self, js_action) -> ActionRecord:
        """Create ActionRecord from JavaScript action data"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if js_action['type'] == 'navigate':
                return ActionRecord(
                    timestamp=timestamp,
                    action_type='navigate',
                    element_xpath='',
                    element_text='',
                    element_tag='',
                    element_attributes={},
                    page_url=js_action['url'],
                    description=f"Navigated to {js_action['url']}"
                )
            
            # For other actions, find the element
            element = js_action['element']
            element_obj = self.driver.execute_script("return arguments[0];", element)
            
            if not element_obj:
                return None
            
            # Generate XPath
            xpath = XPathGenerator.generate_xpath(element_obj)
            
            # Get element details
            tag_name = element_obj.tag_name
            text = element_obj.text.strip() if element_obj.text else ''
            
            attributes = {}
            for attr in ['id', 'class', 'name', 'type', 'value', 'href']:
                value = element_obj.get_attribute(attr)
                if value:
                    attributes[attr] = value
            
            # Take screenshot for this action
            screenshot_path = self._take_screenshot()
            
            return ActionRecord(
                timestamp=timestamp,
                action_type=js_action['type'],
                element_xpath=xpath,
                element_text=text,
                element_tag=tag_name,
                element_attributes=attributes,
                page_url=self.driver.current_url,
                description=f"{js_action['type']} on {tag_name}",
                screenshot_path=screenshot_path
            )
            
        except Exception as e:
            print(f"Error creating action record: {e}")
            return None
    
    def _take_screenshot(self) -> str:
        """Take screenshot for the current action"""
        try:
            self.screenshot_counter += 1
            filename = f"screenshot_{self.screenshot_counter}_{int(time.time())}.png"
            screenshot_path = f"screenshots/{filename}"
            self.driver.save_screenshot(screenshot_path)
            return screenshot_path
        except:
            return None
    
    def navigate_to(self, url: str):
        """Navigate to a specific URL"""
        if self.driver:
            self.driver.get(url)
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()


class WebActionAnalyzerGUI:
    """Main GUI application"""
    
    def __init__(self):
        self.recorder = ActionRecorder()
        self.llm_analyzer = None  # Will be initialized with API key
        
        self.root = tk.Tk()
        self.root.title("Web Action Analyzer - BrowserStack Integration")
        self.root.geometry("1200x800")
        
        self.setup_gui()
        
        # Create screenshots directory
        import os
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
    
    def setup_gui(self):
        """Setup the GUI components"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Recording tab
        recording_frame = ttk.Frame(notebook)
        notebook.add(recording_frame, text="Recording")
        self.setup_recording_tab(recording_frame)
        
        # Analysis tab
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Analysis")
        self.setup_analysis_tab(analysis_frame)
        
        # Export tab
        export_frame = ttk.Frame(notebook)
        notebook.add(export_frame, text="Export")
        self.setup_export_tab(export_frame)
    
    def setup_recording_tab(self, parent):
        """Setup recording controls"""
        # Configuration frame
        config_frame = ttk.LabelFrame(parent, text="Configuration")
        config_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(config_frame, text="OpenAI API Key:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.api_key_entry = ttk.Entry(config_frame, show='*', width=50)
        self.api_key_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Start URL:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.url_entry = ttk.Entry(config_frame, width=50)
        self.url_entry.insert(0, "https://example.com")
        self.url_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.LabelFrame(parent, text="Recording Controls")
        control_frame.pack(fill='x', padx=5, pady=5)
        
        self.setup_button = ttk.Button(control_frame, text="Setup Browser", command=self.setup_browser)
        self.setup_button.pack(side='left', padx=5, pady=5)
        
        self.start_button = ttk.Button(control_frame, text="Start Recording", command=self.start_recording, state='disabled')
        self.start_button.pack(side='left', padx=5, pady=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Recording", command=self.stop_recording, state='disabled')
        self.stop_button.pack(side='left', padx=5, pady=5)
        
        self.navigate_button = ttk.Button(control_frame, text="Navigate to URL", command=self.navigate_to_url, state='disabled')
        self.navigate_button.pack(side='left', padx=5, pady=5)
        
        # Status display
        status_frame = ttk.LabelFrame(parent, text="Status")
        status_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=15)
        self.status_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log_message("Web Action Analyzer initialized. Configure settings and click 'Setup Browser' to begin.")
    
    def setup_analysis_tab(self, parent):
        """Setup analysis display"""
        # Actions list
        actions_frame = ttk.LabelFrame(parent, text="Captured Actions")
        actions_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Treeview for actions
        columns = ('Timestamp', 'Action', 'Element', 'XPath', 'Description')
        self.actions_tree = ttk.Treeview(actions_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.actions_tree.heading(col, text=col)
            self.actions_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(actions_frame, orient='vertical', command=self.actions_tree.yview)
        self.actions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.actions_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')
        
        # Analysis button
        analyze_button = ttk.Button(actions_frame, text="Analyze with LLM", command=self.analyze_actions)
        analyze_button.pack(pady=5)
    
    def setup_export_tab(self, parent):
        """Setup export options"""
        export_frame = ttk.LabelFrame(parent, text="Export Options")
        export_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(export_frame, text="Export as JSON", command=self.export_json).pack(side='left', padx=5, pady=5)
        ttk.Button(export_frame, text="Export as Test Script", command=self.export_test_script).pack(side='left', padx=5, pady=5)
        ttk.Button(export_frame, text="Export Report", command=self.export_report).pack(side='left', padx=5, pady=5)
        
        # Preview
        preview_frame = ttk.LabelFrame(parent, text="Export Preview")
        preview_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.export_preview = scrolledtext.ScrolledText(preview_frame)
        self.export_preview.pack(fill='both', expand=True, padx=5, pady=5)
    
    def log_message(self, message):
        """Add message to status log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def setup_browser(self):
        """Setup browser driver"""
        self.log_message("Setting up browser driver...")
        
        if self.recorder.setup_driver():
            self.log_message("Browser driver setup successful!")
            self.start_button.config(state='normal')
            self.navigate_button.config(state='normal')
            
            # Initialize LLM analyzer if API key provided
            api_key = self.api_key_entry.get().strip()
            if api_key:
                self.llm_analyzer = LLMAnalyzer(api_key)
                self.log_message("LLM analyzer initialized with API key.")
            else:
                self.log_message("No API key provided - using fallback analysis.")
        else:
            self.log_message("Failed to setup browser driver. Check ChromeDriver installation.")
    
    def navigate_to_url(self):
        """Navigate to specified URL"""
        url = self.url_entry.get().strip()
        if url:
            self.recorder.navigate_to(url)
            self.log_message(f"Navigated to: {url}")
    
    def start_recording(self):
        """Start recording actions"""
        if self.recorder.start_recording():
            self.log_message("Recording started! Perform actions in the browser window.")
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
            # Start action monitoring in GUI
            self.monitor_actions()
    
    def stop_recording(self):
        """Stop recording actions"""
        actions = self.recorder.stop_recording()
        self.log_message(f"Recording stopped! Captured {len(actions)} actions.")
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        self.update_actions_display(actions)
    
    def monitor_actions(self):
        """Monitor actions during recording"""
        if self.recorder.is_recording:
            try:
                while not self.recorder.action_queue.empty():
                    action = self.recorder.action_queue.get_nowait()
                    self.log_message(f"Captured: {action.action_type} - {action.description}")
            except queue.Empty:
                pass
            
            # Schedule next check
            self.root.after(500, self.monitor_actions)
    
    def update_actions_display(self, actions):
        """Update the actions tree view"""
        # Clear existing items
        for item in self.actions_tree.get_children():
            self.actions_tree.delete(item)
        
        # Add new actions
        for action in actions:
            self.actions_tree.insert('', 'end', values=(
                action.timestamp,
                action.action_type,
                f"{action.element_tag}: {action.element_text[:30]}...",
                action.element_xpath[:50] + "..." if len(action.element_xpath) > 50 else action.element_xpath,
                action.description[:50] + "..." if len(action.description) > 50 else action.description
            ))
    
    def analyze_actions(self):
        """Analyze captured actions with LLM"""
        if not self.recorder.actions:
            messagebox.showwarning("No Actions", "No actions to analyze. Please record some actions first.")
            return
        
        if not self.llm_analyzer:
            self.llm_analyzer = LLMAnalyzer()  # Use fallback analysis
        
        self.log_message("Analyzing actions with LLM...")
        
        # Analyze each action
        for action in self.recorder.actions:
            enhanced_description = self.llm_analyzer.analyze_action(action)
            action.description = enhanced_description
        
        # Update display
        self.update_actions_display(self.recorder.actions)
        self.log_message("Analysis complete!")
    
    def export_json(self):
        """Export actions as JSON"""
        if not self.recorder.actions:
            messagebox.showwarning("No Data", "No actions to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            export_data = []
            for action in self.recorder.actions:
                export_data.append({
                    'timestamp': action.timestamp,
                    'action_type': action.action_type,
                    'element_xpath': action.element_xpath,
                    'element_text': action.element_text,
                    'element_tag': action.element_tag,
                    'element_attributes': action.element_attributes,
                    'page_url': action.page_url,
                    'description': action.description,
                    'screenshot_path': action.screenshot_path
                })
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            self.log_message(f"Exported JSON to: {filename}")
    
    def export_test_script(self):
        """Export actions as test script"""
        if not self.recorder.actions:
            messagebox.showwarning("No Data", "No actions to export.")
            return
        
        if not self.llm_analyzer:
            self.llm_analyzer = LLMAnalyzer()
        
        script_content = self.llm_analyzer.generate_test_script(self.recorder.actions)
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(script_content)
            
            self.log_message(f"Exported test script to: {filename}")
            
            # Show preview
            self.export_preview.delete(1.0, tk.END)
            self.export_preview.insert(1.0, script_content)
    
    def export_report(self):
        """Export detailed report"""
        if not self.recorder.actions:
            messagebox.showwarning("No Data", "No actions to export.")
            return
        
        report_content = self._generate_report()
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(report_content)
            
            self.log_message(f"Exported report to: {filename}")
            
            # Show preview
            self.export_preview.delete(1.0, tk.END)
            self.export_preview.insert(1.0, report_content)
    
    def _generate_report(self) -> str:
        """Generate detailed test report"""
        report_lines = [
            "WEB ACTION ANALYSIS REPORT",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Actions Captured: {len(self.recorder.actions)}",
            "",
            "SUMMARY:",
            "--------"
        ]
        
        # Action type summary
        action_counts = {}
        for action in self.recorder.actions:
            action_counts[action.action_type] = action_counts.get(action.action_type, 0) + 1
        
        for action_type, count in action_counts.items():
            report_lines.append(f"- {action_type.title()}: {count}")
        
        report_lines.extend([
            "",
            "DETAILED ACTIONS:",
            "-" * 20
        ])
        
        # Detailed action list
        for i, action in enumerate(self.recorder.actions, 1):
            report_lines.extend([
                f"{i}. [{action.timestamp}] {action.action_type.upper()}",
                f"   Description: {action.description}",
                f"   Element: {action.element_tag} - '{action.element_text}'",
                f"   XPath: {action.element_xpath}",
                f"   URL: {action.page_url}",
                ""
            ])
        
        return "\n".join(report_lines)
    
    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        finally:
            # Cleanup
            self.recorder.cleanup()


def main():
    """Main entry point"""
    app = WebActionAnalyzerGUI()
    app.run()


if __name__ == "__main__":
    main()