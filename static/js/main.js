document.addEventListener('DOMContentLoaded', () => {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    
    // Initialize datepickers
    initDatepickers();
    
    // Initialize rich text editors
    initRichTextEditors();
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Add event listeners to search forms
    initSearchForms();
    
    // Add event listeners to document generation forms
    initDocumentGeneration();
    
    // Add event listeners to research forms
    initResearchForms();
    
    // Handle case events calendar
    initCalendar();
});

function initDatepickers() {
    // For browsers that don't support input type="date"
    if (!Modernizr.inputtypes.date) {
        const datepickers = document.querySelectorAll('input[type="date"]');
        datepickers.forEach(input => {
            // Use a fallback datepicker library if needed
            // For simplicity, we'll just show a message
            input.title = 'Please enter date in YYYY-MM-DD format';
        });
    }
}

function initRichTextEditors() {
    // Simple rich text editor for textareas with class 'rich-editor'
    const editors = document.querySelectorAll('textarea.rich-editor');
    editors.forEach(editor => {
        // This is a placeholder - in a real app, you'd initialize a rich text editor
        // like TinyMCE, CKEditor, or Quill here
        editor.style.minHeight = '300px';
        editor.placeholder = 'Start typing here...';
    });
}

function initSearchForms() {
    const searchForms = document.querySelectorAll('.search-form');
    searchForms.forEach(form => {
        const input = form.querySelector('input[type="search"]');
        const clearBtn = form.querySelector('.clear-search');
        
        if (clearBtn && input) {
            clearBtn.addEventListener('click', () => {
                input.value = '';
                input.focus();
            });
        }
    });
}

function initDocumentGeneration() {
    // Toggle AI vs Template generation options
    const templateSelector = document.getElementById('template-selector');
    if (templateSelector) {
        templateSelector.addEventListener('change', function() {
            const selectedTemplate = this.value;
            
            // Hide all template forms
            document.querySelectorAll('.template-form').forEach(form => {
                form.classList.add('d-none');
            });
            
            // Show selected template form
            const selectedForm = document.getElementById(`${selectedTemplate}-form`);
            if (selectedForm) {
                selectedForm.classList.remove('d-none');
            }
        });
    }
    
    // Toggle AI vs Template contract generation
    const generationMethod = document.querySelectorAll('input[name="generation_method"]');
    generationMethod.forEach(radio => {
        radio.addEventListener('change', function() {
            const method = this.value;
            
            // Hide all generation forms
            document.querySelectorAll('.generation-form').forEach(form => {
                form.classList.add('d-none');
            });
            
            // Show selected generation form
            const selectedForm = document.getElementById(`${method}-generation-form`);
            if (selectedForm) {
                selectedForm.classList.remove('d-none');
            }
        });
    });
}

function initResearchForms() {
    // Handle court filter checkboxes
    const courtFilters = document.querySelectorAll('.court-filter');
    if (courtFilters.length > 0) {
        const selectAllBtn = document.getElementById('select-all-courts');
        const clearAllBtn = document.getElementById('clear-all-courts');
        
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', function(e) {
                e.preventDefault();
                courtFilters.forEach(checkbox => {
                    checkbox.checked = true;
                });
            });
        }
        
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', function(e) {
                e.preventDefault();
                courtFilters.forEach(checkbox => {
                    checkbox.checked = false;
                });
            });
        }
    }
    
    // Handle document analysis form
    const analyzeForm = document.getElementById('document-analysis-form');
    if (analyzeForm) {
        const loadingIndicator = document.getElementById('analysis-loading');
        
        analyzeForm.addEventListener('submit', function() {
            if (loadingIndicator) {
                loadingIndicator.classList.remove('d-none');
            }
        });
    }
}

function initCalendar() {
    // Handle calendar navigation
    const calendarNav = document.querySelectorAll('.calendar-nav');
    calendarNav.forEach(link => {
        link.addEventListener('click', function(e) {
            // This is a placeholder - in a real app, you might use AJAX
            // to fetch and update the calendar without a full page reload
        });
    });
    
    // Highlight today's date
    const today = new Date();
    const todayString = `${today.getFullYear()}-${(today.getMonth() + 1).toString().padStart(2, '0')}-${today.getDate().toString().padStart(2, '0')}`;
    const todayCell = document.querySelector(`.calendar-day[data-date="${todayString}"]`);
    
    if (todayCell) {
        todayCell.classList.add('today');
    }
}

// Function to confirm deletion
function confirmDelete(formId, itemName) {
    if (confirm(`Are you sure you want to delete this ${itemName}? This action cannot be undone.`)) {
        document.getElementById(formId).submit();
    }
    return false;
}
