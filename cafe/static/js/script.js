document.addEventListener('DOMContentLoaded', () => {
    // Mobile Menu Toggle (unchanged)
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            hamburger.textContent = navLinks.classList.contains('active') ? '✕' : '☰';
        });
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    navLinks.classList.remove('active');
                    hamburger.textContent = '☰';
                }
            });
        });
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && !navLinks.contains(e.target) && !hamburger.contains(e.target)) {
                navLinks.classList.remove('active');
                hamburger.textContent = '☰';
            }
        });
    }

    // Smooth Scrolling (unchanged)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    // Form Handling (Updated to handle HTML responses)
    const forms = ['table-form', 'ps-room-form', 'order-form', 'add-table-form', 'add-room-form', 'add-item-form'];
    forms.forEach(formId => {
        const form = document.getElementById(formId);
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const submitButton = form.querySelector('button[type="submit"]');
                submitButton.disabled = true;
                submitButton.textContent = 'Processing...';
                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: formData,
                        headers: { 
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });
                    const text = await response.text(); // Get raw HTML response
                    if (response.ok) {
                        // Check if the response contains an error message
                        if (text.includes('class="error"')) {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(text, 'text/html');
                            const errorMessage = doc.querySelector('.error')?.textContent || 'An error occurred';
                            throw new Error(errorMessage);
                        } else {
                            form.reset();
                            showFeedback('Action completed successfully!', 'success');
                            // Reload page to reflect changes
                            setTimeout(() => window.location.reload(), 1000); // Delay for feedback visibility
                        }
                    } else {
                        throw new Error('Request failed with status ' + response.status);
                    }
                } catch (error) {
                    showFeedback(error.message, 'error');
                } finally {
                    submitButton.disabled = false;
                    submitButton.textContent = formId.includes('add') ? 'Add' : 'Submit'; // Restore original text
                }
            });
        }
    });

    // Admin Edit/Delete (unchanged, but could be updated similarly if needed)
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const type = btn.closest('.section').querySelector('h2').textContent.includes('Tables') ? 'table' :
                         btn.closest('.section').querySelector('h2').textContent.includes('Rooms') ? 'room' : 'item';
            const number = btn.dataset.number || '';
            const name = btn.dataset.name || '';
            const price = btn.dataset.price || '';
            const isAvailable = btn.dataset.available === 'true';
            const newNumber = prompt(`Edit ${type} ${number || name}`, number || name);
            if (newNumber !== null) {
                const newPrice = type === 'item' ? prompt('Edit Price', price) : null;
                const newAvailable = confirm('Is it available?');
                fetch(`/cafe/admin/edit_${type}/${id}/`, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') },
                    body: JSON.stringify({ number: newNumber, price: newPrice, is_available: newAvailable })
                }).then(response => response.json())
                  .then(result => {
                      if (result.message) {
                          showFeedback(result.message, 'success');
                          window.location.reload();
                      } else {
                          showFeedback(result.error, 'error');
                      }
                  });
            }
        });
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this?')) {
                const id = btn.dataset.id;
                const type = btn.closest('.section').querySelector('h2').textContent.includes('Tables') ? 'table' :
                             btn.closest('.section').querySelector('h2').textContent.includes('Rooms') ? 'room' : 'item';
                fetch(`/cafe/admin/delete_${type}/${id}/`, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') }
                }).then(response => response.json())
                  .then(result => {
                      if (result.message) {
                          showFeedback(result.message, 'success');
                          window.location.reload();
                      } else {
                          showFeedback(result.error, 'error');
                      }
                  });
            }
        });
    });

    // Feedback Notification (unchanged)
    function showFeedback(message, type) {
        const feedback = document.createElement('div');
        feedback.className = `feedback feedback-${type}`;
        feedback.textContent = message;
        Object.assign(feedback.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            padding: '15px 20px',
            background: type === 'success' ? '#aa5825' : '#d89b6e',
            color: '#e4d3c1',
            borderRadius: '8px',
            boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
            zIndex: '2000',
            opacity: '0',
            transition: 'opacity 0.5s ease'
        });
        document.body.appendChild(feedback);
        setTimeout(() => { feedback.style.opacity = '1'; }, 10);
        setTimeout(() => {
            feedback.style.opacity = '0';
            setTimeout(() => feedback.remove(), 500);
        }, 3000);
    }

    // CSRF Token Helper (unchanged)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Lazy Load (unchanged)
    const sections = document.querySelectorAll('.hero, .services, .testimonials');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    sections.forEach(section => {
        section.classList.add('fade-in');
        observer.observe(section);
    });
    const style = document.createElement('style');
    style.textContent = `
        .fade-in { opacity: 0; transform: translateY(20px); transition: opacity 0.5s ease, transform 0.5s ease; }
        .fade-in.visible { opacity: 1; transform: translateY(0); }
    `;
    document.head.appendChild(style);
});