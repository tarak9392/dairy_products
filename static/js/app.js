// Dairy Application Client Logic

const DairyApp = {
    cart: [],
    
    init() {
        this.loadCart();
        this.updateCartBadge();
    },

    // --- Cart Management ---
    loadCart() {
        try {
            const saved = localStorage.getItem('dairy_cart');
            if (saved) {
                this.cart = JSON.parse(saved);
            }
        } catch (e) {
            this.cart = [];
        }
    },

    saveCart() {
        localStorage.setItem('dairy_cart', JSON.stringify(this.cart));
        this.updateCartBadge();
    },

    addToCart(product, quantity = 1, isSubscription = false) {
        const existingIndex = this.cart.findIndex(item => item.id === product.id && item.isSubscription === isSubscription);
        if (existingIndex > -1) {
            this.cart[existingIndex].quantity += quantity;
        } else {
            this.cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                unit: product.unit,
                image_symbol: product.image_symbol,
                quantity: quantity,
                isSubscription: isSubscription
            });
        }
        this.saveCart();
        this.showToast(`Added ${product.name} to cart!`, 'success');
    },

    removeFromCart(index) {
        this.cart.splice(index, 1);
        this.saveCart();
        if (typeof renderCartPage === 'function') renderCartPage();
    },

    updateCartQuantity(index, newQty) {
        if (newQty <= 0) {
            this.removeFromCart(index);
        } else {
            this.cart[index].quantity = newQty;
            this.saveCart();
            if (typeof renderCartPage === 'function') renderCartPage();
        }
    },

    clearCart() {
        this.cart = [];
        this.saveCart();
    },

    getCartTotal() {
        return this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    },

    updateCartBadge() {
        const badges = document.querySelectorAll('.cart-count');
        const count = this.cart.reduce((sum, item) => sum + item.quantity, 0);
        badges.forEach(b => b.textContent = count);
    },

    // --- Toast Alerts ---
    showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '⚠️';

        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    DairyApp.init();

    // IntersectionObserver for Smooth Scroll Reveal Animations
    const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
    const scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('scroll-reveal-active');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.card, .product-card, .footer-cinematic, .hero, .section-title').forEach(el => {
        el.classList.add('scroll-reveal');
        scrollObserver.observe(el);
    });

    // Magnetic Button Physics
    document.querySelectorAll('.footer-glass-pill-btn, .btn-with-icon, .back-to-top-btn').forEach(btn => {
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            btn.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px) scale(1.04)`;
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'translate(0px, 0px) scale(1)';
        });
    });

    // Proximity Floating Dock Magnification Wave for Navbar Items
    const navContainer = document.querySelector('.nav-container');
    if (navContainer) {
        const dockTargets = navContainer.querySelectorAll('.nav-link, .cart-btn-nav, .user-pill, .btn-outline, .btn-with-icon');
        navContainer.addEventListener('mousemove', (e) => {
            const mouseX = e.clientX;
            dockTargets.forEach(el => {
                const rect = el.getBoundingClientRect();
                const center = rect.left + rect.width / 2;
                const distance = Math.abs(mouseX - center);
                const maxDistance = 140;
                
                if (distance < maxDistance) {
                    const scale = 1 + (0.16 * (1 - distance / maxDistance));
                    const translateY = -5 * (1 - distance / maxDistance);
                    el.style.transform = `translateY(${translateY}px) scale(${scale})`;
                    el.style.zIndex = '10';
                } else {
                    el.style.transform = '';
                    el.style.zIndex = '1';
                }
            });
        });

        navContainer.addEventListener('mouseleave', () => {
            dockTargets.forEach(el => {
                el.style.transform = '';
                el.style.zIndex = '1';
            });
        });
    }
});
