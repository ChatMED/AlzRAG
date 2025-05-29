
// Execute this in browser console to debug dropdown population
(function debugDropdown() {
    console.log("Debugging dropdown population...");
    
    // Find all dropdown elements 
    const dropdowns = document.querySelectorAll('select, [role="combobox"], .dropdown');
    console.log(`Found ${dropdowns.length} potential dropdown elements`);
    
    // Inspect each dropdown
    dropdowns.forEach((dropdown, index) => {
        console.log(`Dropdown ${index}:`, dropdown);
        console.log(`- tagName: ${dropdown.tagName}`);
        console.log(`- id: ${dropdown.id}`);
        console.log(`- class: ${dropdown.className}`);
        
        // Try to find options
        const options = dropdown.querySelectorAll('option') || 
                        dropdown.querySelectorAll('[role="option"]') || 
                        dropdown.querySelectorAll('li');
        
        if (options.length) {
            console.log(`- options count: ${options.length}`);
            console.log(`- option samples:`, options[0], options.length > 1 ? options[1] : null);
        }
        
        // Check for React properties
        for (const key in dropdown) {
            if (key.startsWith('__react')) {
                console.log(`- Has React internals: ${key}`);
            }
        }
    });
    
    // Look for RAG-related elements
    const ragElements = Array.from(document.querySelectorAll('*')).filter(el => {
        const text = el.textContent.toLowerCase();
        return text.includes('rag') || text.includes('prompt');
    });
    
    console.log(`Found ${ragElements.length} elements with RAG or prompt text`);
    ragElements.slice(0, 5).forEach((el, i) => {
        console.log(`RAG Element ${i}:`, el);
    });
    
    // Check localStorage for config
    console.log("Checking localStorage for configuration...");
    Object.keys(localStorage).forEach(key => {
        if (key.toLowerCase().includes('prompt') || key.toLowerCase().includes('rag') || 
            key.toLowerCase().includes('config') || key.toLowerCase().includes('dropdown')) {
            console.log(`- localStorage key: ${key}`);
            try {
                const value = JSON.parse(localStorage.getItem(key));
                console.log(`  Value:`, value);
            } catch(e) {
                console.log(`  Value: ${localStorage.getItem(key)}`);
            }
        }
    });
    
    // Monkey patch fetch to log prompt-related API calls
    const originalFetch = window.fetch;
    window.fetch = async function(url, options) {
        if (url.toString().includes('prompt') || url.toString().includes('rag')) {
            console.log(`Intercepted fetch to ${url}`, options);
        }
        return originalFetch.apply(this, arguments);
    };
    console.log("Fetch API patched to monitor prompt-related calls");
    
    console.log("Debug complete - check the results above");
})();
