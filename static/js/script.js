// Función para mostrar/ocultar el menú principal
function toggleMenu() {
	var menu = document.getElementById('navbarID');
	menu.classList.toggle('open');
}

// Funciones para modales de inventario
document.addEventListener('DOMContentLoaded', function() {
		// Mostrar/ocultar contraseña
		document.querySelectorAll('.toggle-password').forEach(function(eye) {
			eye.addEventListener('click', function() {
				const targetId = eye.getAttribute('data-target');
				const input = document.getElementById(targetId);
				if (input) {
					if (input.type === 'password') {
						input.type = 'text';
					} else {
						input.type = 'password';
					}
				}
			});
		});
	const btnAgregar = document.getElementById('btnAbrirAgregar');
	const modalAgregar = document.getElementById('modalAgregar');
	if(btnAgregar && modalAgregar) {
		btnAgregar.addEventListener('click', function() {
			modalAgregar.style.display = 'flex';
		});
	}
	// Abrir modales editar/eliminar
	document.querySelectorAll('[data-modal]').forEach(function(btn) {
		btn.addEventListener('click', function() {
			const id = btn.getAttribute('data-modal');
			const modal = document.getElementById(id);
			if(modal) modal.style.display = 'flex';
		});
	});
	// Cerrar cualquier modal
	document.querySelectorAll('[data-close]').forEach(function(btn) {
		btn.addEventListener('click', function() {
			const id = btn.getAttribute('data-close');
			const modal = document.getElementById(id);
			if(modal) modal.style.display = 'none';
		});
	});
});

// Funciones para abrir y cerrar modales del dashboard
function openDashboardModal(id) {
	var modal = document.getElementById(id);
	modal.style.display = 'flex';
	modal.style.justifyContent = 'center';
	modal.style.alignItems = 'center';
	document.body.style.overflow = 'hidden';
}
function closeDashboardModal(id) {
	var modal = document.getElementById(id);
	modal.style.display = 'none';
	document.body.style.overflow = '';
}

// Funciones para abrir y cerrar modales del catálogo
function openModal(id) {
	document.getElementById(id).style.display = 'flex';
	document.body.style.overflow = 'hidden';
}
function closeModal(id) {
	document.getElementById(id).style.display = 'none';
	document.body.style.overflow = '';
}
