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

