document.addEventListener('DOMContentLoaded', function() {

    // Handle Feedback Form Validation
    const feedbackForm = document.querySelector('.feedback-section form');
    feedbackForm.addEventListener('submit', function(event) {
        const feedbackTextarea = feedbackForm.querySelector('textarea[name="feedback"]');
        
        // Ensure that feedback isn't empty
        if (feedbackTextarea.value.trim() === '') {
            alert('Please provide feedback before submitting!');
            event.preventDefault();  // Prevent form submission if empty
        }
    });

    // Toggle visibility of the audit trail table
    const auditTrailSection = document.querySelector('.audit-trail-section h2');
    const auditTrailTable = document.querySelector('.audit-trail-table');
    
    auditTrailSection.addEventListener('click', function() {
        // Toggle the table's visibility by changing its display style
        if (auditTrailTable.style.display === 'none' || auditTrailTable.style.display === '') {
            auditTrailTable.style.display = 'block';
        } else {
            auditTrailTable.style.display = 'none';
        }
    });

    // Format the current date and display it in the feedback section
    const currentDate = new Date();
    const formattedDate = currentDate.toISOString().split('T')[0]; // YYYY-MM-DD format
    const reportSummaryElement = document.querySelector('.report-summary');
    if (reportSummaryElement) {
        const dateElement = document.createElement('li');
        dateElement.innerHTML = `<strong>Submission Date:</strong> ${formattedDate}`;
        reportSummaryElement.appendChild(dateElement);
    }

});
