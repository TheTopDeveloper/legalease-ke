// Floating Action Button Functionality
document.addEventListener('DOMContentLoaded', function() {
    const fabContainer = document.querySelector('.fab-container');
    
    if (fabContainer) {
        const fabMain = fabContainer.querySelector('.fab-main');
        
        // Toggle the active class when the main button is clicked
        fabMain.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            fabContainer.classList.toggle('active');
        });
        
        // Close the menu when clicking elsewhere on the page
        document.addEventListener('click', function(e) {
            if (!fabContainer.contains(e.target)) {
                fabContainer.classList.remove('active');
            }
        });
        
        // Prevent menu from closing when clicking on menu items
        const fabOptions = fabContainer.querySelector('.fab-options');
        if (fabOptions) {
            fabOptions.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        }
        
        // Add keyboard accessibility
        fabMain.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fabContainer.classList.toggle('active');
            }
        });
        
        // Close on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && fabContainer.classList.contains('active')) {
                fabContainer.classList.remove('active');
            }
        });
    }
});