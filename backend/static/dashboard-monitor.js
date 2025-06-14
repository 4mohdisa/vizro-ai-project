/**
 * Dashboard Chart Monitor
 * Adds diagnostic logging for chart loading and rendering
 */

(function() {
    // Run after page is fully loaded
    window.addEventListener('DOMContentLoaded', function() {
        console.log('🔍 Dashboard Monitor Initialized');
        
        // Track loaded charts to prevent duplicates
        const loadedCharts = new Set();
        
        // Observer to watch for chart containers being added to the DOM
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length) {
                    checkForCharts();
                }
            });
        });
        
        // Start observing the document body for chart containers
        observer.observe(document.body, { childList: true, subtree: true });
        
        // Function to find and log chart data
        function checkForCharts() {
            // Look for Plotly chart divs
            const chartDivs = document.querySelectorAll('[id^="chart-"]');
            chartDivs.forEach(function(chartDiv, i) {
                const chartId = chartDiv.id;
                
                // Only process charts we haven't seen yet
                if (!loadedCharts.has(chartId)) {
                    console.log(`📊 Found chart ${i} with ID: ${chartId}`);
                    loadedCharts.add(chartId);
                    
                    // Set up a watcher for Plotly data
                    const checkInterval = setInterval(function() {
                        if (chartDiv._fullData) {
                            clearInterval(checkInterval);
                            
                            // Log chart data details
                            const chartData = chartDiv._fullData;
                            console.log(`🔄 Loading chart index ${i}, type: ${chartData[0]?.type || 'unknown'}, data points: ${chartData[0]?.x?.length || 'N/A'}`);
                            
                            // Add visual indicator of chart type
                            const typeIndicator = document.createElement('div');
                            typeIndicator.className = 'chart-type-badge';
                            typeIndicator.textContent = chartData[0]?.type || 'unknown';
                            typeIndicator.style.cssText = 'position:absolute;top:0;right:0;background:#2563eb;color:white;padding:4px 8px;border-radius:4px;font-size:12px;z-index:999;';
                            chartDiv.style.position = 'relative';
                            chartDiv.appendChild(typeIndicator);
                        }
                    }, 100);
                    
                    // Clean up interval after 5 seconds to prevent leaks
                    setTimeout(function() {
                        clearInterval(checkInterval);
                    }, 5000);
                }
            });
        }
        
        // Initial check
        setTimeout(checkForCharts, 500);
        
        // Also check when opening the dashboard via the button
        const viewDashboardBtn = document.getElementById('view-dashboard-btn');
        if (viewDashboardBtn) {
            viewDashboardBtn.addEventListener('click', function() {
                console.log('🔗 Opening dashboard via button click');
            });
        }
    });
})();
