// Se ejecuta antes de pintar: tema claro por defecto; oscuro solo si el usuario lo eligió.
try { document.documentElement.dataset.theme = localStorage.getItem('theme') === 'dark' ? 'dark' : 'light'; }
catch (e) { document.documentElement.dataset.theme = 'light'; }
