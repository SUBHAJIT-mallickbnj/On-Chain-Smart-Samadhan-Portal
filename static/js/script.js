// Frontend JavaScript for Complaint Classifier

document.addEventListener('DOMContentLoaded', function() {
    const complaintForm = document.getElementById('complaintForm');
    const submitBtn = document.getElementById('submitBtn');
    const complaintTextarea = document.getElementById('complaint');

    // Form submission handling
    if (complaintForm) {
        complaintForm.addEventListener('submit', function(e) {
            const complaintText = complaintTextarea.value.trim();
            
            // Validate complaint length
            if (complaintText.length < 10) {
                e.preventDefault();
                alert('Please enter a more detailed complaint (at least 10 characters).');
                return;
            }

            // Show loading state
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    }

    // Character counter for textarea
    if (complaintTextarea) {
        const charCounter = document.createElement('div');
        charCounter.className = 'form-text text-end';
        charCounter.id = 'charCounter';
        complaintTextarea.parentNode.appendChild(charCounter);

        function updateCharCounter() {
            const length = complaintTextarea.value.length;
            charCounter.textContent = `${length}/1000 characters`;
            
            if (length > 1000) {
                charCounter.classList.add('text-danger');
                complaintTextarea.classList.add('is-invalid');
            } else {
                charCounter.classList.remove('text-danger');
                complaintTextarea.classList.remove('is-invalid');
            }
        }

        complaintTextarea.addEventListener('input', updateCharCounter);
        updateCharCounter(); // Initial update
    }

    // Auto-resize textarea
    if (complaintTextarea) {
        complaintTextarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }

    // Add fade-in animation to results
    const resultCard = document.querySelector('.card.shadow');
    if (resultCard && window.location.pathname.includes('/classify')) {
        resultCard.classList.add('fade-in');
    }

    // API function for programmatic access
    window.classifyComplaint = function(complaintText) {
        return fetch('/api/classify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                complaint: complaintText
            })
        })
        .then(response => response.json())
        .catch(error => {
            console.error('Error:', error);
            return { error: 'Network error occurred' };
        });
    };

    // Table search functionality for history page
    const searchInput = document.getElementById('searchComplaints');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const complaintText = row.cells[1].textContent.toLowerCase();
                const department = row.cells[2].textContent.toLowerCase();
                
                if (complaintText.includes(filter) || department.includes(filter)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});

// Utility functions
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Show success message
        const toast = document.createElement('div');
        toast.className = 'alert alert-success position-fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.textContent = 'Copied to clipboard!';
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 2000);
    });
}

// Export for use in other scripts
window.ComplaintClassifier = {
    classifyComplaint: window.classifyComplaint,
    copyToClipboard: copyToClipboard
};