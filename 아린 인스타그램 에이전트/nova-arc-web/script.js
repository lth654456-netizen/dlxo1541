// Intersection Observer for Scroll Animations
const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.2
};

const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.remove('hidden');
            // Adding a brief system log effect when section appears
            const titleElement = entry.target.querySelector('.section-title');
            if (titleElement) {
                const originalText = titleElement.innerText;
                titleElement.innerText = "LOADING...";
                setTimeout(() => {
                    titleElement.innerText = originalText;
                }, 300);
            }
        }
    });
}, observerOptions);

document.querySelectorAll('section').forEach((section) => {
    observer.observe(section);
});

// Update active nav link based on scroll
const sections = document.querySelectorAll('section');
const navLinks = document.querySelectorAll('.nav-links a');

window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        if (pageYOffset >= (sectionTop - sectionHeight / 3)) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href').includes(current)) {
            link.classList.add('active');
        }
    });
});

// Form Submission effect
const form = document.querySelector('.cyber-form');
if (form) {
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const btn = form.querySelector('.transmit-btn');
        const originalText = btn.innerText;
        btn.innerText = "TRANSMITTING...";
        btn.style.color = "#000";
        btn.style.backgroundColor = "var(--accent-cyan)";
        
        setTimeout(() => {
            btn.innerText = "PACKET DELIVERED";
            setTimeout(() => {
                btn.innerText = originalText;
                btn.style.color = "";
                btn.style.backgroundColor = "";
                form.reset();
            }, 2000);
        }, 1500);
    });
}
