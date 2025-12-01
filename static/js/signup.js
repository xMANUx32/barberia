$(document).ready(function() {
    // Mostrar panel de registro al cargar la página
    $('.login-info-box').fadeIn(); // Opción de iniciar sesión a la izquierda
    $('.register-info-box').fadeOut(); // Opción de registro a la derecha
    $('.white-panel').addClass('right-log'); // Panel blanco movido a la derecha
    
    $('.login-show').removeClass('show-log-panel'); // Ocultar formulario de login
    $('.register-show').addClass('show-log-panel'); // Mostrar formulario de registro
});

// Manejo de cambios en los radio buttons para alternar entre iniciar sesión y registrarse
$('.login-reg-panel input[type="radio"]').on('change', function() {
    if ($('#log-login-show').is(':checked')) {
        // Mostrar formulario de registro
        $('.register-info-box').fadeOut(); // Ocultar información de registro
        $('.login-info-box').fadeIn(); // Mostrar información de inicio de sesión
        
        // Mover panel blanco hacia la derecha (mostrar registro)
        $('.white-panel').addClass('right-log');
        
        $('.register-show').addClass('show-log-panel'); // Mostrar formulario de registro
        $('.login-show').removeClass('show-log-panel'); // Ocultar formulario de login
        
    } else if ($('#log-reg-show').is(':checked')) {
        // Mostrar formulario de iniciar sesión
        $('.register-info-box').fadeIn(); // Mostrar información de registro
        $('.login-info-box').fadeOut(); // Ocultar información de inicio de sesión
        
        // Mover panel blanco hacia la izquierda (mostrar login)
        $('.white-panel').removeClass('right-log');
        
        $('.login-show').addClass('show-log-panel'); // Mostrar formulario de login
        $('.register-show').removeClass('show-log-panel'); // Ocultar formulario de registro
    }
});
document.addEventListener('DOMContentLoaded', function () {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
});